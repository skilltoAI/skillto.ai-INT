# AMD-PAD 报表同步与 CRUD

## 入口与目标选择

- 网站报表：`http://192.168.3.188:5173/report-tables?table=<tableId>`。分享链接必须带具体表 ID；切换表会更新地址，刷新和前进后退恢复对应表。网站登录后进入全屏报表，使用“返回网站”退出工作区。
- API Key 管理：`http://192.168.3.188:5173/settings/api-keys`。创建只读或读写 Key，按需设置有效期；明文只显示一次，保存在受保护的运行期文件，不写入技能、源码、日志、URL 或报表。
- 远程 MCP：`http://192.168.3.188:5173/api/report-tables/mcp`。
- 远程 REST：`http://192.168.3.188:5173/api/report-tables/`。直接使用后端 `18080` 端口时去掉 `/api` 前缀。
- 远程部署：`/home/anycom/videoDeepInsight`；共享存储：项目 `data/report_tables/`，可由 `REPORT_TABLE_ROOT` 覆盖。不按用户隔离报表；Key 创建者只决定 Key 的管理归属。
- 本地工作区默认为 `~/skillto-table-data`，以实际 `SKILLTO_TABLE_ROOT` 为准，页面通常为 `http://127.0.0.1:8765/?table=<tableId>`。本地副本与远程副本独立。

执行请求前明确目标：AMD-PAD URL 表示远程操作，本地 URL 表示本地操作。来源、目标或覆盖意图不清楚时先确认，不同时修改两个副本，不自动更改其他任务的 MCP 配置。

## 配置 MCP 客户端

使用同一个 `scripts/server.py` stdio 入口；设置远程 URL 后，它转交 `scripts/remote_client.py`，不是另起一个报表网站。

```json
{
  "command": "python",
  "args": ["<agent-skill-root>/skillto-int-table/scripts/server.py"],
  "env": {
    "SKILLTO_TABLE_API_URL": "http://192.168.3.188:5173/api/report-tables/mcp",
    "SKILLTO_TABLE_API_KEY_FILE": "<受保护运行期目录>/amd-pad.key"
  }
}
```

本地模式不设置 `SKILLTO_TABLE_API_URL`，设置 `SKILLTO_TABLE_ROOT`。也支持 `SKILLTO_TABLE_API_KEY` 环境变量，但优先使用密钥文件，禁止展示真实值。远程失败必须明确报错，不落回本地写入。

连接后执行初始化、工具发现，再用 `table_workspace` 的 `list` 读取远程目录，确认目标表真实存在。客户端未注册 MCP 时不得宣称已连接；明确限制或启动 stdio bridge。HTTP MCP 是 JSON-RPC/Streamable HTTP，不是将 REST 请求直接发送到 MCP URL。

## 常用语义 CRUD

以下是 `tools/call` 的工具名与 `arguments` 示例；先读取实际 ID，示例占位符不能原样写入。

| 操作 | 工具 | arguments |
| --- | --- | --- |
| 浏览知识库、项目、表 | `table_workspace` | `{"action":"list"}` |
| 创建知识库 | `table_workspace` | `{"action":"create","level":"knowledge_base","name":"知识库名"}` |
| 创建项目 | `table_workspace` | `{"action":"create","level":"project","knowledgeBaseId":"<baseId>","name":"项目名"}` |
| 创建表 | `table_workspace` | `{"action":"create","level":"table","knowledgeBaseId":"<baseId>","projectId":"<projectId>","name":"报表名"}` |
| 读取字段 | `table_define` | `{"tableId":"<tableId>"}` |
| 查询行 | `table_query` | `{"tableId":"<tableId>","filters":[{"field":"averageCollects","operator":"gte","value":200}]}` |
| 新增记录 | `table_save_row` | `{"tableId":"<tableId>","action":"create","fields":{"accountName":"示例账号"}}` |
| 修改记录 | `table_save_row` | `{"tableId":"<tableId>","action":"update","rowId":"<rowId>","fields":{"accountName":"新名称"}}` |
| 删除记录 | `table_save_row` | `{"tableId":"<tableId>","action":"delete","rowId":"<rowId>"}` |
| 创建标签 | `table_tags` | `{"tableId":"<tableId>","action":"create","name":"对标账号","color":"#167d72"}` |
| 设置评分与标签 | `table_review` | `{"tableId":"<tableId>","rowId":"<rowId>","score":5,"note":"评分依据","tagIds":["<tagId>"]}` |
| 保存候选图选择 | `table_select_candidates` | `{"tableId":"<tableId>","rowId":"<rowId>","imageFields":["candidateImageA"]}` |

