#!/bin/sh
# VP-19339: create lis_emr.patient_platform_client_ids on prod from the emr-v2 prod pod.
# Aborts unless the target is lisportalprod2 / lis_emr. Prints SHOW CREATE TABLE and the row count.
set -e
SQL=~/src/lis-backend-emr-v2.worktrees/VP-19339/prisma/patient_platform_client_ids.manual.sql
P=$(kubectl get pod -n emr-v2 -l app=lis-emr-v2-prod -o jsonpath='{.items[0].metadata.name}')
C=lis-emr-v2-prod
JS=$(mktemp)
cat > "$JS" <<'JSEOF'
const mysql=require('mysql2/promise');const fs=require('fs');
(async()=>{const u=new URL(process.env.DATABASE_URL);
const c=await mysql.createConnection({host:u.hostname,port:+u.port||3306,user:decodeURIComponent(u.username),password:decodeURIComponent(u.password),database:u.pathname.slice(1),ssl:{rejectUnauthorized:false},connectTimeout:8000});
const [v]=await c.query('SELECT @@version v, DATABASE() d');console.log(JSON.stringify(v),u.hostname);
if(v[0].d!=='lis_emr'||!/lisportalprod2/.test(u.hostname)){console.error('ABORT: unexpected target');process.exit(2);}
const sql=fs.readFileSync('/app/temp/ppci.sql','utf8').split('\n').filter(l=>!l.startsWith('--')).join('\n');
await c.query('SET SESSION lock_wait_timeout = 5');await c.query(sql);
const [s]=await c.query('SHOW CREATE TABLE patient_platform_client_ids');console.log(s[0]['Create Table']);
const [n]=await c.query('SELECT COUNT(*) n FROM patient_platform_client_ids');console.log('rows',n[0].n);await c.end();})().catch(e=>{console.error('ERR',e.message);process.exit(1)});
JSEOF
kubectl -n emr-v2 exec "$P" -c $C -- mkdir -p /app/temp
kubectl -n emr-v2 cp "$SQL" "$P":/app/temp/ppci.sql -c $C
kubectl -n emr-v2 cp "$JS" "$P":/app/temp/ppci_ddl.js -c $C
kubectl -n emr-v2 exec "$P" -c $C -- sh -c 'cd /app/temp && NODE_PATH=/app/node_modules node ppci_ddl.js; rm -f ppci_ddl.js ppci.sql'
rm -f "$JS"
