# Agent Doctor

English | [简体中文](README.zh-CN.md)

**Find the environment problems behind repeated coding-agent mistakes. Know what to fix first.**

Does your agent edit the wrong files, wander through the repository, fill its context with tool output, or finish without useful verification? Model capability is one possible factor. Instructions, tools, configuration, and feedback loops are also worth examining.

Agent Doctor is a **read-only environment-audit skill for Claude Code, Codex, and OpenCode**. **It reconstructs the sources and loading paths of your agent's context first**, then investigates tools, validation, and workflow. Evidence-backed findings become a P0–P3 remediation board. You choose what to change; a separate execution stage implements it.

## First deliverable: a context composition map

Before recommending changes, the skill must account for **what enters the current context, how, and why**: host instructions, global/project/directory rules, skill metadata vs. bodies, tool/MCP schemas, conversations/memory/compaction, tool results, and hooks/attachments/agent returns. Each category includes its source, trigger, observed loading state, measurement method, and evidence gap.

An installed skill is not necessarily loaded. Cumulative usage is not the current resident window. File characters are not exact tokens. If the host does not expose a pre-audit snapshot or category breakdown, the report says **unknown**, maps what can be proved, and requests the smallest missing evidence. The Doctor's own reading overhead is kept separate. See the [context reconstruction method](references/context-map.md).

## What you get

Not just “improve your prompt.” A report explains what is wrong, why the finding holds, what to fix first, what to preserve, and how to verify or roll back a change.

**Synthetic example only — these are not findings from a real repository:**

| Queue | ID | Priority | Finding or open question | Next step |
|---|---|---|---|---|
| Confirmed finding | AD-001 | P1 | `pytest \|\| true` at `scripts/check.sh:12` turns a failing check into success; remote merge protection is still unknown | Restore exit-code propagation while preserving existing checks; verify failing and passing fixtures in isolation |
| Verification hypothesis | VFY-001 | P2 | High effort is the default, but comparable cost and quality evidence is missing | Gather comparable evidence before deciding whether to change routing; do not lower effort globally |

A full report starts with a context composition inventory and loading paths, followed by an environment snapshot, a 22-item coverage ledger, a board, and evidence cards. Each card covers counterevidence, root cause, a minimal remedy, constraints to preserve, cost basis, dependencies, acceptance criteria, rollback, and approval scope. `AD-*` identifies evidence-backed findings; `VFY-*` identifies hypotheses needing verification. A verification priority expresses urgency to investigate, not certainty that an incident occurred.

| Priority | Meaning |
|---|---|
| P0 | Credible evidence of ongoing or imminent major harm; propose containment for approval |
| P1 | Critical correctness gaps or recurring delivery blockers |
| P2 | Evidence-backed repeated work, context waste, or other inefficiency |
| P3 | Low-impact cleanup or optional convenience that can wait |

There is no aggregate health score to hide a critical issue. A report with no findings can have an empty board.

## Quick installation

From a local copy of this repository, run:

```sh
python3 tools/package.py --check
python3 tools/package.py
```

These offline maintenance commands validate and build the archives. They do not install the skill or execute the project being audited. They require Python 3.9+; the skill itself has no script dependency. Output goes to `dist/`. Existing ZIPs are not overwritten; use `--output <new-directory>` to choose another destination.

| Client | Archive | Copy the complete `agent-doctor/` folder to | Invoke in the agent conversation |
|---|---|---|---|
| Claude Code | `agent-doctor-claude-code-v1.2.0.zip` | `.claude/skills/agent-doctor/` | `/agent-doctor` |
| Codex | `agent-doctor-portable-v1.2.0.zip` | `.agents/skills/agent-doctor/` | `$agent-doctor` |
| OpenCode | `agent-doctor-portable-v1.2.0.zip` | `.opencode/skills/agent-doctor/` | `/agent-doctor`, with support for the bundled metadata |

Choose one installation scope per client. Do not copy `SKILL.md` alone. Both variants share their body and references; the portable variant removes only Claude Code's `disable-model-invocation` field. See [platform notes](references/platforms.md) for global paths and invocation policies.

## The 22 checks

First reconstruct context sources and loading paths, then investigate the 22 checks according to risk and your focus. Every item ends as **confirmed issue, no issue observed in the sample, unknown, not applicable, or not inspected**.

| Dimension | Checks | Main questions |
|---|---|---|
| [Context and tools](references/context-and-tools.md) | C01 effort; C02 skill size; C06 tool output; C13 global instructions; C14 repository navigation; G02 effective configuration | What actually loads for this task? Is the information useful? Does the configuration take effect? |
| [Workflow and decisions](references/workflow-and-decisions.md) | C03 initial alignment; C04 excessive alignment; C08 retrospectives; C09 human review; C10 prototypes; C12 bounded autonomy; C15 shared language; C17 delivery strategy; C18 decision validation | Are goals and acceptance criteria clear? Which interactions are necessary decisions, and which are avoidable repetition? |
| [Verification and architecture](references/verification-and-architecture.md) | C05 automated checks; C07 automated review; C11 completion evidence; C16 test architecture; G04 isolation and recovery | Can checks catch relevant errors? Can the agent obtain appropriate completion evidence? |
| [Safety and scope](references/safety-and-scope.md) | G01 permissions and side effects; G03 sensitive data and outbound transfer | Is the read-only boundary actually enforced? Do tools or configuration create out-of-scope risks? |

