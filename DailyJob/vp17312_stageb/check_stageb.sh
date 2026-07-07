#!/bin/bash
# VP-17312 Stage B passive verification — run every 30 min after the 2026-07-07 deploy.
# Exits 2 when the VPN is down (loop terminator), 1 on FAIL findings, 0 on all-pass.
# Deploy facts: main SHA c0a6871, deploy ~2026-07-07 22:56 UTC,
#   cloud pod  = lis-emr-v2-deployment-prod-5ff47dcbdf-* (AKS, PIPELINE_LOCATION=cloud)
#   old onprem pod (pre-deploy baseline) = ...855c86674-bpxqh

MYSQL=/opt/homebrew/opt/mysql-client/bin/mysql
DB_ARGS=(-h lisportalprod2.mysql.database.azure.com -P 3306 -u lis_core_emr -p'md?At3pUJnS2?Zx68' --ssl-mode=REQUIRED lis_emr -N)
DEPLOY_TS='2026-07-07 22:50:00'
CLOUD_HASH='5ff47dcbdf'
FAIL=0

echo "=== VP-17312 Stage B check $(date '+%Y-%m-%d %H:%M:%S %Z') ==="

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

echo "=== verdict: $([ $FAIL -eq 0 ] && echo PASS || echo FAIL) ==="
exit $FAIL
