# Zotero Server — 可修改事项清单

本列表基于项目目标（个人库、轻量、低成本 VPS 自建）筛选。  
**不包含**已被 README 明确列为“不存在”的功能（Group Libraries、全文索引、官方 File Storage API、`/keys/sessions`、完整 Schema 校验等）。

---

## P0：影响数据同步正确性（建议优先修复）

- [x] **Fix：补齐 collection scope 的 item 列表接口**  
  当前服务端缺少 `GET /users/{id}/collections/{collectionKey}/items` 与 `GET /users/{id}/collections/{collectionKey}/items/top`（至少需覆盖 user library），而 Zotero 客户端测试中会请求 `.../collections/{key}/items/top?format=keys`。  
  这会导致客户端在按 collection 解析成员条目、重建集合视图或执行相关同步流程时出现 `404` 或行为不兼容。  
  **最小修复方案：**  
  - 在 `zotero_server/routers/items.py` 新增 collection-scoped 路由：  
    - `GET /{library_type}s/{library_id}/collections/{collection_key}/items`  
    - `GET /{library_type}s/{library_id}/collections/{collection_key}/items/top`  
  - 复用现有 items 列表逻辑，避免复制一套查询/响应代码。建议在 `_list_items_impl()` 增加可选 `collection_key` 参数，进入查询后基于 `item.data["collections"]` 过滤。  
  - 支持与现有 items 列表一致的核心参数：`format`、`since`、`itemKey`、`itemType`、`includeTrashed`、`limit`、`start`。  
  - `top` 语义保持一致：只返回 `parent_key is NULL` 的顶层 item。  
  - `format=keys` 与 `format=versions` 必须可用，并返回正确的 `Last-Modified-Version` / `Total-Results`。  
  - 对不存在的 collection key 返回 `404`；对 group library 仍保持当前策略。  
  **验收标准：**  
  - `GET /users/{id}/collections/{key}/items/top?format=keys` 返回该 collection 下顶层条目 key 列表。  
  - `GET /users/{id}/collections/{key}/items?itemKey=A,B&includeTrashed=1` 只返回属于该 collection 的匹配条目。  
  - `If-Modified-Since-Version` 命中时仍返回 `304`。  
  - 不改变现有 `/items`、`/items/top`、`/items/trash` 的行为。  
  受影响文件：`zotero_server/routers/items.py`，必要时补充共享辅助函数到 `zotero_server/library.py`。  
  **状态：已修复。** `_list_items_impl` 增加 `collection_key` 参数，使用 `func.json_extract(Item.data_json, "$.collections")` LIKE 语义过滤；新增两个路由。受影响文件：`zotero_server/routers/items.py`。  

- [x] **Fix：`GET /searches` 支持 `searchKey` 过滤**  
  当前 `zotero_server/routers/searches.py` 的列表接口只支持 `format` 与 `since`，但 Zotero 客户端会请求 `GET /users/{id}/searches?searchKey=A,B,C` 来按 key 拉取指定 saved search。  
  这会导致服务端返回全部 search 或无法满足客户端按 key 精确拉取的语义，影响增量同步中 missing/changed search 的补拉流程。  
  **最小修复方案：**  
  - 在 `list_searches()` 增加 `searchKey: Optional[str] = Query(None)` 参数。  
  - 与 `items.py` / `collections.py` 保持一致，将逗号分隔的 key 列表解析为数组并加入查询条件 `Search.key.in_(keys)`。  
  - `format=versions`、`format=keys`、普通 JSON 响应三条路径都必须应用同样的 `searchKey` 过滤。  
  - 对传入的每个 key 调用 `validate_object_key()`，避免无效 key 绕过校验。  
  - 保持现有 `since`、`If-Modified-Since-Version`、`Last-Modified-Version` 行为不变。  
  **验收标准：**  
  - `GET /users/{id}/searches?searchKey=A,B` 只返回 key 为 `A`、`B` 且存在的 search。  
  - `GET /users/{id}/searches?format=versions&searchKey=A,B` 只返回对应 key 的版本映射。  
  - `GET /users/{id}/searches?format=keys&searchKey=A,B` 只返回对应 key 的纯文本 key 列表。  
  - `searchKey` 与 `since` 同时存在时取交集。  
  - 不改变未传 `searchKey` 时的现有行为。  
  受影响文件：`zotero_server/routers/searches.py`。  
  **状态：已修复。** `list_searches` 增加 `searchKey` 参数，三条路径（normal/versions/keys）均已加入过滤。  

