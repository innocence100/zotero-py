# Zotero Server — 不修复事项清单

以下问题经分析后判定为**不修复**，理由基于项目目标（个人库、轻量、低成本 VPS 自建）。

---

## 安全模型相关

### WebDAV 无认证

`docker-compose.yml` 中 rclone WebDAV 未配置认证，README/DOCKER.md 明确说明依赖 SSH tunnel 保护。

**不修复理由：** 项目架构就是 `127.0.0.1` 绑定 + SSH tunnel，不存在公网暴露场景。如需认证，在 rclone 侧加 `--user`/`--pass` 即可，不是 Python 代码的问题。

### Admin token 支持 query 参数泄露风险

`admin.py:31` 允许 `?admin_token=` 方式鉴权，token 可能进入 shell history 或代理日志。

**不修复理由：** Admin API 仅用于 `zoteroctl.py` 本机 CLI 操作，频率极低，且 SSH tunnel 下无反代/日志系统。移除一行代码即可，但投入产出比太低。

### API key 权限字段不执行

`auth.py:46-61` 只验证 key 存在，不检查 `ApiKey.access` 中的 `write`/`files`/`groups` 等权限。

**不修复理由：** 单人自用服务器，所有 key 属于同一用户，无需权限隔离。实现权限检查需改动每个路由的 auth 层，工作量大且对个人场景零收益。

---

## 协议行为相关

### 单对象写入允许"未来版本"

`library.py:84-85` 只拒绝 `obj.version > version`（旧版本覆盖），不拒绝 `version > obj.version`（未来版本写入）。批量写入在 `library.py:107-110` 有拒绝未来版本。

**不修复理由：** 原版 Zotero dataserver 的单对象 PUT/PATCH 语义也是如此——只要提交的 version 等于当前 version 就允许写入。批量写入拒绝未来 version 是因为 version=0 表示新建，需区分。两者语义不同，当前行为与原版一致，不是 bug。

### Schema 校验轻量

`library.py:130-142` 对 item 只校验 `itemType` 和 key 格式，不校验字段结构、creator 类型等。

**不修复理由：** 明确的设计取舍，`progress.md` 已标注 "Schema validation is minimal... Sufficient for personal use"。Zotero 客户端自身保证 payload 结构正确，实现完整校验维护成本高、对个人自用无收益。

---

## 架构取舍

### Collection 内 item 查询用 `json_extract` + `LIKE`

`items.py:90-91` 用 SQLite `json_extract` + `LIKE` 在 JSON 文本上匹配 collection key，非结构化关联查询。

**不修复理由：** 个人库通常几千到几万条 item，SQLite 此方案完全够用。换成关联表需重构数据模型和同步逻辑，工作量大且无实际性能收益。

### SQLite 无迁移机制

`main.py:69-73` 只做 `create_all`，无 Alembic 等迁移工具。

**不修复理由：** 项目处于 v0.1.0 早期阶段，model 还在变化。个人部署可随时备份 `zotero.db` 后重建。等 model 稳定后再考虑引入迁移。

---

## 明确排除的功能

以下功能在 README 中已声明"不包含"，此处仅记录分析结论，不再重复论述。

### 全文索引（Full-Text）

端点为 stub（`stubs.py:15-55`），返回空结果。不影响客户端正常使用，Zotero 桌面端自带本地全文搜索。

### Group Libraries

`library.py:20-21` 直接拒绝，`groups.py` 返回空列表。实现群组需要完整的 Group/Library 模型、成员管理、权限系统，远超项目范围。

### 官方 ZFS 文件存储 API

`stubs.py:107-129` 对 file 上传/下载返回 404。文件同步走 WebDAV 是项目核心架构决策。

### `/keys/sessions` Web 登录流程

未实现。支持方式为 API Key（`POST /keys` 用用户名密码换取 key），足够个人使用。
