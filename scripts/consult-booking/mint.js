// Manual Clinical Consult booking kit (LBS-1799/1828/1848). Edit the ids below per ticket: provider user_id, customer_id, clinic_id, login email.
const {execSync}=require('child_process');const jwt=require('/Users/hung.l/src/LIS-transformer-v2/node_modules/jsonwebtoken');
const s=execSync("kubectl get configmap -n transv2 lis-transv2-config -o jsonpath='{.data.secretOrKeyProd}'").toString().replace(/^'|'$/g,'');
const now=Math.floor(Date.now()/1000);
process.stdout.write(jwt.sign({user_id:169338,customer_id:46569,clinic_id:150084,user_roles:['provider'],email_log_in_id:'patti@sensoryfocus.com',iat:now,exp:now+900},s,{algorithm:'HS256'}));
