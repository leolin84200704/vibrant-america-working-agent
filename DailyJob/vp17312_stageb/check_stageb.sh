#!/bin/bash
# VP-17312 Stage B passive verification — run every 30 min after the 2026-07-07 deploy.
# Exits 2 when the VPN is down (loop terminator), 1 on FAIL findings, 0 on all-pass.
# Deploy facts: first gradual-cutover deploy 2026-07-07 22:56 UTC (main c0a6871);
#   the AKS pod is PIPELINE_LOCATION=cloud and must stay idle while all DB flags are onprem.
#   NOTE: every main-branch redeploy gives the AKS pod a NEW replicaset hash, so CLOUD_HASH
#   is resolved dynamically from kubectl below — a hardcoded hash silently goes stale after a
#   redeploy and the "cloud owns 0 rows" check would then pass against a dead pod (2026-07-08:
#   redeploy PR #243 moved cloud pod 5ff47dcbdf -> 854c87c9b and exposed exactly this bug).

MYSQL=/opt/homebrew/opt/mysql-client/bin/mysql
DB_ARGS=(-h lisportalprod2.mysql.database.azure.com -P 3306 -u lis_core_emr -p'md?At3pUJnS2?Zx68' --ssl-mode=REQUIRED lis_emr -N)
DEPLOY_TS='2026-07-07 22:50:00'
FAIL=0

echo "=== VP-17312 Stage B check $(date '+%Y-%m-%d %H:%M:%S %Z') ==="

