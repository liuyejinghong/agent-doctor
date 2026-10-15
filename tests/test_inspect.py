"""Deterministic environment fixtures. No live model, no user configuration."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("inspect_env", ROOT / "scripts/inspect_env.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.r = m.Reader([self.root])
        self.inv = m.Inventory(self.r)

    def put(self, name, text):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def skill(self, name="spare", description="Rare task", manual=False):
        return self.put(f"skills/{name}/SKILL.md", f"---\nname: {name}\ndescription: {description}\ndisable-model-invocation: {str(manual).lower()}\n---\nDo the task.\n")

    def event(self, cid="c1", skill="spare", kind="assistant"):
        return {"type": kind, "timestamp": "2026-10-01T01:00:00Z", "message": {"content": [
            {"type": "tool_use", "id": cid, "name": "Skill", "input": {"skill": skill}}]}}

    def log(self, records):
        return self.put("session.jsonl", "\n".join(json.dumps(x) for x in records))

    def observe(self, row, **extra):
        item = {"id": row["id"], "state": "present", "part": "discovery", "tokens": 120,
                "snapshot": "S0", "phase": "before_doctor", "source": "synthetic-host-view", "basis": "host_measured"}
        item.update(extra)
        self.inv.observations({"components": [item]})

    def test_unicode_lengths_not_tokens(self):
        p = self.skill(description="中文😀")
        self.inv.skill(p, "user")
        row = next(iter(self.inv.rows.values()))
        self.assertEqual(row["source_metrics"]["description_chars"], 3)
        self.assertGreater(row["source_metrics"]["file_bytes_utf8"], row["source_metrics"]["file_chars"])
        self.assertIsNone(row["startup_tokens"])

    def test_manual_skill_large_body_is_not_startup_bloat(self):
        p = self.skill(manual=True)
        p.write_text(p.read_text() + "LONG" * 5000)
        self.inv.skill(p, "user")
        report = self.inv.report()
        self.assertEqual(report["components"][0]["discovery_policy"], "manual_only_declared")
        self.assertEqual(report["candidates"], [])
        self.assertIsNone(report["components"][0]["startup_tokens"])

    def test_zero_usage_requires_history_and_exposure(self):
        self.inv.skill(self.skill(), "user")
        self.assertIsNone(self.inv.report()["components"][0]["usage"])
        self.inv.session(self.log([self.event(skill="other")]))
        self.assertEqual(self.inv.report()["components"][0]["usage"]["calls"], 0)
        self.assertEqual(self.inv.report()["candidates"], [])
        self.observe(next(iter(self.inv.rows.values())))
        candidate = self.inv.report()["candidates"][0]
        self.assertFalse(candidate["automatic_removal"])
        self.assertIn("review_dependencies", candidate["action"])

    def test_disabled_bundle_not_selected(self):
        p = self.root / "bundle"
        self.put("bundle/.claude-plugin/plugin.json", '{"name":"pack"}')
        self.put("bundle/skills/a/SKILL.md", "---\nname: a\ndescription: A\n---\nBody")
        self.inv.plugin(p, enabled=False)
        parent = next(iter(self.inv.rows.values()))
        self.assertFalse(parent["configured_enabled"])
        self.assertFalse(parent["children_inspected"])
        self.assertEqual(len(self.inv.rows), 1)
        self.assertEqual(self.inv.report()["candidates"], [])

    def test_plugin_five_entries_two_enabled_three_disabled(self):
        data = [{"id": f"p{i}@market", "enabled": i < 2, "scope": "user"} for i in range(5)]
        self.inv.plugin_list(data, "synthetic-list")
        report = self.inv.report()
        self.assertEqual(report["by_kind"]["plugin"], 5)
        self.assertEqual(sum(r["configured_enabled"] is True for r in report["components"]), 2)
        self.assertTrue(all(r["startup_tokens"] is None for r in report["components"]))

    def test_duplicate_descriptions_do_not_prove_duplicate_injection(self):
        self.inv.skill(self.skill("one"), "user")
        self.inv.skill(self.skill("two"), "user")
        report = self.inv.report()
        self.assertEqual(len(report["duplicate_source_groups"]), 1)
        self.assertEqual(report["candidates"], [])

    def test_bundle_use_is_not_inferred_from_parent_installation(self):
        self.put("bundle/.claude-plugin/plugin.json", '{"name":"pack"}')
        self.put("bundle/skills/a/SKILL.md", "---\nname: a\ndescription: A\n---\nBody")
        self.inv.plugin(self.root / "bundle", enabled=True)
        self.inv.session(self.log([self.event(skill="pack:a")]))
        report = self.inv.report()
        child = next(r for r in report["components"] if r["kind"] == "skill")
        parent = next(r for r in report["components"] if r["kind"] == "plugin")
        self.assertEqual(child["usage"]["calls"], 1)
        self.assertIsNone(parent["startup_tokens"])
        self.assertIn(child["id"], parent["children"])

    def test_namespaced_and_repeated_events_count_once(self):
        self.inv.skill(self.skill(), "user")
        event = self.event()
        self.inv.session(self.log([event, event, {"type": "queue-operation", "message": event["message"]}]))
        self.assertEqual(self.inv.report()["components"][0]["usage"]["calls"], 1)

    def test_ambiguous_skill_names_are_not_zero(self):
        self.inv.skill(self.skill(), "user")
        second = self.put("other/SKILL.md", "---\nname: spare\ndescription: D\n---\nOther")
        self.inv.skill(second, "project")
        self.inv.session(self.log([self.event()]))
        self.assertTrue(all(r["usage"]["calls"] is None for r in self.inv.report()["components"]))

    def test_config_does_not_print_credentials_or_commands(self):
        p = self.put("settings.json", json.dumps({"env": {"TOKEN": "SECRET_CANARY"}, "mcpServers": {"server": {
            "url": "https://SECRET_CANARY", "command": "touch SECRET_CANARY", "env": {"key": "SECRET_CANARY"}, "alwaysLoad": True}},
            "hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "touch SECRET_CANARY"}]}]}}))
        self.inv.config(p, "user")
        output = json.dumps(self.inv.report())
        self.assertNotIn("SECRET_CANARY", output)
        self.assertFalse((self.root / "SECRET_CANARY").exists())
        self.assertEqual(self.inv.report()["by_kind"], {"mcp": 1, "hook": 1})

    def test_toml_mcp_declarations(self):
        p = self.put("config.toml", '[mcp_servers.search]\nenabled = false\ncommand = "secret"\n')
        self.inv.config(p, "codex")
        row = self.inv.report()["components"][0]
        self.assertIs(row["configured_enabled"], False)
        self.assertEqual(row["exposure"], "unknown")

    def test_rule_cycle_and_missing_import(self):
        a = self.put("CLAUDE.md", "@R.md\n@missing.md\n")
        self.put("R.md", "@CLAUDE.md\n")
        self.inv.rule(a, "user")
        self.assertEqual(len(self.inv.rows), 2)
        edges = next(r for r in self.inv.rows.values() if r["name"] == "CLAUDE.md")["imports"]
        self.assertEqual(edges[1]["target_state"], "missing")

    def test_explicit_file_does_not_grant_parent(self):
        p = self.put("CLAUDE.md", "@other.md\n")
        self.put("other.md", "Hidden")
        inv = m.Inventory(m.Reader([p]))
        inv.rule(p, "user")
        self.assertEqual(len(inv.rows), 1)
        self.assertEqual(inv.report()["components"][0]["imports"][0]["target_state"], "outside_authorized_roots")

    def test_symlinks_and_credentials_refused(self):
        p = self.put("secret.md", "CANARY")
        link = self.root / "link.md"
        link.symlink_to(p)
        self.assertIsNone(self.r.text(link))
        self.assertIsNone(self.r.text(self.put("auth.json", '{"key":"CANARY"}')))
        self.assertIsNone(self.r.text(self.put(".env", 'SECRET=CANARY')))

    def test_fifo_does_not_hang(self):
        p = self.root / "fifo.md"
        os.mkfifo(p)
        self.assertIsNone(self.r.text(p))

    def test_byte_and_file_budgets(self):
        p = self.skill()
        r = m.Reader([self.root], max_files=1, per_file=1)
        self.assertIsNone(r.text(p))
        self.assertEqual(r.bytes, 0)
        r = m.Reader([self.root], max_files=1)
        self.assertIsNotNone(r.text(p))
        self.assertIsNone(r.text(self.put("next.md", "X")))
        self.assertEqual(r.files, 1)

    def test_complex_yaml_is_partial_not_silently_loaded(self):
        p = self.skill(description="!custom dangerous")
        self.inv.skill(p, "user")
        row = self.inv.report()["components"][0]
        self.assertEqual(row["parse_status"], "partial")
        self.assertEqual(row["discovery_policy"], "unknown")

    def test_multiline_description(self):
        meta, _, _ = m.frontmatter("---\nname: s\ndescription: >-\n  First line.\n  Second line.\n---\nBody")
        self.assertEqual(meta["description"], "First line. Second line.")

    def test_invalid_and_conflicting_observations_stay_unknown(self):
        self.inv.skill(self.skill(), "user")
        row = next(iter(self.inv.rows.values()))
        self.observe(row, tokens=-1, chars=100)
        self.assertIsNone(row["startup_tokens"])
        item = {"id": row["id"], "state": "present", "part": "discovery", "tokens": 120,
                "snapshot": "S0", "phase": "before_doctor", "source": "fixture", "basis": "host_measured"}
        self.inv.observations({"components": [item, item, item]})
        self.assertIsNone(row["startup_tokens"])

    def test_no_subprocess_network_or_model_code_in_collector(self):
        import ast
        tree = ast.parse((ROOT / "scripts/inspect_env.py").read_text())
        modules = {n.name.split('.')[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for n in node.names}
        self.assertFalse(modules & {"subprocess", "socket", "requests", "urllib", "openai", "anthropic"})
        called = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertFalse(called & {"eval", "exec", "compile"})

    def test_duplicate_session_files_use_record_identity(self):
        self.inv.skill(self.skill(), "user")
        event = self.event()
        event["sessionId"] = "same-session"
        first = self.log([event])
        second = self.put("copy.jsonl", first.read_text())
        self.inv.session(first)
        self.inv.session(second)
        usage = self.inv.report()["components"][0]["usage"]
        self.assertEqual(usage["calls"], 1)
        self.assertEqual(usage["sessions_sampled"], 1)

    def test_incomplete_log_does_not_support_zero_use(self):
        self.inv.skill(self.skill(), "user")
        p = self.log([self.event(skill="other")])
        p.write_text(p.read_text() + "\n{truncated")
        self.inv.session(p)
        self.assertIsNone(self.inv.report()["components"][0]["usage"]["calls"])

    def test_cli_read_only_and_pagination(self):
        self.skill("one")
        self.skill("two")
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'scripts/inspect_env.py'),
                                 '--skills-dir', str(self.root / 'skills'), '--limit', '1'],
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['components_count'], 2)
        self.assertEqual(len(data['components']), 1)
        self.assertEqual(data['page']['next_offset'], 1)
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})


if __name__ == '__main__':
    unittest.main()
