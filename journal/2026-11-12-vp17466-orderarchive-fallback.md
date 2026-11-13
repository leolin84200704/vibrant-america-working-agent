---
id: 2026-11-12-vp17466-orderarchive-fallback
type: journal
date: 2026-11-12
tickets: [VP-17466]
tags: [emr-v2, hl7-order-fetch, sftp, cerberus, archive, orderarchive]
distilled: true
distilled_on: 2026-11-13
---
# VP-17466: OrderArchive fallback and copy-then-delete, draft PR #543

Trigger: Leo approved the plan to stop waiting on IT for mkdir on four Cerberus accounts and use the
existing sibling OrderArchive folders, copying when rename is denied (his own manual workaround).

Done: emr-v2 feature/leo/VP-17466 -> draft PR #543 to staging. resolveArchiveDir falls back to
{parent}/OrderArchive only on a non-transient mkdir failure and only when the folder exists;
archiveRemoteFile adds copyThenDelete after both renames fail.

Pitfall caught while reading the code: the plan said "upload the local copy that was already
downloaded", but the fetch enqueues the job before archiving and the processor's archiveLocalFile
renames the local file into local archive/. Uploading from the local path would race the worker. The
copy path re-downloads the remote file into a private mkdtemp dir instead (one extra download, only on
the fallback path). Also: SFTP upload overwrites, so the copy path must check fileExists(dest) before
choosing the plain vs suffixed name; rename-collision semantics do not carry over.

Tests: spec 42 passed, full suite 198 suites green, tsc clean, pre-push hook green.

Next: Leo merges to staging and releases to main; then live check with the next OPTIMANTRA order and an
MDHQ order. Jira status change proposed only after that.
