# 构建与验证边界（v1.2.0）

日期：2026-10-15。对象为 Agent Doctor 项目源码与分发包，**不是任何用户的真实 agent 工作环境**。

## 本次核验范围

- 入口必须把上下文结构还原设为第一阶段，并给出七类来源、五态加载证据、A/B/C 观测界限及文档链接；报告模板要求组成表、路径图、计量口径与 Doctor 本轮开销。
- 22 项 C01–C18/G01–G04 报告账本保持完整且不重复；`assets/eval-cases.json` 保持 42 个唯一编号且版本一致，其中 8 个场景改为针对真实上下文诊断的失败模式。
- SKILL.md 入口文件与内部 links、YAML 元数据、JSON 解析、Claude 专用字段差异、两种 ZIP 的 CRC/路径与正文一致性进行离线结构检查（详见实际验证命令/输出）。
- 不执行用户项目代码，不触碰生产，不验证真实用户会话。打包与维护检查属于开发时执行，不属于 Skill 运行时自动行为。

## 没有完成的验证

- **42 个行为场景尚未在 Claude Code/Codex/OpenCode 上运行。** 场景定义存在不意味着表现合格。
- 并未证明 SDK/客户端中全部宿主 prompt 或工具 schema 可由 Skill 观察；缺少宿主用量分解时，本 Skill 只能提供有证据的部分路径与未知项。
- 未验证在真实项目的统计准确性、token 节省、风险修复效果或宿主权限隔离。实际效果需要带已知注入链/遥测的合成仓库及实机对照评测。

## 维护者可执行的离线检查

```sh
python3 tools/package.py --check
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
python3 tools/package.py
```

这些命令仅供对**仓库副本**的维护/发布测试，最终打包命令会新建 dist/ ZIP；不会由审计 Skill 自行调用。维护工具的通过结果不能替代行为评测。
