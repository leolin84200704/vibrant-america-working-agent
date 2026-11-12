#!/usr/bin/env bash
# VP-18479: read-only per-route request counts for vw-page (web-homepage-api) on the on-prem cluster.
# Run as leo on 192.168.60.5:  bash vp18479-vw-page-route-counts.sh
# Prints counts only. The raw pod logs contain request bodies (LoggingMiddleware logs form posts),
# so they are never written to disk or copied off the host.
set -euo pipefail
NS=lis
PODS=$(kubectl -n "$NS" get pods -o name | grep vw-page || true)
[ -z "$PODS" ] && { echo "no vw-page pods in ns $NS"; exit 1; }

echo "== pods (start time, restarts)"
kubectl -n "$NS" get pods -o custom-columns=NAME:.metadata.name,START:.status.startTime,RESTARTS:.status.containerStatuses[0].restartCount | grep -E 'NAME|vw-page' || true

for p in $PODS; do
  echo "== $p"
  kubectl -n "$NS" logs "$p" --timestamps 2>/dev/null | awk '
    NR==1 { first=$1 }
    { last=$1; total++ }
    # uvicorn access line: <ts> INFO:  <ip>:<port> - "GET /path?q HTTP/1.1" 200 OK
    match($0, /"(GET|POST|PUT|DELETE|OPTIONS|PATCH|HEAD) [^ "]+ HTTP\/[0-9.]+" [0-9]+/) {
      req=substr($0, RSTART+1, RLENGTH-1)
      split(req, a, " "); m=a[1]; path=a[2]; st=a[4]
      sub(/\?.*/, "", path)
      sub(/^\/v1\/lis\/vw-page/, "", path)
      sub(/\/getEducationInfo\/[^\/]+$/, "/getEducationInfo/{country}", path)
      if      (path=="/health" || path=="/consultest") g="probe"
      else if (path ~ /ReportAction|ReportCount/)      g="report-action"
      else if (path ~ /getEducationInfo/)              g="education"
      else if (path ~ /\/shortURL$/)                   g="short-url"
      else if (path=="/orders")                         g="order-stats"
      else if (path ~ /\/(subscribe|patientsignup|contactus|applyjob|clinicaltrialpage)$/) g="forms"
      else if (path ~ /^\/v1\/webpage\//)               g="cms"
      else                                              g="other"
      req_n++; grp[g]++; route[g" "m" "path" "st]++
    }
    END {
      printf "log window: %s -> %s, lines %d, access lines %d\n", first, last, total, req_n
      for (k in grp) printf "group %-14s %d\n", k, grp[k]
      for (k in route) printf "route %s %d\n", k, route[k]
    }' | sort
done
