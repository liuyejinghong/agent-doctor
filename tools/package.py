#!/usr/bin/env python3
"""Offline maintainer utility, never invoked by the audit skill. Python 3.9+."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "agent-doctor"
CLAUDE_FLAG = "disable-model-invocation: true\n"
EXPECTED_SCENARIOS = 42


def collect_and_check() -> tuple[dict[str, bytes], str]:
    """Check known package invariants; not a full YAML or behavioral validator."""
    paths = [ROOT / name for name in (
        "SKILL.md", "README.md", "README.zh-CN.md", "BUILD-VALIDATION.md", "CHANGELOG.md"
    )]
    for directory in ("agents", "assets", "references"):
        paths.extend(p for p in (ROOT / directory).rglob("*") if p.is_file())
    files: dict[str, bytes] = {}
    for path in sorted(paths):
        if path.is_symlink() or ROOT not in path.resolve().parents:
            raise ValueError(f"Unsafe package source: {path}")
        if path.suffix not in {".md", ".yaml", ".json"}:
            raise ValueError(f"Unexpected runtime file: {path}")
        files[path.relative_to(ROOT).as_posix()] = path.read_bytes()

    text = files["SKILL.md"].decode("utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not match:
        raise ValueError("Missing SKILL.md frontmatter")
    header = match.group(1)
    version = re.search(r'^  version: "(\d+\.\d+\.\d+)"$', header, re.M)
    if not version or f"name: {NAME}\n" not in header + "\n":
        raise ValueError("Invalid skill name or version")
    if text.count(CLAUDE_FLAG) != 1 or CLAUDE_FLAG.strip() not in header:
        raise ValueError("Expected exactly one Claude explicit-invocation flag")
    if len(text.splitlines()) >= 500 or "\nallowed-tools:" in text or "!`" in text:
        raise ValueError("Oversized entry or unexpected tool/dynamic execution field")
    for setting in ('  opencode/slash: "true"', '  opencode/autoinvoke: "false"'):
        if setting not in header.splitlines():
            raise ValueError(f"Missing metadata: {setting}")
    policy = files["agents/openai.yaml"].decode("utf-8")
    if "  allow_implicit_invocation: false" not in policy or f"${NAME}" not in policy:
        raise ValueError("Missing Codex explicit-invocation policy")

    expected_checks = {f"C{i:02d}" for i in range(1, 19)} | {f"G{i:02d}" for i in range(1, 5)}
    report = files["references/report-template.md"].decode("utf-8")
    checks = re.findall(r"^\| ([CG]\d{2}) \|", report, re.M)
    if len(checks) != 22 or set(checks) != expected_checks:
        raise ValueError("Coverage ledger must contain each of the 22 checks once")
    matrix = "\n".join(line for line in text.splitlines() if line.startswith("|"))
    entry_checks = re.findall(r"\b[CG]\d{2}\b", matrix)
    if len(entry_checks) != 22 or set(entry_checks) != expected_checks:
        raise ValueError("Entry matrix must define each of the 22 checks once")
    # Contract for the actual diagnostic deliverable, not merely a 22-item checklist.
    context_bytes = files.get("references/context-map.md")
    if context_bytes is None:
        raise ValueError("Missing required context map")
    context_map = context_bytes.decode("utf-8")
    if (text.find("## 1. 建立快照并还原上下文结构（必做）") < 0 or
            text.find("## 1. 建立快照并还原上下文结构（必做）") >= text.find("## 3. 用 22 项检查")):
        raise ValueError("Context diagnosis must precede the 22 checks")
    for document in (context_map, report):
        kinds = re.findall(r"^\| ([HRSTMOX]) ", document, re.M)
        if len(kinds) != 7 or set(kinds) != set("HRSTMOX"):
            raise ValueError("Context inventory must include seven source classes")
    required_states = ("已证实载入", "按规则推定", "仅发现配置", "已证实未载入", "未知")
    if any(state not in context_map or state not in report for state in required_states):
        raise ValueError("Context inventory missing evidence states")
    if any(item not in context_map for item in ("A：审计前", "B：Doctor", "C：审计")):
        raise ValueError("Context snapshot boundaries missing")
    if any(item not in report for item in ("进入路径与占用边界", "Doctor 本轮引入")):
        raise ValueError("Context measurement boundary missing")

    evaluation = json.loads(files["assets/eval-cases.json"])
    cases = evaluation["cases"]
    if evaluation["version"] != version.group(1) or evaluation["execution_status"] != "not_run_with_agents":
        raise ValueError("Unexpected evaluation version/status")
    if len(cases) != EXPECTED_SCENARIOS or {c["id"] for c in cases} != {f"EVAL-{i:02d}" for i in range(1, EXPECTED_SCENARIOS + 1)}:
        raise ValueError(f"Expected {EXPECTED_SCENARIOS} unique scenario IDs")
    scenario_index = files["references/acceptance-scenarios.md"].decode("utf-8")
    index_ids = re.findall(r"^\| (EVAL-\d{2}) \|", scenario_index, re.M)
    if len(index_ids) != len(cases) or set(index_ids) != {c["id"] for c in cases}:
        raise ValueError("Scenario index and JSON must match")
    for case in cases:
        if not all(case.get(k) for k in ("title", "setup", "request", "expected", "forbidden")):
            raise ValueError(f"Incomplete scenario: {case.get('id')}")

    for name, content in files.items():
        decoded = content.decode("utf-8")
        if "agent-" + "environment-audit" in decoded or "AEA-" in decoded or "AEA/VFY" in decoded:
            raise ValueError(f"Stale branding in {name}")
        if name.endswith(".md"):
            for target in re.findall(r"\[[^\]]+\]\(([^\s)]+)\)", decoded):
                if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                    continue
                resolved = (ROOT / name).parent.joinpath(target.split("#", 1)[0]).resolve()
                if ROOT not in resolved.parents or not resolved.exists():
                    raise ValueError(f"Broken/out-of-scope link in {name}: {target}")
    return files, version.group(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check structure only; do not write archives")
    parser.add_argument("--output", type=Path, default=ROOT / "dist", help="New archive destination")
    args = parser.parse_args()
    try:
        files, version = collect_and_check()
        print(f"Static structure checks passed: 22 coverage entries, {EXPECTED_SCENARIOS} unevaluated scenarios.")
        if args.check:
            return 0
        output = args.output.resolve()
        targets = [output / f"{NAME}-{variant}-v{version}.zip" for variant in ("claude-code", "portable")]
        if any(path.exists() for path in targets):
            raise FileExistsError("Archive already exists; choose a new --output directory")
        output.mkdir(parents=True, exist_ok=True)
        for variant, path in zip(("claude-code", "portable"), targets):
            with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, content in sorted(files.items()):
                    if variant == "portable" and name == "SKILL.md":
                        content = content.replace(CLAUDE_FLAG.encode("utf-8"), b"", 1)
                    info = zipfile.ZipInfo(f"{NAME}/{name}", date_time=(2026, 10, 15, 0, 0, 0))
                    info.create_system = 3
                    info.external_attr = 0o100644 << 16
                    info.compress_type = zipfile.ZIP_DEFLATED
                    archive.writestr(info, content)
            with zipfile.ZipFile(path) as archive:
                if archive.testzip() is not None:
                    raise ValueError(f"Archive integrity check failed: {path}")
            print(f"{path}\n  sha256: {hashlib.sha256(path.read_bytes()).hexdigest()}")
        return 0
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        print(f"Packaging failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
