// usage: node my.js "SQL"  -- SELECT only; session forced READ ONLY. creds from configmap lis-corelisv7-config
const {execSync}=require('child_process');
const mysql=require('/Users/hung.l/src/lis-backend-emr-v2/node_modules/mysql2/promise');
const u=new URL(execSync("kubectl get configmap -n default lis-corelisv7-config -o jsonpath='{.data.DATABASE_URL}'").toString());
const sql=process.argv[2]; if(!/^\s*(select|show|describe|desc)\b/i.test(sql)){console.error('read-only kit');process.exit(2)}
(async()=>{const c=await mysql.createConnection({host:u.hostname,port:u.port||3306,user:decodeURIComponent(u.username),password:decodeURIComponent(u.password),ssl:{rejectUnauthorized:false},supportBigNumbers:true,bigNumberStrings:true,dateStrings:true});
await c.query('SET SESSION TRANSACTION READ ONLY');const [r]=await c.query(sql);console.log(JSON.stringify(r,null,1));await c.end();})().catch(e=>{console.error(e.message);process.exit(1)});
