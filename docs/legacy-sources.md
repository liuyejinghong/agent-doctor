# 来源与设计取舍

核对日期：2026-10-15。本包是面向用户需求的原创审计流程，不是 AIHero 官方 skill，也不是其仓库副本。没有打包上游 skill 正文、脚本或依赖。

## 参考资料

| 编号 | 来源 | 本包采用的有限依据 |
|---|---|---|
| S01 | The AI Coding Dictionary | 区分 model、harness、environment；区分确定性检查与 agent 审查；使用按需上下文与来源分层概念 |
| S02 | AIHero：retro | 从具体会话证据提出环境改进候选，审批前不自动修改；单次复盘不能代表环境全貌 |
| S03 | AIHero：writing-for-agents | 文本应改变行为，明确完成条件，降低重复与无关常驻内容 |
| S04 | AIHero：code-review | 需求正确性与工程标准分别审查，不让一个维度掩盖另一个 |
| S05 | AIHero：tdd | 关注可观察行为、有效断言与恰当测试边界，而非机械数量 |
| S06 | AIHero：domain-modeling | 用明确领域含义减少需求、代码与测试之间的歧义 |
| S07 | AIHero：codebase-design | 检查接口、实现与局部理解/验证成本，不只看目录样式 |
| S08 | AIHero：skills 总览 | 小职责能力组合；本包不要求安装该技能集合 |
| S09 | Agent Skills Specification | SKILL.md + YAML 元数据 + 按需 references 的可移植结构 |
| S10 | Claude Code：skills | 发现路径、显式调用、禁用隐式调用；allowed-tools 是预授权而非排他权限 |
| S11 | Codex：Build skills | .agents/skills 发现、显式 $skill、agents/openai.yaml 的隐式调用策略 |
| S12 | OpenCode：Agent Skills | 发现路径、metadata 的 slash/autoinvoke，以及 skill 访问权限与工具权限的区别 |

原始地址：

```text
S01 https://www.aicodingdictionary.com/
S02 https://www.aihero.dev/skills-retro
S03 https://www.aihero.dev/skills-writing-for-agents
S04 https://www.aihero.dev/skills-code-review
S05 https://www.aihero.dev/skills-tdd
S06 https://www.aihero.dev/skills-domain-modeling
S07 https://www.aihero.dev/skills-codebase-design
S08 https://www.aihero.dev/skills
S09 https://agentskills.io/specification
S10 https://code.claude.com/docs/en/skills
S11 https://developers.openai.com/codex/skills/
    本次转向 https://learn.chatgpt.com/docs/build-skills
S12 https://opencode.ai/docs/skills/
```

截图：用户本次提供的 18 项工作流问题，按原有顺序映射为 C01–C18。它们是检查假设，不是对用户的诊断结果。G01–G04 是为当前配置、安全、只读与验证隔离补充的治理项。

## 明确不照搬的判断

不把高 effort、长 skill、频繁人工审批或没有原型本身认定为错误；需要适用情境与可核查影响。

不采用“全局文件只能放导航”的绝对规则；必要的安全边界与业务不变量可以保留。判断性标准的放置取决于实际工作流，不让实现者丢失必要要求。

不把减少人工 review 等同于取消高风险人工责任，不将不同模型评审当成硬性要求，也不宣称子代理的嵌套能力在所有 harness 中相同。

本包额外设计了：全环境快照、22 项覆盖账本、反证与误报检查、未知状态、现有规则生命周期、根因去重、P0–P3、执行依赖、最小整改、审批交接和只读复查。这些是本包的操作设计，不是声称由上述资料证明的效果或行业标准。

## 验证边界

来源阅读与静态包检查不能证明在任意模型/客户端中行为正确。需要独立场景评测与宿主级权限验证；未对用户本机、私有仓库、真实会话或真实资金环境执行测试。

## 1.1.0 维护评审取舍

本次吸收外部 README 重写与五项优化建议，采用“症状与价值 → 报告示例 → 安装与体检矩阵 → 体检/审批/复查”的展示方式，保留 Agent Doctor 名称、既有编号与双语说明。

| 建议 | 采用方式与限制 |
|---|---|
| 收敛否定指令 | 合并动作边界，并明确已授权原生只读操作可直接执行；保留具体安全禁区。不把否定词数量与所谓“防御性瘫痪”写成已证实因果关系 |
| 明确渐进式读取 | 主入口内联 22 项取证问题，直接建账；按标题和范围读取细则。按当前工具契约限量，不假定所有客户端默认读全文，也不声称固定节省多少 token |
| 内部参考不占取证预算 | 取证与内部规则分别计量，各有上限并受合计上限约束；自动注入、重复读取与估算都披露。上限是设计参数，不是实验结果 |
| 自然语言映射参数 | 明确 mode/focus 与显式指令优先级；仅附旧报告不强制 recheck，缺基线不发明历史结论 |
| description 加症状词 | 采用用途提示，但保留全部显式调用策略；S10–S12 的关闭隐式调用设置不会因描述更丰富而变成自动触发 |

本次重新核对 S10–S12 中与调用控制有关的官方文档；这不是对所有原始资料或所有客户端版本的新一轮实机认证。“环境值得排查”不等于已经证明模型能力不是原因。未经对照测试，不承诺降低 token、减少漏触发或提高模型遵循率。
