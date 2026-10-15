# Sources and scope decisions — 2026-10-15

The product brief is the owner's explicit request: inventory accumulated extensions, distinguish idle discovery overhead from invoked content, identify obsolete/duplicate/wrong-scope injections, and propose reversible changes without executing them. The original 18 reminders are inspiration, not a mandatory engineering audit.

## Current primary documentation

- Claude Code skills: https://code.claude.com/docs/en/skills — discovery versus invocation; manual controls; `/skill-doctor` availability; skill-list truncation, namespaces and symlink handling. These are runtime/version-dependent; local text lengths do not reproduce the final list.
- MCP: https://code.claude.com/docs/en/mcp — deferred tool definitions versus startup server instructions/names; proxy and model-specific fallbacks. No universal MCP startup-cost assumption.
- Plugin manifest: https://code.claude.com/docs/en/plugins-reference — bundle composition and custom component paths. The collector reports unsupported custom paths instead of executing code.
- Codex: https://developers.openai.com/codex/skills/ — discovery metadata, local skill paths and explicit invocation policy. The optional collector does not emulate all host overrides.
- OpenCode: https://opencode.ai/docs/skills/ and https://opencode.ai/docs/mcp-servers/ — skill discovery, MCP enablement and permissions. JSONC/dynamic plugin resolution needs separate evidence.
- Original inspiration: https://www.aicodingdictionary.com/ and https://www.aihero.dev/skills . No affiliation or claim of upstream endorsement.

## First-run evidence

The user-supplied installation/audit transcript showed five plugin-list entries with two enabled declarations and three disabled declarations, a CLI help entry for component/cost inspection, and a real command-rewriting hook. These motivate synthetic tests; they are not a benchmark of lifetime use or proof of the current environment. No raw transcript, private path, credential, repository-specific rules or personal history is shipped in fixtures.

## Validation distinction

Executed offline tests check computation, I/O boundaries and packaging. They do not measure real-agent decision quality. Native host statistics remain inputs, not secretly collected telemetry. Conflicting/absent evidence stays unknown; no inference of model degradation solely from extension count.
