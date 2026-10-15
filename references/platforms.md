# 平台适配与安全安装

资料核对日期：2026-10-15。这里只说明本 skill 的发现/调用方式，不证明用户当前客户端版本或有效权限。证据来源见 `sources.md` 的 S09–S12。客户端、网关和托管策略可能不同，以当前实例为准。

## 分发变体

Claude Code 版的 `SKILL.md` 比通用版多一个顶层字段：`disable-model-invocation: true`。这是 Claude Code 扩展，不把它塞进要求严格标准字段的上传格式。

两个版本的正文和检查材料相同。通用版保留标准 `metadata`，并附带 Codex 的 `agents/openai.yaml`。不要把两个版本同时装到同一个宿主的多个发现目录，以免产生重名与维护漂移。

安装是用户选择的独立写入动作，不是体检运行过程。审计者不得自行把附件安装到项目，也不得替用户调用下载器或 package installer。

## Claude Code

项目级目标：`.claude/skills/agent-doctor/SKILL.md`。
个人级目标：`~/.claude/skills/agent-doctor/SKILL.md`。
只选一个作用域，复制整个目录，而不是只放入口文件。

在 Claude Code 对话中显式输入：

```text
/agent-doctor
只读体检当前项目和当前已授权的 agent 配置，输出 P0–P3 整改看板。
不得运行测试/构建/项目脚本，不保存文件，不创建外部任务。
```

`disable-model-invocation: true` 控制模型自行加载，不是读写隔离。`allowed-tools` 是调用预授权，不会移除其他工具；本包不包含它，也不附带 `context: fork`、hook 或动态 shell 注入。

要用宿主进一步约束，只在用户批准的独立配置步骤中设定：允许必要的原生读取、拒绝写入工具与可写 MCP、限制 shell/外部命令/网络。权限层级和匹配方式需按当前宿主核实，不能靠一份通用片段覆盖现有组织策略。某些 Plan 流程会保存计划文件，不把“Plan”标签当作磁盘零写入证据。

嵌套目录、worktree、插件与托管 skill 的发现可能不同；若名称冲突，查实际解析来源，不默认项目级一定优先。

## Codex

项目级目标：`.agents/skills/agent-doctor/`。
个人级目标：`~/.agents/skills/agent-doctor/`。
本包的 `agents/openai.yaml` 使用 `policy.allow_implicit_invocation: false`，保留显式调用。

在 Codex 对话中输入：

```text
$agent-doctor
只读体检当前项目。使用当前模型，不另开子代理，不运行项目代码。
给出证据、反证、优先级、整改验收和需批准的范围。
```

`$...` 是对话中的 skill 调用，不是在 shell 中执行。发现路径和 metadata 不设置沙箱；需由宿主实际读写/网络限制执行安全边界。不要为本 skill 自行升级模式或改变用户既有模型预算。

## OpenCode

项目级目标：`.opencode/skills/agent-doctor/`。
全局目标：`~/.config/opencode/skills/agent-doctor/`。
当前文档也列有 `.claude/skills`、`.agents/skills` 兼容发现路径；不要因此重复安装。

通用版采用字符串 metadata：

```yaml
metadata:
  opencode/slash: "true"
  opencode/autoinvoke: "false"
```

前者将 skill 暴露为 TUI 的 `/agent-doctor` 命令，后者从模型自动选择指引中隐藏。旧版是否支持这些键需核对，不能声称所有版本均已验证。

skill 访问权限（allow/ask/deny）与其执行期间工具权限是两个层次。允许读取 skill 不等于允许执行其中任何命令。必要时让用户显式要求加载该 skill；仍需按当前 OpenCode/agent 权限独立控制编辑、shell 与外部工具。

## 描述、自然语言与实际触发

三个适配都保留显式调用：Claude Code 的 `disable-model-invocation: true`；Codex 的 `policy.allow_implicit_invocation: false`；OpenCode 的 `opencode/autoinvoke: "false"`。OpenCode 的该设置使 skill 不出现在模型自动选择列表中，仍可按名称手动加载。实际效果需在对应客户端版本验证。

description 中的“找不到代码、上下文很快耗尽、改完无法验证”等症状用于解释用途和辅助显式选择，不承诺自动路由，也不改变授权范围。先显式调用，再解析自然语言的 audit/recheck/focus；仅提到症状不等于同意启动整套体检。若宿主忽略相应 metadata，应标明限制，而不是偷偷开启隐式调用。

## 被审计配置的候选来源

先用当前会话暴露的运行信息，再看当前项目入口与用户已授权配置。常见线索包括 `AGENTS.md`、`CLAUDE.md`、规则目录、上述 skill 目录、harness 设置、工具清单和启动配置。

这些只是候选，不是生效清单。明确区分：内容存在、能够被发现、实际触发、当前有效。特别核对子目录/工作树、全局覆盖、托管策略、同名 skill、网关参数覆盖。

不要整扫 home 来找全局配置。不能在返回模型前脱敏的混合配置，不整文件读取；不读 auth/token/key 等认证存储。没有生效证据时记录未知。