- [x] **Fix：补齐 collections/searches 批量删除接口**  
  当前已实现 `DELETE /items?itemKey=...`、`DELETE /settings?settingKey=...`、`DELETE /tags?tags=...`，但缺少原版 API 语义中的 `DELETE /collections?collectionKey=...` 与 `DELETE /searches?searchKey=...`。  
  客户端或同步恢复流程可能使用批量 key 参数删除多个 collection/search；缺失时会导致 `405/404` 或只能逐个删除，协议兼容性不完整。  
  **最小修复方案：**  
  - 在 `zotero_server/routers/collections.py` 新增 `DELETE /{library_type}s/{library_id}/collections`，读取 `collectionKey` 查询参数。  
  - 在 `zotero_server/routers/searches.py` 新增 `DELETE /{library_type}s/{library_id}/searches`，读取 `searchKey` 查询参数。  
  - 两个接口都复用当前单对象删除逻辑中的关键行为：  
    - 校验 `If-Unmodified-Since-Version`。  
    - 校验每个 object key 格式。  
    - 不存在的 key 可按当前 `DELETE /items?itemKey=...` 风格忽略，避免批量删除因远端已删除而失败。  
    - 每个实际删除的对象都写入 `SyncDeleteLog`。  
    - 每次实际删除都 bump library version，并返回最终 `Last-Modified-Version`。  
  - collection 批量删除必须复用或抽取单对象删除中的清理逻辑：  
    - 清理子 collection 的 `parent_key` / `parentCollection`。  
    - 清理 item JSON 中的 `collections` 引用。  
    - 更新受影响 item/child collection 的 version。  
  - search 批量删除必须使用已修复的 `bump_version()`，不能再次引入 `_bump_version`。  
  **验收标准：**  
  - `DELETE /users/{id}/collections?collectionKey=A,B` 删除存在的 collection，写入 deleted log，并返回 `204`。  
  - `DELETE /users/{id}/searches?searchKey=A,B` 删除存在的 search，写入 deleted log，并返回 `204`。  
  - 删除不存在 key 不应导致整个批量请求失败。  
  - `GET /users/{id}/deleted?since={oldVersion}` 能返回被删除的 collection/search key。  
  - collection 删除后，相关 child collection 与 item membership 不留下悬挂引用。  
  - 不改变现有单对象 delete 行为。  
  受影响文件：`zotero_server/routers/collections.py`、`zotero_server/routers/searches.py`，建议必要时抽取局部 helper 降低重复逻辑。  
  **状态：已修复。** collections.py 新增 `delete_collections`，复用单对象 delete 中的子 collection 与 item membership 清理；searches.py 新增 `delete_searches`，使用已修复的 `bump_version`。  

- [x] **Fix：Tag 删除后应更新受影响 item 的 version**  
  `DELETE /tags` 会从所有相关 item 中移除标签，但当前只 bump library version，未更新 item.version。  
  客户端在增量同步时可能因 `format=versions&since=` 看不到这些 item 的更新，导致 tag 删除状态无法同步到远端。  
  受影响文件：`zotero_server/routers/tags.py`。

- [x] **Fix：Collection 硬删除时应清理子 collection 的 parent_key 引用**  
  当前删除 collection 后直接写 delete log，子 collection 的 `parent_key` 可能指向已不存在的 key。  
  客户端 rebuild 树结构时可能产生孤儿或无效引用。  
  受影响文件：`zotero_server/routers/collections.py`。