Covering 22 dimensions is not a claim to have read every file. Large repositories are sampled by critical module, with uninspected areas disclosed.

## From audit to recheck

### 1. Run an audit

Explicitly invoke the skill, then describe the scope and focus. For example, in Claude Code or an OpenCode version supporting the metadata:

```text
/agent-doctor
Audit this project and authorized agent configuration. Focus on context use,
tool output, and automated verification. Continue static inspection without
session history. Show the board first, then evidence and approvable remedies.
```

Use `$agent-doctor` in Codex. These are conversation instructions, not terminal commands. Read-only and spending boundaries are built in; you do not need to repeat a long prohibition list.

**Even without host token telemetry, the report must include every context category and the known or unknown loading paths.** The default mode is `audit`. “Focus on tool output” changes the order, not the coverage ledger. An explicitly narrower scope is respected, with other items recorded as not inspected this run. History is limited to the visible conversation and authorized records for the current project; static settings do not establish your working habits.

### 2. Approve a plan and receive a handoff

```text
Approve AD-001 from this report and prepare an execution handoff limited to its
listed files, actions, verification, and side effects. Leave the other items
pending. Preserve uncommitted changes. No extra model calls, production access,
commits, or pushes.
```

A clear plan can be approved in ordinary language; no magic phrase or repeated approval is required. Permission to save a report covers only that action. **Agent Doctor does not apply fixes.** Give its handoff to a separate execution session, which works within the approved scope.

### 3. Recheck after implementation

```text
/agent-doctor
Recheck AD-001 from the previous report. The report and current changes are
provided; compare the original finding with the available acceptance evidence.
```

Requests to “recheck the previous findings” or “verify the remediation” map to `recheck`; an explicitly requested mode takes precedence. Attaching an old report alone does not switch modes. When the baseline is missing, inspect available current evidence and disclose the gap rather than inventing old IDs or closure claims.

Recheck preserves finding IDs and distinguishes a static edit from matching acceptance evidence. It does not run tests to fill gaps or automatically close issues and board cards.

## Why the findings are inspectable

**Evidence before judgment.** A configuration file is not proof it loaded. A test script is not proof it blocks errors. Each finding needs a real location, counterevidence, and consideration of alternative explanations.

**Useful mechanisms are preserved.** High effort, long reference documents, and human review can be appropriate. Before proposing deletion, establish what a rule or test protects. When an independent purpose cannot be ruled out, investigate first. Repair existing mechanisms before proposing another tool stack.

## Reading budgets

Project evidence and the skill's own instructions have separate counters. This keeps evidence coverage distinct from procedural overhead; internal references still consume context.

| Category | Default reading cap | Contents |
|---|---|---|
| Project evidence | 60 calls / 60,000 characters | Project files, configuration, authorized history, and other audited material |
| Internal instructions | 20 calls / 20,000 characters | The invoked Agent Doctor entry and its own references |
| Combined | 80 calls / 80,000 characters | Both categories together, subject to tighter user or host limits |

Read roughly 200 lines at a time, locate sections before expanding, and reuse loaded text. Reaching an applicable limit stops that category of reading and leaves disclosed gaps. Where precise measurement is unavailable, label estimates. These adjustable sampling budgets are not performance guarantees or API billing totals. See [safety and scope](references/safety-and-scope.md).

## Safety boundary

The audit reads authorized materials, analyzes existing evidence, and returns proposals in the conversation. Project tests, builds, diagnostic commands, file writes, external task updates, and installations belong in a separately approved execution stage. The audit does not start extra models or subagents, read credentials, or access production systems.

**A prompt is not a sandbox.** Explicit invocation controls loading, not write isolation. Actual protection depends on host permissions and tool constraints. A read path with known write side effects is stopped in favor of a safe alternative; authorized native reads with clear contracts can proceed without repeated confirmation.

## File guide

```text
agent-doctor/
├── SKILL.md                 # Boundaries, input mapping, six-step audit
├── README.md / README.zh-CN.md
├── agents/openai.yaml       # Codex explicit-invocation policy
├── references/              # Context map, 22 checks, report, handoff, platform notes
├── assets/eval-cases.json   # Synthetic behavioral evaluation cases
├── tools/package.py         # Offline maintainer checks and packaging
├── tests/test_package.py    # Maintainer-tool regression tests, not agent evals
├── CHANGELOG.md             # Version changes and review decisions
└── BUILD-VALIDATION.md      # Executed checks and unverified areas
```

[Report template](references/report-template.md) · [Priority rules](references/priorities-and-remediation.md) · [Approval handoff](references/approval-handoff.md)

## Validation and sources

Version **1.2.0**. See [BUILD-VALIDATION.md](BUILD-VALIDATION.md) for reproducible structure checks, maintainer-tool tests, and limitations. **The 42 synthetic behavioral scenarios have not been executed with real agents.** They are not 42 passed model tests. Real-client installation, invocation suppression, host isolation, and model reliability still need validation.

The design draws on the AI Coding Dictionary and AIHero's skills material. This is an independent project, not an official AIHero skill. Audit rules are currently written in Chinese; report output follows the user's language. See [sources and design decisions](references/sources.md) and the [changelog](CHANGELOG.md).
