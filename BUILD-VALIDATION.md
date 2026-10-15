# Validation — Agent Doctor 2.0.0

Executed on 2026-10-15 in the working Linux container, not the user's Mac or production environment.

## Executed

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`: **29 tests passed** (23 collector fixtures, 6 package tests). Tests use temporary synthetic files and clean them up.
- Collector tests cover Unicode source counts, manual-only large bodies, absence of history, exposed-but-uninvoked candidates, disabled bundles, plugin-child attribution, duplicate descriptions, event deduplication across copied logs, ambiguous names, partial logs, credential-output canaries, TOML declarations, import cycles, scope limits, symlink/FIFO refusal, read budgets and pagination.
- The real user-supplied plugin-list snapshot was replayed offline: **5 registry entries, 2 enabled declarations, 3 disabled declarations; 0 target files read**. This is a historical fixture result, not current runtime exposure. Its raw content is not committed.
- Entry frontmatter and Codex YAML parsed with a development-only YAML parser. This does not turn the runtime's conservative frontmatter subset into a full YAML implementation.
- Package tests cover metadata, runtime-only links, policy/growth guards, nine-file archives, variant parity, ZIP CRC, deterministic rebuilding and refusal to overwrite an existing archive.

## Not established

No live Claude Code/Codex/OpenCode behavioral evaluation, complete host-resolution compatibility, lifetime usage inference, numerical token savings, accuracy of semantic cleanup decisions or operating-system sandbox proof. The first v1 run is evidence of design problems, not a passing v2 model benchmark. The collector's source sizes and native host observations intentionally remain different metrics.

## Reproduce

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
python3 tools/package.py --check
python3 tools/package.py --output /new/output/directory
```

The final command creates distribution archives and is for source maintainers, not audit execution. Runtime collection itself has no file-write option. System access times and host logs are outside the collector's zero-target-write guarantee.
