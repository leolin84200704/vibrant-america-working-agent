# VP-18462 shadow replay (LIS-setting-consumer)

Runs INSIDE a prod `lis-setting-consumer` pod and replays the shadow comparison
for a range of ids without waiting for organic traffic. It uses the pod's OWN
`/protos/*.proto`, `/dist/grpc.options.js` loader options, `/dist/oauth2.js`
(`getServiceToken`, `createOAuth2Metadata`) and `/dist/setting-consumer/proxy-grpc-mode.js`
(`diffShadow`, `normaliseKitStatus`), so the verdict is the consumer's own decoder,
not a probe's approximation (the 09-23 lesson).

    kubectl cp setting-consumer-shadow-replay.js setting/<pod>:/tmp/replay.js
    kubectl exec -n setting <pod> -- sh -c 'node /tmp/replay.js <kit_center> <kit_radius> <patient_center> <patient_radius> [extra_kit_centers...] > /tmp/replay.out 2>&1; cat /tmp/replay.out'

Notes:
- axios in the image is ESM → dynamic import. The app's redis client keeps the
  event loop alive, hence the explicit `process.exit(0)`.
- Every proxy call it makes shows up as `@operation:proxyGrpcCaller` on trans v1
  (`route:/proxy/grpc/get*`) from the setting-consumer pod IPs — exclude the run
  window when counting organic proxy traffic for VP-18320.
- 2026-09-30 00:11–00:12Z: kit 163/163 agree (89 non-empty), result 61/61 agree
  (50 non-empty), 0 errors → prod flipped to `SETTING_GRPC_MODE=grpc`.
