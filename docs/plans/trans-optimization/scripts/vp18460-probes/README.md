# VP-18460 equivalence probes

Run INSIDE the trans pod (no curl in the image; node + axios are there):

    kubectl -n default cp probe-batches2-6-prod.js default/<pod>:/tmp/p.js -c lis-trans
    kubectl -n default exec <pod> -c lis-trans -- node /tmp/p.js <accession> <sample_id> <barcode>

Each probe mints a client-credentials token from the pod's own OAUTH2_* env, then fetches
every key's URL through the public ingress (old) and the in-cluster Service (new) and
compares status + body bytes. Unauthenticated calls are compared too (both must 401/404 the
same way — proves the ingress injects nothing the service depends on).

Known non-identical-but-equivalent cases (2026-09-29):
- generateNormalOrderPdf 400 body carries a timestamp.
- getSubmittedBarcodesInfo carries signed R2 URLs; old-vs-old differs raw too, equal after stripping.
- downloadReceipt renders a fresh PDF per call (same size, different creation metadata).

`transv2-direct-grpc-probe.js` runs inside the transv2 pod and calls ShippingService /
TestResultGrpcService directly; it needs a proto that declares GetKitStatusBySampleId, which
the stage_test image did NOT have on 2026-09-29 (the S2 direct-gRPC code is main-only).
