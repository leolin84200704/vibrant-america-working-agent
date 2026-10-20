#!/bin/bash
URL=$(kubectl get configmap -n transv2 lis-transv2-config -o jsonpath='{.data.DATABASE_URL_CALENDAR}' | sed 's/?schema=.*//')
PGOPTIONS="-c search_path=calendar_prod -c default_transaction_read_only=on" /opt/homebrew/opt/libpq/bin/psql "$URL" -X -A -F'|' -c "$1"
