# 平台采集适配（仅按当前平台读）

原则：现成原生清单/统计 → 本地有界元数据 → 对高价值候选补证。不为审计新开会话、调用模型或启动 MCP；不把工具名带 doctor 当作无副作用证明。优先利用用户已经提供的结果；可直接查询的只读接口须符合本机工具契约。

## Claude Code

安装：`.claude/skills/agent-doctor/` 或 `~/.claude/skills/agent-doctor/`，只选一个，调用 `/agent-doctor`。

优先取已存在的 `/context`、`/skill-doctor` 或插件管理器统计。`/skill-doctor` 的可用性受版本、feature flags 和连接方式限制；远程连接可能无法用。拿不到就继续静态盘点，不让整个诊断停在“缺 token”。不自动调用会建议/执行修复的 `/doctor`。

插件已有列表先区分 enabled 声明与当前会话加载；对启用候选在当前 CLI 明确支持时，可读取 `claude plugin details <已确认ID>` 的组件清单/预计开销。预计数不是实际 prompt。主会话原生只读接口不可用时，采集器可读已授权 `.claude` 目录和已有 JSON 列表，但不会自行执行这个命令。

skill 的发现信息、正文、参考文件分开；手动调用设置不能跨平台套用。列表可能被宿主截断、缩为 name-only，实际预算应用后的量与源 description 长度不同。插件子项有命名空间；同名和链接可能被宿主去重或覆盖，源目录重复不证明上下文重复。

MCP 区分名称/服务器说明、完整 schema、工具返回。第三方 gateway 与工具搜索配置可能改变是否延迟加载，**不能默认所有 MCP 都全量常驻，也不能默认全部无开销**。只报告明确设置和观测，勿输出网关凭据。全局 `.claude.json` 的嵌套项目配置不由脚本自动遍历，需当前项目的筛选结果。

## Codex

安装：`.agents/skills/agent-doctor/`，使用通用版，调用 `$agent-doctor`。保留 `agents/openai.yaml` 的显式调用策略；是否保留某种发现描述应由客户端证据确认，不因为禁止隐式调用就填 0 tokens。

采集器支持 `--skills-dir`、`--rules-file`、`--config <已授权 config.toml>` 的来源统计和 MCP 声明。skill 禁用项、组织策略、路径覆盖、生效状态用原生信息核对；Claude JSONL 使用解析器不用于 Codex transcript。没有适配的历史就保留未统计，不能编造兼容。

## OpenCode

安装：`.opencode/skills/agent-doctor/`，通用版；当前支持 metadata 的版本可用 `/agent-doctor`，否则按宿主方式显式选择。

采集器支持明确 skill 目录及 JSON MCP 声明；JSONC、动态 TypeScript 插件与完整 permission/工具覆盖不自动解释。禁止 import 插件来获得清单；manifest/源码只作为数据取证。MCP enabled 与 agent-specific tool permission 分开。实际支持的字段与加载方式以当前客户端为准。

## 安装与更新

复制完整运行包即可，无需在用户机器运行打包器，也无需新装依赖。已有同名目录先比较来源/版本，保留完整备份，移出发现目录，再用新包替换；**不要直接解压叠加留下旧参考规则**。这一步只有用户明确要求安装/更新时才执行，不属于只读体检。
