# WIP: Zotero Server in Python

轻量自建 Zotero 数据同步服务器，兼容 Zotero 桌面客户端 API v3。

## 包含的功能

- **数据同步**：item（条目）、collection（分类）、setting（设置）、search（搜索）、tag（标签）的增量同步
- **版本冲突检测**：基于 `version` 的乐观锁，支持 `412`/`428` 语义
- **Trash / 永久删除**：支持 `deleted: 1` 软删除和硬删除
- **API Key 管理**：创建、验证、删除 API Key
- **WebDAV 文件同步**：通过 Docker Compose 外挂 rclone 实现，支持附件（PDF、网页快照等）多端同步
- **冲突安全**：批量写入时逐条校验版本，阻止旧版本覆盖新数据

## 明确不包含的功能

- **全文索引**（Full-Text）：端点存在但返回空结果，不影响客户端正常使用
- **Group 图书馆**：仅支持个人用户库（User Library）
- **ZFS 官方文件存储 API**：不模拟 S3 上传授权流程，文件同步走 WebDAV
- `/keys/sessions` Web 登录流程：仅支持 API Key 方式绑定客户端

## 快速部署

### 1. 环境要求

- Docker + Docker Compose
- SSH tunnel（无公网端口暴露方案）

### 2. 克隆并一键启动

```bash
git clone <repo>
cd zotero-py
./init.sh
# 首次运行会自动创建 .env，编辑后再次执行 ./init.sh
# nano .env  # 设置 ZOTERO_ADMIN_TOKEN 和 USER_ID/GROUP_ID（默认 1000:1000）
# ./init.sh
```

`init.sh` 会自动完成：创建 `.env`、创建数据目录（用当前用户身份，避免 root 权限问题）、构建并启动容器。

如果需要手动步骤：

### 3. 启动（Docker + WebDAV）

```bash
docker compose up -d --build
```

- 数据同步：`http://127.0.0.1:8080`
- WebDAV 文件同步：`http://127.0.0.1:9000`

### 4. SSH Tunnel（推荐）

在本地机器执行：

```bash
ssh -N \
  -L 8080:127.0.0.1:8080 \
  -L 9000:127.0.0.1:9000 \
  user@vps
```

### 5. Zotero 客户端配置

| 配置项 | 值 |
|--------|-----|
| 数据同步服务器 | `http://127.0.0.1:8080` |
| 文件同步协议 | WebDAV |
| WebDAV URL | `http://127.0.0.1:9000/zotero/` |

用户名/密码可填任意值（当前 WebDAV 未启用认证，依赖 SSH tunnel 保护）。

## 纯本地快速启动（不带 WebDAV）

```bash
# 需要 Python 3.10+ 和 uv/venv
./run_server.sh
```

默认监听 `127.0.0.1:8080`，SQLite 数据库保存在 `./zotero.db`。

## 用户管理

```bash
# 创建用户（自动从 .env 读取 admin token）
./zoteroctl.py create <username> <password>

# 列出现有用户
./zoteroctl.py list
```

## 数据备份

```bash
# 数据库
cp ./data/server/zotero.db ./backup/

# WebDAV 附件文件
cp -r ./data/webdav ./backup/
```

## 调试日志

```bash
# 查看实时日志
docker compose logs -f zotero-server

# 查看批量 item 处理详情
docker compose logs -f zotero-server | grep "ITEMS BATCH"
```

## 项目结构

```
zotero-py/
├── zotero_server/      # FastAPI 服务端源码
│   ├── main.py
│   ├── routers/
│   └── database.py
├── docker-compose.yml  # Docker 编排（server + rclone WebDAV）
├── run_server.sh       # 本地快速启动脚本
├── zoteroctl.py        # 用户管理 CLI
├── test_sync.py        # 协议回归测试
└── DOCKER.md           # 详细部署文档
```

## 协议兼容性

参考原版 Zotero `dataserver` 与客户端 `syncEngine.js` / `zfs.js` 实现，已在个人库场景下完成协议测试。

---

**Python implementation built by AI, inspired by the original Zotero dataserver. Authors: GPT-5.5, GPT-5.4, Kimi-K2.6, GLM-5.1, GLM-5. Tested by innocence100.**