- 字段定义通过 `table_define.fields` 提交完整 schema；先读取并合并已有定义，不能为新增一列覆盖其他列。选择字段要给 `options`，类型按 `references/schema.md`。
- 更新行只提交要改的字段，保留其他字段、媒体和历史。`tagIds`、`imageFields` 是完整选择列表；追加标签先读当前列表并去重，不能丢失原有选择。`[]` 表示清空。
- 范围是包含边界；严格大于/小于条件应在查询后再次检查边界和缺失值。标签定义仅属于当前表，不跨表复用 tag ID。
- 重命名与删除目录对象使用 `table_workspace`，同时传父级 ID 与目标 `id`。删除前须用户明确确认，非空对象要列出受影响后代，确认后才传 `cascade:true`；记录删除也需确认。不要用直接改 JSON 绕过历史和校验。
- 写入后再次 `table_query` 验证，并用具体表 URL 在网站刷新核对。只读 Key 不允许写入。

## REST、媒体与导入导出

REST 请求使用 `Authorization: Bearer <key>`；网页登录请求沿用 JWT。`GET catalog` 浏览目录，`GET table?id=<tableId>` 导出完整表数据；`POST workspace/define/query/row/review/tags/candidates` 对应上面的语义操作。

媒体上传用 `POST upload/<tableId>`，`multipart/form-data` 字段名为 `file`。返回 `src` 后再通过行更新写入对应 image/video 字段；上传本身不自动关联记录。读取媒体同样要鉴权，网站使用登录会话建立的短期 Cookie。不要把 Windows 文件路径或本地 8765 媒体 URL 当成 AMD-PAD 可用媒体。

`POST import` 参数为 `{"tableId":"<tableId>","data":<导出的表数据>}`，是替换式导入，不是自动增量合并。网站也支持导入/导出 JSON；导入前备份目标，确认覆盖范围，核对字段、标签、评分和历史。七个语义 MCP 工具目前不包含文件上传或整表导入，使用已有 REST，不编造额外 MCP 工具。

## “同步”的实际含义

1. **网页与 MCP 同步**：远程网站、REST、MCP 读写同一个共享工作区；写入保存后，另一客户端重新查询/刷新即可看到。页面“刷新”只是重新读取远程数据，不会抓取本地副本。
2. **首次整库复制**：项目 `backend/scripts/copy_skillto_tables.py --source <source> --destination <empty-destination>` 在源锁下复制目录、表和媒体，保留稳定 ID、未知字段及历史；目标必须为空。它不是远程传输 CLI，也不是重复同步工具，需要先生成锁定快照并通过授权部署流程传输。
3. **两端已有数据的单向更新**：明确来源、目标、表范围和覆盖/合并规则；分别读取两端并备份目标。少量记录使用 MCP 逐行更新；整表替换须明确确认后用 REST import。新增记录会分配 ID，不能假称跨端行 ID 自动保留。需要保留全部 ID 的整库迁移走锁定快照和空目标复制。
4. **冲突处理**：两端同表 ID 不代表内容一致。两端都改过且缺少确定合并规则时停止覆盖，列出冲突供用户选择；不实施静默双向同步，不把本地历史覆盖远程新历史。
5. **媒体处理**：外部 URL 保留；本机媒体先确认实际文件，再复制或上传并重写引用。核对数量和校验值，列出缺失项。不要复制 API Key 数据库、凭据或浏览器缓存来实现报表同步。

只复制到准备好的空目标；禁止为了通过初始复制脚本而清空线上 `data/report_tables`。远程不可达时停止，保留本地源不变；传输失败不宣称同步完成。

## 验收与排错

- 输出来源与目标、具体表 URL、操作数量、未同步项和冲突；核对表/行 ID、记录数、字段、标签、评分、历史与媒体可读性。
- 401：检查 Key 是否缺失、过期或撤销；403：检查读写权限和浏览器 Origin；连接失败：检查 AMD-PAD 网络与服务。不打印 Key/JWT 调试。
- MCP 写入后远程网页刷新可见，网页编辑后 MCP 查询可见；本地副本不会自动改变。
- 维护依据：项目 `技术规范.md` 和 `docs/多媒体报表与MCP技术规范.md`。定点部署先备份；不覆盖 `.env`、Compose 或原业务数据库，不重启无关 Worker/模型。公网访问须 HTTPS。
