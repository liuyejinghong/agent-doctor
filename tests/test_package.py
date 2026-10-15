"""Offline maintainer regression tests; these do not execute behavioral agent evals."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("agent_doctor_package", ROOT / "tools/package.py")
assert SPEC is not None and SPEC.loader is not None
package = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package)


class PackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "source"
        files, _ = package.collect_and_check()
        for name, content in files.items():
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        (self.root / "tools").mkdir()
        shutil.copyfile(ROOT / "tools/package.py", self.root / "tools/package.py")

    def edit(self, name: str, old: str, new: str) -> None:
        target = self.root / name
        text = target.read_text(encoding="utf-8")
        self.assertIn(old, text)
        target.write_text(text.replace(old, new, 1), encoding="utf-8")

    def check(self):
        with patch.object(package, "ROOT", self.root):
            return package.collect_and_check()

    def cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.root / "tools/package.py"), *args],
            capture_output=True, text=True, timeout=15,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def snapshot(self) -> dict[str, bytes]:
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob("*") if p.is_file()}

    def test_valid_structure_and_documented_version(self) -> None:
        files, version = self.check()
        self.assertEqual(version, "1.2.0")
        self.assertEqual(len(files), 18)
        for name in ("README.md", "README.zh-CN.md", "BUILD-VALIDATION.md"):
            self.assertIn(version, files[name].decode())
        self.assertEqual(len(json.loads(files["assets/eval-cases.json"])["cases"]), 42)

    def test_missing_inline_check_rejected(self) -> None:
        self.edit("SKILL.md", "C18 决策", "决策")
        with self.assertRaisesRegex(ValueError, "Entry matrix"):
            self.check()

    def test_missing_context_map_rejected(self) -> None:
        (self.root / "references/context-map.md").unlink()
        with self.assertRaisesRegex(ValueError, "Missing required context map"):
            self.check()

    def test_missing_context_class_rejected(self) -> None:
        self.edit("references/context-map.md", "| T 工具定义 |", "| OMITTED 工具定义 |")
        with self.assertRaisesRegex(ValueError, "Context inventory"):
            self.check()

    def test_context_stage_must_precede_checklist(self) -> None:
        self.edit("SKILL.md", "## 1. 建立快照并还原上下文结构（必做）",
                  "## 3. 建立快照并还原上下文结构（必做）")
        with self.assertRaisesRegex(ValueError, "Context diagnosis must precede"):
            self.check()

    def test_report_must_include_doctor_overhead(self) -> None:
        self.edit("references/report-template.md", "- Doctor 本轮引入", "- Internal only")
        with self.assertRaisesRegex(ValueError, "Context measurement boundary"):
            self.check()

    def test_missing_report_check_rejected(self) -> None:
        self.edit("references/report-template.md", "| C14 |", "| OMITTED |")
        with self.assertRaisesRegex(ValueError, "Coverage ledger"):
            self.check()

    def test_codex_implicit_invocation_rejected(self) -> None:
        self.edit("agents/openai.yaml", "allow_implicit_invocation: false", "allow_implicit_invocation: true")
        with self.assertRaisesRegex(ValueError, "Codex"):
            self.check()

    def test_opencode_implicit_invocation_rejected(self) -> None:
        self.edit("SKILL.md", 'opencode/autoinvoke: "false"', 'opencode/autoinvoke: "true"')
        with self.assertRaisesRegex(ValueError, "metadata"):
            self.check()

    def test_dynamic_command_rejected(self) -> None:
        self.edit("SKILL.md", "## 操作边界", "!`echo unsafe`\n\n## 操作边界")
        with self.assertRaisesRegex(ValueError, "dynamic execution"):
            self.check()

    def test_broken_reference_rejected(self) -> None:
        self.edit("README.md", "# Agent Doctor", "# Agent Doctor\n[broken](missing.md)")
        with self.assertRaisesRegex(ValueError, "Broken/out-of-scope"):
            self.check()

    def test_duplicate_scenario_id_rejected(self) -> None:
        self.edit("assets/eval-cases.json", '"id": "EVAL-42"', '"id": "EVAL-41"')
        with self.assertRaisesRegex(ValueError, "unique scenario"):
            self.check()

    def test_scenario_index_drift_rejected(self) -> None:
        self.edit("references/acceptance-scenarios.md", "| EVAL-42 |", "| OMITTED |")
        with self.assertRaisesRegex(ValueError, "Scenario index"):
            self.check()

    def test_check_only_does_not_write(self) -> None:
        before = self.snapshot()
        result = self.cli("--check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.root / "dist").exists())

    def test_archives_equivalent_safe_and_reproducible(self) -> None:
        first = Path(self.temp.name) / "first"
        second = Path(self.temp.name) / "second"
        for destination in (first, second):
            result = self.cli("--output", str(destination))
            self.assertEqual(result.returncode, 0, result.stderr)
        archives = sorted(first.glob("*.zip"))
        self.assertEqual(len(archives), 2)
        content = []
        for archive in archives:
            self.assertEqual(archive.read_bytes(), (second / archive.name).read_bytes())
            with zipfile.ZipFile(archive) as z:
                self.assertIsNone(z.testzip())
                for name in z.namelist():
                    self.assertTrue(name.startswith("agent-doctor/"))
                    self.assertNotIn("..", Path(name).parts)
                    self.assertNotIn("tools", Path(name).parts)
                    self.assertNotIn("tests", Path(name).parts)
                    self.assertNotIn(".git", Path(name).parts)
                content.append({name: z.read(name) for name in z.namelist()})
        claude, portable = content
        key = "agent-doctor/SKILL.md"
        self.assertIn(package.CLAUDE_FLAG.encode(), claude[key])
        claude[key] = claude[key].replace(package.CLAUDE_FLAG.encode(), b"", 1)
        self.assertEqual(claude, portable)

    def test_existing_archives_are_preserved(self) -> None:
        output = Path(self.temp.name) / "existing"
        first = self.cli("--output", str(output))
        self.assertEqual(first.returncode, 0, first.stderr)
        before = {p.name: p.read_bytes() for p in output.iterdir()}
        second = self.cli("--output", str(output))
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("already exists", second.stderr)
        self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})


if __name__ == "__main__":
    unittest.main()
