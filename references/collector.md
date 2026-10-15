# 离线采集器

`python3 -I -B <可信安装目录>/scripts/inspect_env.py ...`。Python 3.11+、macOS/Linux；只用标准库，无网络、shell 子进程、模型、插件加载或写入参数。没有 Python 或执行被拒时，使用原生有界读取或交付部分盘点，不绕过拒绝。宿主日志与访问时间不在零写入承诺范围内。

## 参数与范围

所有路径必须来自当前环境或明确授权。示例中 `$HOME` 只示意常见位置，实际采用已确认的配置路径。

```sh
python3 -I -B /trusted/agent-doctor/scripts/inspect_env.py \
  --claude-dir /authorized/.claude \
  --config /authorized/project/.mcp.json \
  --skills-dir /authorized/project/.claude/skills --limit 20
```

| 参数，可重复 | 只读处理 |
|---|---|
| `--claude-dir DIR` | settings 白名单、直接 skills、rules、commands、agents、插件安装登记及已授权范围内的启用包默认组件目录；不扫 projects/ 历史 |
| `--skills-dir DIR` | 直接子目录 SKILL.md；不自动递归到 synced/、备份或未声明嵌套目录 |
| `--plugin-dir DIR` | 明确包目录：manifest、默认 skills/commands/agents、hooks/hooks.json、.mcp.json；自定义 manifest 路径列缺口 |
| `--config FILE` | JSON 或 TOML 的 MCP 声明、enabledPlugins、hooks；不打印 env/args/URL/认证字段；JSONC 不自动猜解析 |
| `--rules-file FILE` | 字符/字节、相同规则、独占一行的 @file.md 导入链；只跟随已授权根内的目标 |
| `--session FILE` | 明确授权的 Claude Code JSONL：只计实际 Skill/MCP 调用与用户 slash 事件；不输出聊天、工具参数、隐藏推理 |
| `--plugin-list FILE` | 已保存的列表/安装登记，不运行 CLI 获取；外部包目录需另行授权 |

`--max-files 500 --max-bytes 8000000 --per-file 1000000` 限本地读取。`--offset N --limit 20` 控制返回页，每页最多 200 项，摘要列出总数/下一页；辅助列表亦有截断标记。每次分页重新本地计算，不写缓存。缺失、格式不支持、预算耗尽、symlink 不自动追踪均给原因。文件参数只授权该文件，不授权父目录。

这是**静态来源统计，不是完整宿主解析器**。YAML 仅支持常见顶层 scalar/block 子集，复杂语法为 partial；只读形态不自动套任何平台的加载优先级。配置启用不等于已注入。托管覆盖、CLI 设置、JSONC、插件定制加载路径、符号链接目标需原生接口或指定摘录补充。

## 结果与证据

`components` 含具体 ID/路径、父包、类型、作用域、启用声明、源字符数、正文大小、调用样本、暴露观测。`duplicate_source_groups` 给规范化相同文本的字符数和额外源副本量，**不是实测重复注入**。不输出整个描述/正文，模型只对重要候选读取必要片段。`gaps` 明示缺口；辅助列表截断时不能声称完整。

默认 `startup_tokens: null`。已经取得宿主统计时，可通过 `--observations FILE` 或 `--observations -` 输入以下**标准化格式**，不能编造数据来填空，也不要求另建文件：

```json
{"components":[{"id":"skill:来自本次清单的ID","state":"present","part":"discovery","tokens":120,"snapshot":"S0","phase":"before_doctor","source":"已提供的宿主截图/行号","basis":"host_measured"}]}
```

`state`: present/absent；`part`: discovery/instructions/tool_definitions/dynamic_output；`phase`: before_doctor/after_doctor；`basis`: host_measured/host_estimate。tokens/chars 至少一个非负整数；同组件只接收一个分项快照，冲突保留未知。更复杂的多分项可直接在对话表中表达，不硬塞本格式。

脚本不加总不同快照、不同单位或插件父子项，也不将 API 累计 usage 当驻留量。只在观测到正开销且授权样本调用为 0 时给出 P2 审核候选；依赖检查、代表性、实际优先级仍由审计者确认，不自动删除。规则和 hooks 没有调用数淘汰规则。

会话统计仅支持列明的 JSONL 事件形态，不包含引用文字中的调用、队列副本或子代理内部未提供的事件。同名映射歧义不归零。安装会话不是长期代表样本；缺会话数据为 null，不能声称“从未使用”。
