# Agent Doctor

[English](README.md) | 简体中文

**找出那些装进 agent 环境后，不用也一直带着的东西。**

MCP、skills、插件和规则越装越多，哪些还在占位，哪些已经重复或过时？Agent Doctor 按组件盘点、测量和核对，给出可回滚的精简方案。体检期间不修改配置、不关闭或卸载任何组件。

## 它会告诉你什么

| 问题 | 具体交付 |
|---|---|
| 装了什么？ | 组件名称、来源、版本、作用域、启用声明、插件附带子组件、未查范围 |
| 不用时还占什么？ | 发现描述、工具定义、持久指令的可见开销；和磁盘正文、实际调用后内容分开 |
| 实际用过多少？ | 已授权样本里的调用次数、使用会话数、最近使用时间；没有记录不填 0 |
| 哪些值得精简？ | 重复描述/规则、失效导入、范围过宽、候选语义冲突、持续注入 |
| 应该先改什么？ | P0–P3 建议、可收回的内容、保留能力、依赖、验收和恢复方法 |

未调用的 skill 仍可能有发现描述开销；很长的手动 skill 正文未必常驻。关闭的插件不直接算负担；插件父包与子组件不重复累计。**不是按文件大小批量删工具，也不是再做一份 22 项工程审计。**

## 安装与使用

把运行包中完整的 `agent-doctor/` 放入一个发现目录：

| 客户端 | 项目级目录 | 对话中调用 |
|---|---|---|
| Claude Code | `.claude/skills/agent-doctor/` | `/agent-doctor` |
| Codex | `.agents/skills/agent-doctor/` | `$agent-doctor` |
| OpenCode | `.opencode/skills/agent-doctor/` | 支持包内 metadata 的版本用 `/agent-doctor` |

Claude Code 个人级也可用 `~/.claude/skills/agent-doctor/`，与项目级二选一。用户安装不需要运行打包脚本；Python 只供可选采集器使用。

从 v1 更新时，先把完整旧目录备份到**发现路径之外**，再用新包替换，避免叠加解压留下旧规则。安装/更新必须由用户单独提出，不包含在只读体检里。

```text
/agent-doctor
检查当前扩展与持久规则。按具体组件列出上下文负担、样本使用量和精简优先级。
```

默认只做环境盘点；不强制审查 CI、业务架构、原型数量、人工工作习惯，也不把刚才的安装复盘当作整个环境诊断。

## 有实际统计，不只靠模型估数

优先用现有原生清单和使用统计。信息不足时，[离线采集器](references/collector.md) 可统计文件/描述/正文大小、插件父子关系、重复文本、规则导入，以及指定 Claude JSONL 中的调用事件：

```sh
python3 -I -B /trusted/agent-doctor/scripts/inspect_env.py \
  --claude-dir /authorized/.claude \
  --config /authorized/project/.mcp.json --limit 20
```

仅 Python 3.11+ 标准库，面向 macOS/Linux；明确路径、有界读取、JSON 分页输出。**不联网、不调用模型、不执行插件或 hooks，没有写入/修复开关。** 混合配置在本地解析，只输出白名单元数据，不输出命令、URL、env 或凭据值；认证文件和未授权链接目标不读。

采集器不是宿主内部状态的完整模拟器。托管覆盖、插件自定义路径、JSONC、复杂 YAML 等会保留具体缺口；没有宿主遥测时 `startup_tokens` 为 null，但仍报告可测字符数和重复量。语义冲突、低频关键用途和依赖关系由 agent 针对候选核查。

## 精简不是失去能力

优先考虑保留、改手动调用、按项目启用、按需加载、合并入口，再考虑停用。零调用只代表授权样本内没看到，不代表永远无用。一个插件仍有有用子组件时，不建议整个关闭。

报告给出具体 ID、读数、证据、建议、损失的能力和恢复办法。批准指定范围后，Doctor 生成执行交接单；独立的获批执行阶段才实施。复查比较相同宿主和快照口径，并保留必要能力；旧会话中已经进入的内容不保证立即消失。

[采集参数](references/collector.md) · [平台差异](references/platforms.md) · [判断方法](references/environment.md) · [报告结构](references/report-template.md)

## 开发与验证

版本 **2.0.0**。维护者在源码副本中运行：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
python3 tools/package.py --check
python3 tools/package.py
```

最后一条才在 `dist/` 生成两个运行包，拒绝覆盖已有文件。测试使用合成环境，不连接真实服务。采集计算与打包测试通过，不等于真实模型判断已经可靠。详见[验证记录](https://github.com/liuyejinghong/agent-doctor/blob/main/BUILD-VALIDATION.md)、[资料来源](https://github.com/liuyejinghong/agent-doctor/blob/main/docs/sources.md)和[更新记录](https://github.com/liuyejinghong/agent-doctor/blob/main/CHANGELOG.md)。
