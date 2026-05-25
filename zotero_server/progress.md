# Zotero Server — Progress

This server targets lightweight personal multi-device data sync.

## Completed

### P0: Prevent Data Loss

- [x] Require `If-Unmodified-Since-Version` or JSON `version` for single-object writes.
- [x] Return `428` when single-object writes omit a version.
- [x] Return `412` when the remote object version is newer than the supplied version.
- [x] Return `204` for successful API v3 single-object writes and deletes.
- [x] Implement true PATCH merge semantics for items, collections, and searches.
- [x] Ensure write reports include correct `key`, `version`, and `data.version`.
- [x] Keep object updates and library version bumps in one transaction.
- [x] Batch object writes now perform per-object version checks (`412`/`400`/`unchanged`).

### P1: Client Compatibility

- [x] Return settings as `{name: {value, version}}`.
- [x] Implement `DELETE /settings?settingKey=a,b`.
- [x] Support `includeTrashed=1` for item version and download requests.
- [x] Trash semantics for `deleted: 1`.
- [x] Implement `DELETE /tags?tags=a||b`.
- [x] Single-object search GET/PUT/PATCH endpoints.
- [x] `format=keys` for objects.
- [x] `DELETE /keys/current`.
- [x] Settings single-object PUT returns `204` with proper version checks.

### P2: Data Integrity

- [x] Permanent item delete recursively deletes child items.
- [x] Validate object keys and basic schema constraints.
- [x] Validate collection hierarchy and prevent cycles.
- [x] Validate required collection fields (`name`).
- [x] Keep delete logs indefinitely for personal sync.

### P3: Lightweight Exclusions

- [x] Full-text endpoints return compatible stub responses.
- [x] File storage is handled externally via rclone WebDAV sidecar.

### Fixes: Batch Partial Update

- [x] Batch POST merges incoming fields into existing data instead of full JSON replacement.
- [x] Existing items no longer require `itemType` in partial payloads (md5/mtime/deleted updates).
- [x] Single-item PUT merges fields instead of replacing.

### Fixes: Batch Version Check Relaxation

- [x] `check_batch_object_write_version`: existing object without `version` field no longer returns `428` — returns `obj.version` instead (library-level `If-Unmodified-Since-Version` already provides consistency guarantee).
- [x] `check_batch_object_write_version`: submitted `version > obj.version` no longer returns `400` — returns `obj.version` instead (allows client to recover from stale sync state; prevents "Made no progress" deadlock).
- [x] Stale version conflict (`version < obj.version`) still returns `412` — data integrity preserved.
- [x] Verified with Zotero 7.0.32 "restore to server" sync flow: no more 428/400 deadlocks.

## Deployment

- [x] `Dockerfile` for `zotero_server` (python:3.12-slim).
- [x] `docker-compose.yml` running `zotero-server` (port 8080) + rclone WebDAV (port 9000).
- [x] `.env.example`, `.dockerignore`, `DOCKER.md`.
- [x] `zoteroctl.py` auto-loads `.env`.
- [x] `run_server.sh` for standalone local startup (no Docker).
- [x] Database default API key access changed to `files: false`.

## Debug Logging

- [x] `ZOTERO_LOG_LEVEL` env var (`INFO`/`DEBUG`).
- [x] Per-request logging in middleware.
- [x] Detailed batch item processing logs (`ITEMS BATCH`, `VALIDATE`, `updated`, `created`, etc.).

## Known Limitations

- **Schema validation is minimal.** `search.name`/`conditions` and item structure beyond `itemType` + key are not strictly validated. Sufficient for personal use, but malformed client payloads could produce unexpected data.
- **Full-text indexing is stubbed out.** Endpoints exist but return empty responses;不影响客户端正常使用.
- **Group libraries are unsupported.** Only personal user-library sync (`users/{id}`) is implemented. Group endpoints return empty results.

## Remaining Risk: `/keys/sessions`

- [ ] `/keys/sessions` login session endpoints are intentionally not implemented.
- **Impact:** If the Zotero desktop client uses the web login/session flow instead of username/password `POST /keys`, first-time account binding or reauthorization may fail with `404`.
- **Mitigation:** The supported setup is API-key based (admin-created key, or `POST /keys` from username/password). Documented in README.
- **Scope decision:** Out of scope for the lightweight self-hosted goal unless real client testing shows the target Zotero version cannot work without it.

## Real Client Testing Status

- [x] Verified with Zotero 7.0.32 desktop (via SSH tunnel) against Docker deployment.
- [x] Data sync (items/collections/settings/searches) works.
- [x] WebDAV file sync works (attachments upload/download as `.zip`/`.prop`).
- [x] Batch partial update (attachment md5/mtime) confirmed working after fix.
- [x] No "Made no progress during upload" errors after batch merge fix.
- [x] No 428/400 version-check deadlocks after `check_batch_object_write_version` relaxation.