# Resolve the CURRENT AKS (cloud) pod's replicaset hash dynamically (survives redeploys).
CLOUD_POD=$(kubectl get pods -n emr-v2 -l app=lis-emr-v2-prod -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
CLOUD_HASH=$(printf '%s' "$CLOUD_POD" | sed -E 's/^lis-emr-v2-deployment-prod-(.+)-[a-z0-9]+$/\1/')
if [ -z "$CLOUD_HASH" ] || [ "$CLOUD_HASH" = "$CLOUD_POD" ]; then
  echo "cloud_hash: UNRESOLVED (kubectl failed or pod-name format changed) — cloud-idle checks unreliable this run"
  CLOUD_HASH='__CLOUD_POD_UNKNOWN__'; FAIL=1
else
  echo "cloud_pod: $CLOUD_POD (hash=$CLOUD_HASH)"
fi

# 0. VPN / on-prem reachability — loop terminates when this is gone
if ! nc -z -w 4 192.168.60.6 22 2>/dev/null; then
  echo "VPN_DOWN: 192.168.60.6 unreachable — stop the monitoring loop"
  exit 2
fi

# 1. Health, both sides
parse_health() { python3 -c "import sys,json;d=json.load(sys.stdin);print(d['status'],'uptime='+str(int(d['uptime']))+'s')" 2>/dev/null; }
ONPREM=$(curl -s -m 6 http://192.168.60.6:31318/api/v1/health | parse_health)
echo "onprem_health: ${ONPREM:-FAIL}"; [ -z "$ONPREM" ] && FAIL=1
CLOUD=$(kubectl exec -n emr-v2 deploy/lis-emr-v2-deployment-prod -c lis-emr-v2-prod -- wget -qO- -T 5 http://localhost:3000/api/v1/health 2>/dev/null | parse_health)
echo "cloud_health: ${CLOUD:-FAIL}"; [ -z "$CLOUD" ] && FAIL=1

# 2. Cloud pod must own ZERO pipeline rows
CLOUD_ROWS=$("$MYSQL" "${DB_ARGS[@]}" -e "
SELECT (SELECT COUNT(*) FROM hl7_file_input WHERE last_update_pod_name LIKE '%${CLOUD_HASH}%')
     + (SELECT COUNT(*) FROM result_transmission_records WHERE processing_pod_name LIKE '%${CLOUD_HASH}%');" 2>/dev/null | tail -1)
echo "cloud_pipeline_rows: $CLOUD_ROWS (must be 0)"; [ "$CLOUD_ROWS" != "0" ] && FAIL=1

# 3. On-prem activity since deploy (informational — sparse traffic is normal)
"$MYSQL" "${DB_ARGS[@]}" -e "
SELECT CONCAT('orders_since_deploy: ', COUNT(*), ' (pods: ', IFNULL(GROUP_CONCAT(DISTINCT SUBSTRING_INDEX(last_update_pod_name,'-',-2)),'-'), ')') FROM hl7_file_input WHERE received_time >= '${DEPLOY_TS}';
SELECT CONCAT('results_since_deploy: ', COUNT(*), ' status=', IFNULL(GROUP_CONCAT(DISTINCT transmission_status),'-'), ' (pods: ', IFNULL(GROUP_CONCAT(DISTINCT SUBSTRING_INDEX(processing_pod_name,'-',-2)),'-'), ')') FROM result_transmission_records WHERE created_at >= '${DEPLOY_TS}';" 2>/dev/null | grep -v Warning

# 4. Duplicate delivery check since deploy
DUPS=$("$MYSQL" "${DB_ARGS[@]}" -e "
SELECT COUNT(*) FROM (SELECT sample_id FROM result_transmission_records WHERE created_at >= '${DEPLOY_TS}' GROUP BY sample_id, result_client_id, emr_service, sftp_remote_path HAVING COUNT(*) > 1) d;" 2>/dev/null | tail -1)
echo "duplicate_deliveries: $DUPS (must be 0)"; [ "$DUPS" != "0" ] && FAIL=1

# 5. Stuck/failed transmissions since deploy
STUCK=$("$MYSQL" "${DB_ARGS[@]}" -e "
SELECT COUNT(*) FROM result_transmission_records WHERE created_at >= '${DEPLOY_TS}' AND (transmission_status LIKE '%ERROR%' OR generation_status LIKE '%ERROR%' OR (transmission_status IN ('PENDING','TRANSMITTING') AND created_at < NOW() - INTERVAL 30 MINUTE));" 2>/dev/null | tail -1)
echo "stuck_or_error_results: $STUCK (must be 0)"; [ "$STUCK" != "0" ] && FAIL=1

# 6. Cloud pod new ERRORs in the last 35 min
CLOUD_ERR=$(kubectl logs -n emr-v2 deploy/lis-emr-v2-deployment-prod -c lis-emr-v2-prod --since=35m 2>/dev/null | grep -c "ERROR")
echo "cloud_pod_errors_35m: ${CLOUD_ERR:-kubectl_fail}"; [ "${CLOUD_ERR:-1}" != "0" ] && FAIL=1

# 7. Retriable backlog should not grow abnormally
"$MYSQL" "${DB_ARGS[@]}" -e "SELECT CONCAT('pending_retriable: ', COUNT(*)) FROM hl7_file_input WHERE parse_finished=0 AND retry_num>0;" 2>/dev/null | grep -v Warning

# 8. emr-logging — cloud pod stdout WARN/ERROR/FATAL breakdown (last 35m)
#    (on-prem pod stdout logs need in-cluster kubectl / ssh key not held here; DB log tables in step 9 cover on-prem too)
CLOUD_LOG=$(kubectl logs -n emr-v2 deploy/lis-emr-v2-deployment-prod -c lis-emr-v2-prod --since=35m 2>/dev/null)
if [ -z "$CLOUD_LOG" ]; then
  echo "emr_logging_cloud: kubectl_fail_or_empty"
else
  W=$(printf '%s\n' "$CLOUD_LOG" | grep -cE '\bWARN\b'); E=$(printf '%s\n' "$CLOUD_LOG" | grep -cE '\bERROR\b'); F=$(printf '%s\n' "$CLOUD_LOG" | grep -cE '\bFATAL\b')
  echo "emr_logging_cloud_35m: WARN=$W ERROR=$E FATAL=$F"
  [ "$E" != "0" ] || [ "$F" != "0" ] && FAIL=1
  # surface first 2 ERROR/FATAL lines when present (trimmed)
  if [ "$E" != "0" ] || [ "$F" != "0" ]; then
    printf '%s\n' "$CLOUD_LOG" | grep -E '\bERROR\b|\bFATAL\b' | head -2 | cut -c1-160 | sed 's/^/    /'
  fi
fi

# 9. emr logging TABLES (order_processing_logs / result_transmission_logs)
#    Baseline 2026-07-07: both are EMPTY all-time (app logs to stdout, DB log tables unwired).
#    Assertions during Stage B: (a) no ERROR/FATAL rows since deploy, (b) cloud pod never appears as pod_name.
for T in order_processing_logs result_transmission_logs; do
  READ=$("$MYSQL" "${DB_ARGS[@]}" -e "
    SELECT CONCAT(
      (SELECT COUNT(*) FROM $T WHERE created_at >= '${DEPLOY_TS}'), '|',
      (SELECT COUNT(*) FROM $T WHERE created_at >= '${DEPLOY_TS}' AND log_level IN ('ERROR','FATAL')), '|',
      (SELECT COUNT(*) FROM $T WHERE pod_name LIKE '%${CLOUD_HASH}%'));" 2>/dev/null | tail -1)
  ROWS=${READ%%|*}; REST=${READ#*|}; ERR=${REST%%|*}; CLOUDP=${REST##*|}
  echo "logtable_${T}: rows_since_deploy=${ROWS:-?} error_fatal=${ERR:-?} cloud_pod_rows=${CLOUDP:-?}"
  [ "${ERR:-0}" != "0" ] && FAIL=1
  [ "${CLOUDP:-0}" != "0" ] && FAIL=1
done

echo "=== verdict: $([ $FAIL -eq 0 ] && echo PASS || echo FAIL) ==="
exit $FAIL
