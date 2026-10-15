# Changelog

## 1.1.0 — 2026-10-15

### Documentation

Reworked both READMEs around symptoms, deliverables, a clearly labeled synthetic report, the 22-check matrix, and the audit → approval handoff → recheck workflow. Kept Agent Doctor branding and stable finding IDs. Installation instructions describe archives built from source, not nonexistent release assets.

### Audit instructions

- Consolidated action boundaries and made authorized, bounded native reads an affirmative default. Preserved production, credential, spending, write, and tool-side-effect constraints.
- Inlined all 22 investigation questions in the entry. Added heading/range-based reads, loaded-context reuse, tool-contract-aware limits, and explicit handling of truncation and unavailable bounded reads.
- Split evidence reads (60 calls / 60,000 characters) from internal instructions (20 / 20,000), with a combined 80 / 80,000 cap and precedence for tighter user or host limits. Included repeated reads, automatic entry injection, estimates, and stop conditions.
- Mapped natural-language requests to mode and focus. Explicit mode wins; an old report alone does not imply recheck. Missing baselines remain visible; narrower scope leaves other dimensions uninspected.
- Added symptom vocabulary without enabling implicit invocation in Claude Code, Codex, or OpenCode. Clear approval of a bounded plan still needs no special phrase; the audit returns a handoff rather than executing it.

### Validation

Added EVAL-33–EVAL-42 for bounded reading, budget accounting, input mapping, invocation policy, safe-read progress, and contextual approval. All 42 scenarios remain `not_run_with_agents`. Added offline regression tests for package structure and archive behavior; these do not evaluate agent reliability.

### Review decisions

The rewrite's information structure and practical reading guidance were adopted. Blanket internal-reference exemptions became bounded separate accounting. Automatic-trigger claims were not adopted because the shipped variants suppress implicit invocation. Claims that a particular count of negative instructions causes model paralysis, or that the changes save a fixed number of tokens, remain unverified and are not product guarantees. Model limitations remain a possible cause of poor results.

## 1.0.0 — 2026-10-15

Initial Agent Doctor source: 22 checks, evidence and counterevidence requirements, P0–P3 remediation, a separate verification queue, scoped approval handoffs, and read-only rechecks. Claude Code and portable packages share their body and references. Included 32 unevaluated behavioral scenarios and an offline package utility.
