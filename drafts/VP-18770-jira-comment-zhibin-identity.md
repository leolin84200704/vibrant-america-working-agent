# Draft Jira comment for VP-18770 (to Zhibin) — NOT posted

@Zhibin — one thing to be aware of on Core's side when emr-v2 starts sending the RS256 token (PR to staging today):

The OAuth2 client emr-v2 uses (OAUTH2_CLIENT_ID in the emr-v2 ConfigMaps, the same one it has used since LIS-7882 for results-grpc) mints tokens whose payload identifies the caller as `internal_user_name: "trans v2"` (internal_user_id 10000, internal_user_role service). The algorithm switch does not change that: the RS256 token carries the same identity claims.

So in Core's `token_check` / any token-based attribution, emr-v2 traffic will show up as "trans v2". The `service-name` metadata (`lis-backend-emr-v2-production`) is what tells the two apart.

If Core intends to authorize or rate-limit per service identity rather than per `service-name`, emr-v2 needs its own OAuth2 client (a new client id/secret issued for `lis-backend-emr-v2`). Who issues those on your side? Once we have it, it is a ConfigMap change only on our end.
