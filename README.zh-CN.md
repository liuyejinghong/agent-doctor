# Agent Doctor · Agent 工作环境体检

[English](README.md) | 简体中文

版本：1.0.0 · 初始版本：2026-10-15

检测当前 coding agent 的工作条件，解释什么机制导致反复出错、低效探索、上下文浪费或验证不足，输出可批准的 P0–P3 整改看板。

不是代码全量审查，不要求安装某一套第三方 skills，也不因为“规则多、effort 高、人工审核多”就判定不好。

## 最重要的边界

**本 skill 一直只读。** 它检查并提出方案，不运行项目测试/构建/脚本，不创建报告文件或外部任务，不修改环境，不自行增加模型或子代理。用户批准具体方案后，它只生成有边界的执行交接单；另一个获批执行阶段完成整改，再由本 skill 只读复查。

只读提示词不等于安全隔离。要防工具误操作，还需要实际宿主权限/沙箱支持。包内没有写入权限预授权、安装脚本、自动 hook 或动态执行命令。

## 选择一个版本

仓库根目录的 `SKILL.md` 是 Claude Code 版。通用版由同一份源文件生成，仅移除 Claude Code 专用的显式调用字段，避免维护两份正文。

在克隆后的本仓库根目录，手动运行以下维护命令可生成两个安装包；它不会安装 skill、访问网络或运行被审计项目：

```sh
python3 tools/package.py --check
python3 tools/package.py
```

输出在 `dist/`；已有同名包时拒绝覆盖，可以用 `--output <新目录>` 指定其他输出目录。Python 仅用于可选的维护打包，skill 运行不依赖脚本。


- `agent-doctor-claude-code-v1.0.0.zip`：Claude Code 版；额外设置 `disable-model-invocation: true`。
- `agent-doctor-portable-v1.0.0.zip`：标准字段版，适合 Codex/OpenCode；附 Codex 显式调用策略与 OpenCode metadata。

两个版本使用相同审计正文与参考材料。不要给同一个宿主重复安装两个版本。请复制 ZIP 内整个 `agent-doctor` 目录，单独复制 SKILL.md 会缺少检查规则。

## 安装位置与调用

安装是你选择的独立文件复制动作。解压对应安装包，将其中完整的 `agent-doctor/` 目录复制到下表的一处目标位置；上传此仓库不等于安装到你的工作项目或全局环境。

| 客户端 | 项目级目录 | 对话中的调用 |
|---|---|---|
| Claude Code | `.claude/skills/agent-doctor/` | `/agent-doctor` |
| Codex | `.agents/skills/agent-doctor/` | `$agent-doctor` |
| OpenCode | `.opencode/skills/agent-doctor/` | 当前支持本包 metadata 的版本可用 `/agent-doctor` |

全局路径、版本差异、权限边界见 `references/platforms.md`，来源见 `references/sources.md`。没有承诺所有旧版客户端兼容。

## 第一次体检

在客户端对话中调用 skill 后，附上：

```text
检查当前项目及已授权可读的当前 agent 配置。
覆盖所有检查维度，优先看规则/skills、工具输出、自动验证和审查闭环。
缺少历史记录时继续做静态检查，不推断我的使用习惯。
只读；不运行测试、构建、项目脚本，不写文件，不创建 Issue/看板卡片，
不额外调用模型或子代理。先给 P0–P3 整改看板，再给证据和可批准的方案。
```

这是自然语言任务参数，不是要求在终端执行的命令，也没有额外 CLI 解析器。

历史分析：需要你提供/明确授权当前项目的会话记录范围；不默认遍历全部历史。可先只读静态材料，后续再补日志。

复查：调用时说明 `recheck` 并给旧报告与当前证据位置。保留原 ID，区分静态改动与真正验收，不自动关闭外部任务。

## 你会得到什么

第一屏是优先级看板，不是一个含义不清的总分。每项问题都有实际证据、反证、根因、最小方案、保留项、成本、依赖、验收与回滚。未知进入补证队列，不伪装成失败。

覆盖设计输入中的 18 个工作流问题，以及权限副作用、配置实际生效、敏感信息外发、验证隔离四个补充项。每项标为：已证实问题、样本内未见问题、未知、不适用或未检查。

默认预算是有界取样，不等于逐文件全仓审计。大型项目记录未抽样子系统，完整维度覆盖不冒充完整代码覆盖。

## 审批例子

```text
批准本报告版本中的 AD-001 和 AD-003，按各自列明的文件、动作、
验证及副作用范围实施；其余项继续只读。先给独立执行会话的交接单。
不新增模型调用，不接触生产，不提交或推送，不覆盖已有未提交改动。
```

有精确计划时，无需某种固定口令。模糊的“继续”不被扩大成全局写权限。用户只批准保存报告时，也不扩展成修配置或同步看板。

## 文件结构

```text
agent-doctor/
  SKILL.md
  README.md
  README.zh-CN.md
  BUILD-VALIDATION.md
  agents/openai.yaml
  references/
    safety-and-scope.md
    context-and-tools.md
    workflow-and-decisions.md
    verification-and-architecture.md
    priorities-and-remediation.md
    report-template.md
    approval-handoff.md
    platforms.md
    acceptance-scenarios.md
    sources.md
  assets/eval-cases.json
  tools/package.py          # 仅仓库维护；不进入安装包
```

`tools/package.py` 只在维护者显式运行时进行结构校验或打包，不是自动 hook，也不会由本 skill 调用。

入口只包含边界与主流程；详细规则按检查项读取。没有必需的外部 skill、MCP、模型或脚本。

## 验证状态

已进行的静态检查记录在 `BUILD-VALIDATION.md`。32 个行为验收场景是可供后续评测的设计用例，不是“32 项模型测试通过”。尚未在你的真实环境执行，也未验证各客户端实机触发、工具隔离或不同模型的行为可靠性。

资料中的术语与方法已转化为具体检查假设；新增证据门、反证、审批交接与优先级是本包设计，不是第三方效果保证。详见来源说明。