- [x] **Fix：Collection 硬删除时应清理相关 item.collections 引用**  
  Item JSON 内部 `collections` 数组会保留已删除 collection 的 key，造成残留。  
  受影响文件：`zotero_server/routers/collections.py`、`zotero_server/routers/items.py`（或共享工具）。

## P1：内部一致性与基础体验修复

- [x] **Refactor：Searches 路由统一复用 `library.py` 公共逻辑**  
  `searches.py` 自行实现了 `_get_library()`、`_bump_version()`，未使用 `check_if_modified()`、`validate_object_key()` 等。  
  导致 `GET /searches` 不支持 `If-Modified-Since-Version` → `304`，且 key 格式未校验。  
  受影响文件：`zotero_server/routers/searches.py`。

- [x] **Fix：`/keys/current` 与 `POST /keys` 返回的 access 语义应与数据库一致**  
  数据库默认 `access_json` 为 `files: false`，但代码中写死返回 `files: true`，且 groups 写死可写。  
  单人使用无感知，但会导致 admin 设置的权限被忽略。  
  受影响文件：`zotero_server/routers/keys.py`。

- [x] **Fix：Setting 删除日志 `key` 字段可能被截断**  
  `SyncDeleteLog.key` 定义为 `String(8)`，而 setting name（如 `tagColors`）可能超过 8 字符。  
  SQLite 当前不强制长度，但切换到 PostgreSQL/MySQL 时会报错或被截断。  
  受影响文件：`zotero_server/database.py`。

- [x] **Fix：批量上传 items/collections/searches 时，检查 library_type 限制**  
  `searches.py` 中 `_get_library()` 已拒绝 group，但 items 和 collections 的 `get_library()` 虽也拒绝，需确保 batch POST 错误提示一致清晰。  
  （属于确认项，如已一致则关闭。）

## P2：增强项（可做，不影响主同步流程）

- [ ] **Enhance：最小化 schema 校验（itemType / creatorType 白名单）**  
  当前只校验 `itemType` 存在和 key 格式。可额外校验：
  - itemType 是否在已知列表（使用已有的 `schema_data.ITEM_TYPES`）
  - creatorType 是否合法
  目的是防止客户端异常或未来协议变更导致脏数据写入。  
  受影响文件：`zotero_server/library.py`。

- [ ] **Docs：固化真实客户端回归测试步骤**  
  `progress.md` 已记录 Zotero 7.0.32 测试结果，建议整理成独立文档或脚本，方便后续升级客户端后快速验证。  
  受影响文件：新增 `docs/client-testing.md` 或在 `progress.md` 中扩充。

- [ ] **Enhance：引入最小数据库迁移机制（如 Alembic）**  
  当前启动时直接 `create_all`，适合从零开始，但后续字段/索引变更无法平滑升级已有数据库。  
  对长期运营的个人 VPS 有价值，短期可延后。  
  受影响文件：新增 migrations/ 目录及依赖。

---

## 不在本列表中的排除项（按 README 明确范围裁剪）

以下功能虽在参考分析中被提及，但属于 README 已声明的“不包含”或“架构决策”，当前不作修改：

- **Group Libraries**：README 明确“仅支持个人用户库（User Library）”。
- **全文索引（Full-Text）**：端点已为 stub，README 声明不影响正常使用。
- **ZFS 官方文件存储 API / S3 上传授权**：README 声明文件同步走 WebDAV。
- **`/keys/sessions` Web 登录流程**：README 声明仅支持 API Key 方式。
- **完整 Zotero API 查询参数**（`q`、`sort`、`style`、`sincetime` 等）：客户端同步主流程不需要。
- **多用户权限隔离/细粒度 key 权限**：README 定位是“个人”轻量服务器，当前 key 权限设计足以支撑。
