# Docker Deployment

This document describes how to deploy `zotero_server` with a WebDAV sidecar using Docker Compose.

## Architecture

```
VPS Docker Compose
  ├─ zotero-server
  │    ├─ FastAPI
  │    ├─ SQLite DB volume
  │    └─ 127.0.0.1:8080
  │
  └─ zotero-webdav
       ├─ rclone serve webdav
       ├─ attachment file volume
       └─ 127.0.0.1:9000

Local machine
  └─ ssh tunnel
       ├─ localhost:8080 -> VPS 127.0.0.1:8080
       └─ localhost:9000 -> VPS 127.0.0.1:9000
```

**Note**: No Nginx/Caddy reverse proxy is required because access is via SSH tunnel only.

## Quick Start

1. Clone or navigate to the project directory.

2. Create `.env` from the example and make sure the data directories are owned by your user:

```bash
cp .env.example .env
# Edit .env with your credentials and UID/GID
mkdir -p data/server data/webdav
```

`.env` contains:

```
ZOTERO_ADMIN_TOKEN=your-secret-token
USER_ID=1000      # $(id -u) on the host
GROUP_ID=1000     # $(id -g) on the host
```

3. Build and start services:

```bash
docker compose up -d --build
```

4. Verify:

```bash
# API server
curl -i http://127.0.0.1:8080/

# WebDAV
curl -i -X OPTIONS http://127.0.0.1:9000/
```

## SSH Tunnel

On your local machine:

```bash
ssh -N \
  -L 8080:127.0.0.1:8080 \
  -L 9000:127.0.0.1:9000 \
  user@vps
```

## Zotero Settings

### Data Sync Server

```
URL: http://127.0.0.1:8080
```

### File Sync (WebDAV)

```
Protocol: WebDAV
URL: http://127.0.0.1:9000/zotero/
Username: any
Password: any
```

The WebDAV server is configured without authentication. You may enter any username and password in the Zotero client settings. The connection is secured by the SSH tunnel.

Click "Verify Server" in Zotero to confirm connectivity.

## Data Locations

Bind mounts are used for easy backup:

```
SQLite DB:      ./data/server/zotero.db
WebDAV files:   ./data/webdav/zotero/*.zip
                ./data/webdav/zotero/*.prop
```

## Logs

```bash
docker compose logs -f zotero-server
docker compose logs -f zotero-webdav
```

## Stop

```bash
docker compose down
```

## Backup

```bash
# Backup SQLite
cp ./data/server/zotero.db ./backup/zotero-$(date +%Y%m%d).db

# Backup WebDAV files
tar czf ./backup/webdav-$(date +%Y%m%d).tgz -C ./data/webdav .
```

## Debug Logging

Set the log level to `DEBUG` in `docker-compose.yml` (default is `INFO`):

```yaml
environment:
  ZOTERO_LOG_LEVEL: "DEBUG"
```

After restarting with `docker compose up -d`, server logs will include:

```bash
# Show all requests and responses
docker compose logs -f zotero-server

# Show detailed batch item processing (search for ITEMS BATCH)
docker compose logs -f zotero-server | grep "ITEMS BATCH"

# Show itemType validation errors specifically
docker compose logs -f zotero-server | grep "validate_item_data\|itemType"
```

Useful log patterns:

- `REQUEST ... headers=...` — incoming request with URL and headers
- `RESPONSE ... status=... version=...` — response status and library version
- `ITEMS BATCH count=N` — number of items in a batch upload
- `ITEMS BATCH[N] missing itemType key=... available_keys=...` — when an item lacks `itemType`
- `VALIDATE FAIL itemType missing for key=...` — validation failure with full data snapshot
