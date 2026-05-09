#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# ----------------------------------------------------------------------------
# 初始化环境
# ----------------------------------------------------------------------------

if [[ ! -f .env ]]; then
    cp .env.example .env
    echo "[init] 已创建 .env，请编辑后重新运行本脚本:"
    echo "       nano .env   # 或 vim .env"
    echo ""
    echo "至少需要修改:"
    echo "  ZOTERO_ADMIN_TOKEN=your-secret-token"
    echo "  USER_ID=$(id -u)"
    echo "  GROUP_ID=$(id -g)"
    exit 1
fi

# 确保数据目录由当前用户拥有，避免 Docker 自动创建为 root
mkdir -p data/server data/webdav

echo "[init] 数据目录已准备:"
ls -ld data data/server data/webdav

echo ""
echo "[init] 启动 Docker Compose ..."
docker compose up -d --build

echo ""
echo "============================================"
echo "  Zotero Server 已启动"
echo "============================================"
echo "  数据同步:   http://127.0.0.1:8080"
echo "  WebDAV:     http://127.0.0.1:9000"
echo ""
echo "  数据位置:"
echo "    数据库:   ./data/server/"
echo "    附件:     ./data/webdav/"
echo ""
echo "  常用命令:"
echo "    docker compose logs -f zotero-server"
echo "    docker compose down"
echo "    ./zoteroctl.py create <user> <pass>"
echo "============================================"
