# Agent Doctor

English | [简体中文](README.zh-CN.md)

**Find the extensions you keep carrying into context, even when you do not use them.**

Over time, an agent environment accumulates MCP servers, skills, plugins, hooks and persistent rules. Agent Doctor inventories those components, measures what is observable, and proposes a reversible cleanup. It does not uninstall or change anything during an audit.

## What the report answers

| Question | Deliverable |
|---|---|
| What is installed or declared? | Component inventory, source, scope, enabled declarations, plugin-to-child relationships and gaps |
| What occupies context when idle? | Observed discovery text, tool definitions or instructions, separate from source sizes and invoked bodies |
| Is it used? | Calls, sessions used and last-use time in an explicitly authorized sample; unavailable history is not zero |
| What looks redundant or stale? | Exact duplicate descriptions/rules, unresolved imports, overlapping scopes and targeted semantic review |
| What should change first? | P0–P3 proposals: keep, manual invocation, project scope, lazy loading, merge or disable candidates; dependencies, lost capability and rollback |

A never-invoked skill may still have discovery overhead. A huge manual-only body may have none before invocation. A disabled plugin is not automatically current prompt load. Plugin parents and child components must not be double-counted. The audit checks these distinctions instead of equating installation size with wasted tokens.

## Install and run

Use the Claude Code or portable runtime archive and copy the complete `agent-doctor/` directory to **one** location:

| Client | Project installation | Invoke in the conversation |
|---|---|---|
| Claude Code | `.claude/skills/agent-doctor/` | `/agent-doctor` |
| Codex | `.agents/skills/agent-doctor/` | `$agent-doctor` |
| OpenCode | `.opencode/skills/agent-doctor/` | `/agent-doctor` on versions supporting the metadata |

For a personal Claude installation use `~/.claude/skills/agent-doctor/`. No build step is needed on the target machine. When updating v1, back up the complete old directory **outside discovery paths**, then replace it; do not overlay new files over stale audit references. Installation is a separate user-authorized action, not part of the read-only audit.

```text
/agent-doctor
Inspect my current extensions and persistent rules. Show individual components,
measured or estimated context burden, sample usage and reversible cleanup priorities.
```

The skill is explicit-only. Default scope no longer includes a compulsory 22-check engineering audit, CI review or an assessment of the user's work habits.

## Deterministic collection, not mental arithmetic

Prefer existing native component and usage reports. The optional [offline collector](references/collector.md) measures source sizes, plugin relationships, exact duplicate descriptions/rules and selected Claude JSONL invocation events without loading the inspected extensions.

```sh
python3 -I -B /trusted/agent-doctor/scripts/inspect_env.py \
  --claude-dir /authorized/.claude \
  --config /authorized/project/.mcp.json --limit 20
```

Python 3.11+, macOS/Linux, standard library only. Explicit paths, bounded reads, paged JSON stdout; no network, subprocess, model call, file-write option or automatic home/history traversal. The collector parses mixed configuration locally but omits commands, URLs, environment and credential values from output. Authentication files and unapproved symlink targets are refused.

It is not a complete host resolver: managed overrides, custom plugin loading paths, JSONC and unsupported YAML remain gaps. Native statistics can be supplied as normalized observations; without them, `startup_tokens` remains null. The skill still reports measurable source lengths and duplicates. Semantic overlap and dependencies require targeted review, not an automatic deletion algorithm.

## Approval and recheck

The report gives a component table and a prioritized board, including what would be removed from context and what capability might be lost. Zero sampled calls never grants permission to uninstall. A low-frequency recovery tool can be worth keeping.

Approve named findings and their scope to receive an execution handoff. A separate authorized execution stage applies the changes. Recheck compares the same host/snapshot basis and relevant capabilities; an old session may still retain earlier content.

[Collection contract](references/collector.md) · [Platform notes](references/platforms.md) · [Judgment rules](references/environment.md) · [Report layout](references/report-template.md)

## Development and validation

Version **2.0.0**. Source maintainers can run:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
python3 tools/package.py --check
python3 tools/package.py
```

Only the last command writes runtime ZIPs to `dist/`; it refuses to overwrite them. Tests use synthetic temporary environments. Tests of collection and packaging are not tests of real-agent decision accuracy. See [validation](https://github.com/liuyejinghong/agent-doctor/blob/main/BUILD-VALIDATION.md), [sources](https://github.com/liuyejinghong/agent-doctor/blob/main/docs/sources.md), and [changes](https://github.com/liuyejinghong/agent-doctor/blob/main/CHANGELOG.md).
