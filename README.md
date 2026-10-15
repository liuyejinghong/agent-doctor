# Agent Doctor

**Diagnose your coding agent's environment. Get a prioritized treatment plan. Stay read-only.**

English | [简体中文](README.zh-CN.md)

Agent Doctor is an explicitly invoked skill that examines the environment around a coding agent: instructions, skills, tools, effective configuration, permissions, verification paths, and authorized session evidence. It explains which mechanisms cause repeated mistakes, unnecessary work, or unreliable completion claims, then produces an evidence-backed P0–P3 remediation board.

It is not a full code review, an installer, an auto-fixer, or a checklist demanding a particular tool stack. High effort, long reference files, and human review are not automatically defects.

## Read-only by design

The audit stays read-only, even after a remediation proposal is approved. Approval produces a scoped handoff for a separate execution stage; Agent Doctor can subsequently recheck the evidence.

During an audit it does not run project code, tests, builds, diagnostic scripts, or services; edit files or save reports; create issues or update boards; install dependencies; start extra agents or model requests; or access production systems and credentials.

**A prompt is not a sandbox.** Host permissions and tool isolation must enforce the actual boundary. Explicit invocation settings are not write protection. Existing tool hooks and side effects are part of the audit, not exemptions from it.

## Install

The repository-root `SKILL.md` is the Claude Code variant. Both installable variants are generated from that same source; the portable variant removes only Claude Code's `disable-model-invocation` field.

From a local clone of this repository, manually run:

```sh
python3 tools/package.py --check
python3 tools/package.py
```

This optional, standard-library-only maintenance tool validates the package structure and writes two ZIPs to `dist/`. It does not install the skill, use the network, or execute the project being audited. Existing ZIPs are not overwritten; use `--output <new-directory>` for another destination. The skill itself has no script dependency.

| Client | Archive | Copy the complete `agent-doctor/` directory to | Explicit invocation in the agent conversation |
|---|---|---|---|
| Claude Code | `agent-doctor-claude-code-v1.0.0.zip` | `.claude/skills/agent-doctor/` | `/agent-doctor` |
| Codex | `agent-doctor-portable-v1.0.0.zip` | `.agents/skills/agent-doctor/` | `$agent-doctor` |
| OpenCode | `agent-doctor-portable-v1.0.0.zip` | `.opencode/skills/agent-doctor/` | `/agent-doctor` in versions supporting the bundled metadata |

Install one variant in one discovery scope per host. Do not copy `SKILL.md` alone: it needs the reference files. Publishing or cloning this repository does not install it into your working projects. See [platform notes](references/platforms.md) for global paths and version limitations.

## First audit

Invoke the skill in your agent conversation and add:

```text
Read-only audit of the current project and authorized current-agent configuration.
Cover every dimension; prioritize rules/skills, tool output, automated checks,
and the review loop. Without session history, continue static inspection but
leave behavioral claims unknown. Do not execute project code, write files,
create external tasks, or start additional models or agents.
Show a P0–P3 remediation board first, then evidence, counterevidence, and
precise approval scopes. Respond in my language.
```

These are conversation instructions, not shell commands. Historical analysis is limited to the current project and the records explicitly authorized by the user. For `recheck`, supply the previous report and relevant current evidence; existing finding IDs are preserved.

## What you receive

A board of confirmed findings (`AD-001`, etc.) and a separate verification queue (`VFY-001`, etc.). Each finding includes its evidence, counterevidence, root cause, minimal remedy, constraints to preserve, alternatives, cost basis, dependencies, acceptance criteria, rollback, and approval scope.

| Priority | Meaning |
|---|---|
| P0 | Credible evidence of ongoing or imminent major harm; flag it without taking unilateral action. |
| P1 | Confirmed critical correctness gaps or recurring delivery blockers. |
| P2 | Evidence-backed inefficiency or unnecessary repeated work. |
| P3 | Optional, low-impact improvements. |

Coverage spans 18 workflow questions plus four governance checks: permission side effects, effective configuration, sensitive-data exposure, and verification isolation. Each is marked confirmed issue, no issue observed in the sample, unknown, not applicable, or not inspected. Sampling is bounded; a complete dimension ledger is not a claim to have read every file.

There is no aggregate health score to hide a critical issue, no invented percentage savings, and no obligation to produce findings for a healthy sample.

## Approval and recheck

Approve specific findings against a specific report and its listed action boundaries. The skill returns a restricted execution handoff, not an automatic fix. Permission to save a report does not authorize configuration changes, external publication, or extra model spending. Recheck distinguishes a static change from matching acceptance evidence and does not close external issues automatically.

See the [report template](references/report-template.md), [priority rules](references/priorities-and-remediation.md), and [approval handoff](references/approval-handoff.md).

## Validation status

Version **1.0.0**. Local package-structure checks are recorded in [BUILD-VALIDATION.md](BUILD-VALIDATION.md). The [32 behavioral scenarios](references/acceptance-scenarios.md) and [machine-readable cases](assets/eval-cases.json) are specifications, **not 32 passed agent tests**. Real-client discovery, invocation behavior, tool isolation, and model reliability have not been validated in this release.

The audit instructions and detailed references are currently written in Chinese; output follows the user's language. Both READMEs document the same behavior.

## Design references

Inspired by the AI Coding Dictionary and AIHero's skills material, especially evidence-driven retrospectives and progressive disclosure. This is an independent project, not an official AIHero skill or a repackaging of upstream skill code. See [sources and design decisions](references/sources.md).
