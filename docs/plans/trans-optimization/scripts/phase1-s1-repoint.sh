#!/usr/bin/env bash
# TRANS-OPT Phase 1.1 (S1): repoint transv2 ConfigMap key
#   checkIfPersonalizedReportCanBeCreated
# from cloud-local-proxy (cloud-local ns :3047 -> on-prem 192.168.60.77:8081)
# to the on-prem report server directly, i.e. the value trans v1 prod already uses.
#
# Config-only. No code change. Default is DRY RUN (prints current value and the
# planned patch). Pass --apply to patch + rollout restart, --rollback to restore
# the value recorded in the backup file of the same env.
#
# Usage:
#   phase1-s1-repoint.sh st            # dry run on staging
#   phase1-s1-repoint.sh st --apply    # patch staging cm + restart st deployment
#   phase1-s1-repoint.sh prod --apply  # same on prod (do st first, verify, then prod)
#   phase1-s1-repoint.sh prod --rollback
#
# Requires: kubectl context lisportalprod with a fresh Azure login (az login).
set -euo pipefail

ENV="${1:-}"; ACTION="${2:---dry-run}"
case "$ENV" in
  st)   NS=transv2; CM=lis-transv2-config-st; DEPLOY=lis-transv2-deployment-st ;;
  prod) NS=transv2; CM=lis-transv2-config;    DEPLOY=lis-transv2-deployment ;;
  *) echo "usage: $0 <st|prod> [--apply|--rollback|--dry-run]" >&2; exit 2 ;;
esac

KEY=checkIfPersonalizedReportCanBeCreated
# Same string as trans v1 prod (LIS-transformer/docs/proxy-migration-configmap.md).
# Callers append the sample id directly, so the trailing "?sampleId=" is part of the value.
NEW_VALUE='http://192.168.60.77:8081/secure/nologin/CheckIfPersonalizedReportCanBeCreated?sampleId='

BACKUP_DIR="${S1_BACKUP_DIR:-$HOME/.trans-opt-backups}"   # contains secrets: never commit
mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%dT%H%M%S)"
VALUE_FILE="$BACKUP_DIR/${CM}.${KEY}.before"

K="kubectl --request-timeout=30s -n $NS"

echo "== $ENV: $NS/$CM key=$KEY"
CURRENT="$($K get cm "$CM" -o jsonpath="{.data.$KEY}")"
echo "current : $CURRENT"
echo "target  : $NEW_VALUE"

case "$ACTION" in
  --dry-run)
    echo "(dry run; pass --apply to patch, --rollback to restore)"; exit 0 ;;
  --apply)
    if [ "$CURRENT" = "$NEW_VALUE" ]; then echo "already at target, nothing to do"; exit 0; fi
    $K get cm "$CM" -o yaml > "$BACKUP_DIR/${CM}.${STAMP}.yaml"
    [ -f "$VALUE_FILE" ] || printf '%s' "$CURRENT" > "$VALUE_FILE"
    echo "backup  : $BACKUP_DIR/${CM}.${STAMP}.yaml (+ $VALUE_FILE)"
    $K patch cm "$CM" --type merge -p "{\"data\":{\"$KEY\":\"$NEW_VALUE\"}}"
    ;;
  --rollback)
    [ -f "$VALUE_FILE" ] || { echo "no recorded value at $VALUE_FILE" >&2; exit 1; }
    OLD="$(cat "$VALUE_FILE")"
    echo "restore : $OLD"
    $K patch cm "$CM" --type merge -p "{\"data\":{\"$KEY\":\"$OLD\"}}"
    ;;
  *) echo "unknown action $ACTION" >&2; exit 2 ;;
esac

echo "after   : $($K get cm "$CM" -o jsonpath="{.data.$KEY}")"
# envFrom configMapRef is read at pod start -> pods must be recreated to pick it up.
$K rollout restart deployment/"$DEPLOY"
$K rollout status deployment/"$DEPLOY" --timeout=300s

# Consumer-layer readback: the env var as the new pod actually sees it, and a
# real GET from inside the pod to the new target (proves network path from ns).
POD="$($K get pods -l app=$( [ "$ENV" = st ] && echo lis-transv2-st || echo lis-transv2 ) \
        --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}')"
echo "readback pod: $POD"
$K exec "$POD" -- sh -c "env | grep '^$KEY='"
$K exec "$POD" -- node -e "
const http=require('http');const u=process.env.$KEY+'0';
http.get(u,r=>{let b='';r.on('data',d=>b+=d);r.on('end',()=>console.log('GET',u,'->',r.statusCode,b));})
  .on('error',e=>{console.error('GET failed',e.message);process.exit(1)});"
