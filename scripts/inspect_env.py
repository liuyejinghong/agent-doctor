#!/usr/bin/env python3
"""Bounded offline inventory. Python 3.11+. Explicit paths, read-only, JSON stdout.

Never executes plugins, hooks, project code, subprocesses, network calls or models.
Static lengths are source measurements, NOT observed prompt tokens. See collector.md.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tomllib

VERSION = "2.0.0"
SENSITIVE = {"auth.json", ".credentials.json", "credentials.json", ".env", "id_rsa", "id_ed25519"}
PARTS = {"discovery", "instructions", "tool_definitions", "dynamic_output"}


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def label(value, fallback="unknown") -> str:
    value = str(value)
    return value if re.fullmatch(r"[\w.@:/+ -]{1,160}", value) else fallback


def number(value) -> bool:
    return type(value) is int and value >= 0


class Reader:
    def __init__(self, roots, max_files=500, max_bytes=8_000_000, per_file=1_000_000):
        self.roots = [Path(p).expanduser().resolve() for p in roots]
        self.max_files, self.max_bytes, self.per_file = max_files, max_bytes, per_file
        self.files = self.bytes = 0
        self.gaps = []
        self.cache = {}

    def gap(self, path, reason):
        item = {"source": str(path), "reason": reason}
        if item not in self.gaps:
            self.gaps.append(item)

    def allowed(self, path):
        p = Path(os.path.abspath(Path(path).expanduser()))
        roots = [r for r in self.roots if p == r or r in p.parents]
        if not roots:
            self.gap(p, "outside_authorized_roots")
            return False
        root = max(roots, key=lambda r: len(r.parts))
        for q in [p, *p.parents]:
            if q.is_symlink():
                self.gap(p, "symlink_not_followed")
                return False
            if q == root:
                break
        return True

    @staticmethod
    def open_fd(path, directory=False):
        # POSIX descriptor walk: no symlinked parent can redirect a later read.
        if not hasattr(os, "O_NOFOLLOW") or os.open not in os.supports_dir_fd:
            raise OSError("safe descriptor reads unavailable")
        parts = Path(path).parts
        fd = os.open(parts[0], os.O_RDONLY | os.O_DIRECTORY)
        try:
            for i, part in enumerate(parts[1:]):
                is_dir = directory or i < len(parts) - 2
                flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                if is_dir:
                    flags |= os.O_DIRECTORY
                new_fd = os.open(part, flags, dir_fd=fd)
                os.close(fd)
                fd = new_fd
            return fd
        except BaseException:
            os.close(fd)
            raise

    def text(self, path, optional=False):
        p = Path(os.path.abspath(Path(path).expanduser()))
        key = str(p)
        if key in self.cache:
            return self.cache[key]
        if p.name in SENSITIVE or p.name.startswith(".env."):
            self.gap(p, "credential_file_refused")
            return None
        if not self.allowed(p):
            return None
        if self.files >= self.max_files or self.bytes >= self.max_bytes:
            self.gap(p, "read_budget_exhausted")
            return None
        try:
            fd = self.open_fd(p)
            with os.fdopen(fd, "rb") as f:
                s = os.fstat(f.fileno())
                if not stat.S_ISREG(s.st_mode):
                    self.gap(p, "not_regular_file")
                    return None
                cap = min(self.per_file, self.max_bytes - self.bytes)
                if s.st_size > cap:
                    self.gap(p, "file_too_large")
                    return None
                data = f.read(cap + 1)
            self.files += 1
            self.bytes += len(data)
            if len(data) > cap:
                self.gap(p, "file_grew_past_limit")
                return None
            text = data.decode("utf-8-sig")
            self.cache[key] = text
            return text
        except FileNotFoundError:
            if not optional:
                self.gap(p, "not_found")
        except (OSError, UnicodeError):
            self.gap(p, "unreadable_or_non_utf8")
        return None

    def children(self, path):
        p = Path(path)
        if not self.allowed(p):
            return []
        try:
            out = []
            fd = self.open_fd(p, directory=True)
            try:
                with os.scandir(fd) as it:
                    for i, e in enumerate(it):
                        if i >= self.max_files:
                            self.gap(p, "directory_listing_truncated")
                            break
                        if not e.name.startswith("."):
                            out.append(p / e.name)
            finally:
                os.close(fd)
            return sorted(out)
        except OSError:
            self.gap(p, "directory_unavailable")
            return []

    def structured(self, path, optional=False):
        text = self.text(path, optional)
        if text is None:
            return None
        try:
            return tomllib.loads(text) if str(path).endswith(".toml") else json.loads(text)
        except (ValueError, RecursionError):
            self.gap(path, "unsupported_or_invalid_json_toml")
            return None


def frontmatter(text):
    """Conservative scalar/block subset; never load YAML tags, aliases or code."""
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
    if not match:
        return {}, text, "missing_frontmatter"
    header = match.group(1)
    result, uncertain = {}, False
    lines = header.splitlines()
    keys = {"name", "description", "when_to_use", "disable-model-invocation", "user-invocable"}
    for i, line in enumerate(lines):
        m = re.match(r"^([\w-]+):\s*(.*)$", line)
        if not m or m[1] not in keys:
            continue
        k, v = m.groups()
        if k in result:
            uncertain = True
        if v in (">", ">-", ">+", "|", "|-", "|+"):
            block = []
            for nxt in lines[i + 1:]:
                if nxt and not nxt[0].isspace():
                    break
                block.append(nxt.strip())
            v = (" " if v.startswith(">") else "\n").join(block)
        elif v.startswith('"'):
            try:
                v = json.loads(v)
            except ValueError:
                uncertain = True
                v = None
        elif v.startswith("'") and v.endswith("'"):
            v = v[1:-1].replace("''", "'")
        elif not v or v.startswith(("!", "&", "*", "[", "{")):
            uncertain = True
            v = None
        else:
            v = v.split(" #", 1)[0].strip()
        result[k] = v
    if result.get("disable-model-invocation") not in (None, "true", "false"):
        uncertain = True
    return result, text[match.end():], "partial" if uncertain else "scalar_subset"


class Inventory:
    def __init__(self, reader):
        self.r = reader
        self.rows = {}
        self.fingerprints = defaultdict(list)
        self.fingerprint_chars = {}
        self.plugin_flags = defaultdict(list)
        self.usage_events = []
        self.session_sources = []
        self.session_times = []
        self.seen_events = set()
        self.usage_incomplete = False
        self.session_identity_fallback = False

    def add(self, kind, source, name, scope, parent=None, aliases=()):
        identity = kind + ":" + str(source)
        cid = kind + ":" + digest(identity)[:12]
        if cid not in self.rows:
            self.rows[cid] = {
                "id": cid, "kind": kind, "name": label(name), "source": str(source),
                "scope": scope, "parent": parent, "configured_enabled": None, "dependencies_checked": False,
                "exposure": "unknown", "startup_tokens": None, "usage": None,
                "source_metrics": {}, "evidence": [], "aliases": sorted(set(aliases)),
            }
        return self.rows[cid]

    def skill(self, path, scope, parent=None, namespace=None):
        text = self.r.text(path)
        if text is None:
            return
        meta, body, parse = frontmatter(text)
        name = label(meta.get("name") or Path(path).parent.name)
        command = (namespace + ":" if namespace else "") + name
        row = self.add("skill", path, command, scope, parent, (command,))
        desc = meta.get("description")
        hint = meta.get("when_to_use")
        discovery = None if desc is None else name + " " + desc + (" " + hint if hint else "")
        row["source_metrics"] = {
            "file_bytes_utf8": len(text.encode("utf-8")), "file_chars": len(text),
            "body_chars": len(body), "description_chars": len(desc) if desc is not None else None,
            "discovery_source_chars": len(discovery) if discovery is not None else None,
        }
        row["invocation_setting"] = meta.get("disable-model-invocation")
        row["discovery_policy"] = ("manual_only_declared" if meta.get("disable-model-invocation") == "true"
                                   else "automatic_eligible_if_discovered" if parse == "scalar_subset" else "unknown")
        row["parse_status"] = parse
        row["evidence"] = ["frontmatter", "source_lengths_not_prompt_cost"]
        if desc:
            key = ("same_description", digest(" ".join(desc.split())))
            if row["id"] not in self.fingerprints[key]:
                self.fingerprints[key].append(row["id"])
            self.fingerprint_chars[key] = len(" ".join(desc.split()))
        row["body_sha256"] = digest(body)
        # Only count reference links: loading a skill must not read every reference.
        row["reference_links"] = len(re.findall(r"\]\((?![a-z]+:|#)[^\s)]+\)", body))

    def skills_dir(self, directory, scope, parent=None, namespace=None):
        for child in self.r.children(directory):
            if not self.r.allowed(child):
                continue
            if child.is_dir():
                if (child / "SKILL.md").exists():
                    self.skill(child / "SKILL.md", scope, parent, namespace)
                else:
                    self.r.gap(child, "not_a_direct_skill_root_not_recursed")

    def rule(self, path, scope, depth=0):
        source = str(Path(path).absolute())
        existing = any(r["kind"] == "rule" and r["source"] == source for r in self.rows.values())
        if existing:
            return
        text = self.r.text(path)
        if text is None:
            return
        row = self.add("rule", source, Path(path).name, scope)
        row["source_metrics"] = {"file_chars": len(text), "file_bytes_utf8": len(text.encode("utf-8"))}
        key = ("same_rule_text", digest(" ".join(text.split())))
        self.fingerprints[key].append(row["id"])
        self.fingerprint_chars[key] = len(" ".join(text.split()))
        row["imports"] = []
        for token in re.findall(r"(?m)^\s*@([^\s]+\.md)\s*$", text):
            if not re.fullmatch(r"[\w./~ -]+\.md", token):
                continue
            target = Path(token).expanduser()
            if not target.is_absolute():
                target = Path(path).parent / target
            target = Path(os.path.abspath(target))
            state = "outside_authorized_roots"
            if self.r.allowed(target):
                state = "present" if target.is_file() else "missing"
            row["imports"].append({"target": str(target), "target_state": state, "edge": "declared_import"})
            if state == "present" and depth < 5:
                self.rule(target, scope, depth + 1)
            elif state == "present":
                self.r.gap(target, "import_depth_limit")

    def config(self, path, scope, parent=None):
        obj = self.r.structured(path, optional=True)
        if not isinstance(obj, dict):
            return
        for name, enabled in obj.get("enabledPlugins", {}).items() if isinstance(obj.get("enabledPlugins"), dict) else []:
            if type(enabled) is bool:
                self.plugin_flags[name].append({"source": str(path), "value": enabled, "scope": scope})
        for key in ("mcpServers", "mcp_servers", "mcp"):
            servers = obj.get(key)
            if not isinstance(servers, dict):
                continue
            for name, definition in servers.items():
                if not isinstance(definition, dict):
                    continue
                row = self.add("mcp", str(path) + "#" + key + "/" + name, name, scope, parent, ("mcp:" + name,))
                row["configured_enabled"] = definition.get("enabled") if type(definition.get("enabled")) is bool else None
                row["always_load_setting"] = definition.get("alwaysLoad") if type(definition.get("alwaysLoad")) is bool else None
                row["transport"] = label(definition.get("type", "unspecified"))
                row["evidence"] = ["declared_server_only_not_connected"]
                # Do not print commands, args, URLs, headers, env or their values.
        hooks = obj.get("hooks")
        if isinstance(hooks, dict):
            for event, groups in hooks.items():
                if not isinstance(groups, list):
                    continue
                for i, group in enumerate(groups):
                    if not isinstance(group, dict):
                        continue
                    items = group.get("hooks", [])
                    if not isinstance(items, list):
                        continue
                    for j, hook in enumerate(items):
                        if not isinstance(hook, dict):
                            continue
                        row = self.add("hook", f"{path}#hooks/{event}/{i}/{j}", event, scope, parent)
                        row["hook_type"] = label(hook.get("type", "unknown"))
                        row["source_metrics"] = {"inline_prompt_chars": len(hook["prompt"]) if isinstance(hook.get("prompt"), str) else None}
                        row["evidence"] = ["declaration_not_execution_or_injection"]

    def markdown_dir(self, directory, kind, scope, parent=None, namespace=None):
        for path in self.r.children(directory):
            if path.suffix != ".md":
                self.r.gap(path, "nested_or_non_markdown_not_read")
                continue
            if kind == "rule":
                self.rule(path, scope)
                continue
            text = self.r.text(path)
            if text is None:
                continue
            meta, body, parse = frontmatter(text)
            name = (namespace + ":" if namespace else "") + label(meta.get("name") or path.stem)
            row = self.add(kind, path, name, scope, parent)
            row["source_metrics"] = {"file_chars": len(text), "body_chars": len(body),
                                     "description_chars": len(meta["description"]) if meta.get("description") else None}
            row["parse_status"] = parse

    def plugin(self, path, scope="plugin", enabled=None, display=None):
        path = Path(path)
        obj = self.r.structured(path / ".claude-plugin/plugin.json", optional=True)
        obj = obj if isinstance(obj, dict) else {}
        name = label(obj.get("name", display or path.name))
        row = self.add("plugin", path, display or name, scope)
        if enabled is not None:
            row["configured_enabled"] = enabled
        row["version"] = label(obj.get("version", "unknown"))
        row["evidence"] = ["bundle_parent_not_additive_cost"]
        if enabled is False:
            row["children"] = []
            row["children_inspected"] = False
            return
        row["children_inspected"] = True
        pid = row["id"]
        if (path / "skills").exists():
            self.skills_dir(path / "skills", scope, pid, name)
        if (path / "SKILL.md").exists():
            self.skill(path / "SKILL.md", scope, pid, name)
        for directory in ("commands", "agents"):
            if (path / directory).exists():
                for p in self.r.children(path / directory):
                    if p.suffix == ".md":
                        text = self.r.text(p)
                        if text is not None:
                            kind = "command" if directory == "commands" else "agent"
                            r = self.add(kind, p, name + ":" + p.stem, scope, pid)
                            r["source_metrics"] = {"file_chars": len(text)}
        self.config(path / ".claude-plugin/plugin.json", scope, pid)
        self.config(path / ".mcp.json", scope, pid)
        self.config(path / "hooks/hooks.json", scope, pid)
        for field in ("skills", "commands", "agents", "hooks", "mcpServers", "types"):
            if field in obj:
                self.r.gap(path, "custom_manifest_field_requires_targeted_read:" + field)
        row["children"] = [r["id"] for r in self.rows.values() if r["parent"] == pid]
        if enabled is False:
            for child in row["children"]:
                self.rows[child]["configured_enabled"] = False

    def plugin_list(self, data, source):
        entries = data if isinstance(data, list) else None
        if isinstance(data, dict) and isinstance(data.get("plugins"), dict):
            entries = []
            for name, values in data["plugins"].items():
                if isinstance(values, list):
                    entries.extend({**v, "id": name} for v in values if isinstance(v, dict))
        if entries is None:
            self.r.gap(source, "unsupported_plugin_list")
            return
        for item in entries:
            if not isinstance(item, dict):
                continue
            name = label(item.get("id", "unknown"))
            path = item.get("installPath")
            scope = label(item.get("scope", "unknown"))
            enabled = item.get("enabled") if type(item.get("enabled")) is bool else None
            flags = self.plugin_flags.get(name, [])
            if enabled is None and flags and len({x["value"] for x in flags}) == 1:
                enabled = flags[0]["value"]
            if isinstance(path, str) and Path(path).is_absolute() and self.r.allowed(Path(path)):
                self.plugin(Path(path), scope, enabled, name)
            else:
                row = self.add("plugin", str(source) + "#" + name, name, scope)
                row["configured_enabled"] = enabled
                row["evidence"] = ["registry_entry_components_not_read"]
                row["children"] = []

    def session(self, path):
        text = self.r.text(path)
        if text is None:
            self.usage_incomplete = True
            return
        file_session = digest(str(Path(path).absolute()))[:12]
        for index, line in enumerate(text.splitlines()):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except (ValueError, RecursionError):
                self.r.gap(path, "session_contains_invalid_lines")
                self.usage_incomplete = True
                continue
            if not isinstance(record, dict) or record.get("type") not in ("user", "assistant"):
                continue
            sid = record.get("sessionId")
            session = digest("session:" + sid)[:12] if isinstance(sid, str) and sid else file_session
            self.session_identity_fallback |= session == file_session
            self.session_sources.append(session)
            timestamp = record.get("timestamp")
            normalized_time = None
            if isinstance(timestamp, str):
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    if dt.tzinfo:
                        normalized_time = dt.astimezone(timezone.utc).isoformat()
                        self.session_times.append(normalized_time)
                except ValueError:
                    pass
            timestamp = normalized_time
            msg = record.get("message", {})
            if not isinstance(msg, dict):
                continue
            content = msg.get("content")
            events = []
            if record["type"] == "assistant" and isinstance(content, list):
                for node in content:
                    if not isinstance(node, dict) or node.get("type") != "tool_use":
                        continue
                    tool, args = node.get("name", ""), node.get("input", {})
                    if tool == "Skill" and isinstance(args, dict) and isinstance(args.get("skill"), str):
                        events.append((node.get("id"), args["skill"], timestamp))
                    elif isinstance(tool, str) and tool.startswith("mcp__") and len(tool.split("__")) >= 3:
                        events.append((node.get("id"), "mcp:" + tool.split("__")[1], timestamp))
            elif record["type"] == "user" and isinstance(content, str):
                command = re.search(r"<command-name>/([^<\s]+)</command-name>", content)
                if command:
                    events.append((record.get("uuid") or f"line:{index}", command[1], timestamp))
            for eid, alias, when in events:
                key = (session, str(eid))
                if eid is None:
                    self.r.gap(path, "usage_event_without_stable_id")
                    self.usage_incomplete = True
                    continue
                if key in self.seen_events:
                    continue
                self.seen_events.add(key)
                self.usage_events.append((alias, session, when))

    def usage(self):
        aliases = defaultdict(list)
        for row in self.rows.values():
            for a in row["aliases"]:
                aliases[a].append(row)
        by_id = defaultdict(list)
        for alias, session, when in self.usage_events:
            matches = aliases.get(alias, [])
            if len(matches) == 1:
                by_id[matches[0]["id"]].append((session, when))
            else:
                self.r.gap("usage:" + label(alias), "unresolved_or_ambiguous_alias")
        if not self.session_sources:
            return
        for row in self.rows.values():
            if row["kind"] not in ("skill", "mcp"):
                continue
            if any(len(aliases[a]) > 1 for a in row["aliases"]):
                row["usage"] = {"status": "ambiguous", "calls": None}
                continue
            events = by_id[row["id"]]
            times = [t for _, t in events if isinstance(t, str)]
            row["usage"] = {
                "status": "observed_in_supplied_files" if events else "not_observed_in_supplied_files",
                "calls": None if self.usage_incomplete else len(events), "calls_lower_bound": len(events),
                "sample_parse_complete": not self.usage_incomplete, "sessions_used": len({s for s, _ in events}),
                "sessions_sampled": len(set(self.session_sources)), "last_used": max(times) if times else None,
            }

    def observations(self, obj):
        # Optional normalized *existing* host measurements, not generated estimates.
        if not isinstance(obj, dict) or not isinstance(obj.get("components"), list):
            self.r.gap("observations", "invalid_observation_document")
            return
        seen = set()
        for item in obj["components"]:
            if not isinstance(item, dict):
                continue
            row = self.rows.get(item.get("id"))
            if row is None:
                self.r.gap("observations", "unknown_component_id")
                continue
            valid = (item.get("state") in ("present", "absent") and item.get("part") in PARTS
                     and bool(item.get("snapshot")) and isinstance(item.get("snapshot"), str)
                     and bool(item.get("source")) and isinstance(item.get("source"), str)
                     and item.get("basis") in ("host_measured", "host_estimate")
                     and all(number(item[k]) for k in ("tokens", "chars") if k in item)
                     and item.get("phase") in ("before_doctor", "after_doctor")
                     and any(number(item.get(k)) for k in ("tokens", "chars")))
            if not valid or row["id"] in seen:
                seen.add(row["id"])
                row["exposure"] = "conflicting_or_invalid_observations"
                row.pop("observation", None)
                row["startup_tokens"] = None
                self.r.gap(row["id"], "observation_requires_one_valid_measurement")
                continue
            seen.add(row["id"])
            if item["state"] == "absent" and any(item.get(k, 0) != 0 for k in ("tokens", "chars") if item.get(k) is not None):
                self.r.gap(row["id"], "absent_observation_has_nonzero_cost")
                continue
            row["observation"] = {k: item[k] for k in ("state", "part", "snapshot", "source", "phase", "basis", "tokens", "chars") if k in item}
            row["exposure"] = "observed_" + item["state"]
            if item["part"] != "dynamic_output":
                row["startup_tokens"] = item.get("tokens")

    def report(self, offset=0, limit=20):
        self.usage()
        groups = [{"reason": key[0], "components": ids, "normalized_text_chars": self.fingerprint_chars[key],
                   "extra_source_copy_chars": (len(ids) - 1) * self.fingerprint_chars[key],
                   "runtime_duplicate_injection": "not_established"}
                  for key, ids in self.fingerprints.items() if len(ids) > 1]
        candidates = []
        for row in self.rows.values():
            usage = row.get("usage") or {}
            obs = row.get("observation") or {}
            if (row["kind"] in ("skill", "mcp") and row["configured_enabled"] is not False
                    and row["exposure"] == "observed_present" and obs.get("part") != "dynamic_output"
                    and usage.get("calls") == 0 and any((obs.get(k) or 0) > 0 for k in ("tokens", "chars"))):
                candidates.append({"component": row["id"], "reason": "exposed_with_no_observed_calls",
                                   "action": "review_dependencies_then_consider_manual_or_project_scope",
                                   "priority": "P2", "automatic_removal": False})
        # Source-size ranking only. It does NOT rank observed startup cost or value.
        ordered = sorted(self.rows.values(), key=lambda r: (-r["source_metrics"].get("discovery_source_chars", 0) if r["source_metrics"].get("discovery_source_chars") is not None else 0, r["id"]))
        return {
            "version": VERSION, "mode": "read_only_inventory", "inventory_scope": "explicit_paths_only",
            "components_count": len(ordered), "by_kind": dict(Counter(r["kind"] for r in ordered)),
            "configured_enabled_counts": {kind: {str(value): sum(r["kind"] == kind and r["configured_enabled"] is value for r in ordered)
                                                 for value in (True, False, None)} for kind in sorted({r["kind"] for r in ordered})},
            "skill_source_totals": {"discovery_chars_measured": sum(r["source_metrics"].get("discovery_source_chars") or 0 for r in ordered if r["kind"] == "skill"),
                                    "unmeasured_descriptions": sum(r["kind"] == "skill" and r["source_metrics"].get("discovery_source_chars") is None for r in ordered),
                                    "not_actual_startup_cost": True},
            "usage_window": {"sessions_sampled": len(set(self.session_sources)), "start": min(self.session_times) if self.session_times else None,
                             "end": max(self.session_times) if self.session_times else None, "representative": "not_established", "session_identity_uses_file_proxy": self.session_identity_fallback},
            "read_meter": {"files": self.r.files, "bytes": self.r.bytes, "max_files": self.r.max_files,
                           "max_bytes": self.r.max_bytes, "includes_local_scan_not_model_context": True},
            "page": {"offset": offset, "limit": limit, "order": "discovery_source_chars_desc_not_startup_cost",
                     "next_offset": offset + limit if offset + limit < len(ordered) else None},
            "components": ordered[offset:offset + limit], "duplicate_groups_count": len(groups),
            "duplicate_source_groups": [{**g, "components": g["components"][:limit], "component_count": len(g["components"])} for g in groups[:limit]],
            "candidates_count": len(candidates), "candidates": candidates[:limit],
            "plugin_enabled_declarations": dict(list(self.plugin_flags.items())[:limit]),
            "gaps_count": len(self.r.gaps), "gaps": self.r.gaps[:limit],
            "auxiliary_lists_may_be_truncated": any(n > limit for n in (len(groups), len(candidates), len(self.r.gaps), len(self.plugin_flags))),
            "limits": ["No hidden prompt telemetry. Null is not zero.", "Lengths are source code points/UTF-8 bytes, not prompt tokens.",
                       "Plugin parents and child costs must not be added twice.", "Zero sampled calls is not lifetime non-use; rules/hooks have no call-count inference.",
                       "Managed/CLI overrides, custom plugin paths, symlinks and unprovided history need separate evidence.",
                       "Dependencies and semantic conflicts require targeted review before any change."],
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("claude-dir", "skills-dir", "plugin-dir", "rules-file", "config", "session", "plugin-list"):
        parser.add_argument("--" + flag, action="append", default=[])
    parser.add_argument("--observations", help="Existing normalized host evidence JSON; '-' reads stdin")
    parser.add_argument("--max-files", type=int, default=500)
    parser.add_argument("--max-bytes", type=int, default=8_000_000)
    parser.add_argument("--per-file", type=int, default=1_000_000)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)
    if not (1 <= args.limit <= 200 and args.offset >= 0 and args.max_files > 0 and args.max_bytes > 0 and args.per_file > 0):
        parser.error("positive budgets and 1 <= limit <= 200 required")
    directories = args.claude_dir + args.skills_dir + args.plugin_dir
    files = args.rules_file + args.config + args.session + args.plugin_list
    if args.observations and args.observations != "-":
        files.append(args.observations)
    if not directories and not files:
        parser.error("supply explicit authorized paths; no default home scan")
    # An explicitly passed file grants only that file, not its parent directory.
    r = Reader(directories + files, args.max_files, args.max_bytes, args.per_file)
    inv = Inventory(r)
    normalize = lambda p: Path(p).expanduser().resolve()
    for p in args.config:
        inv.config(normalize(p), "explicit_config")
    for p in args.claude_dir:
        base = normalize(p)
        inv.config(base / "settings.json", "user_config")
        inv.config(base / "settings.local.json", "local_config")
        inv.skills_dir(base / "skills", "config_directory")
        if (base / "CLAUDE.md").exists():
            inv.rule(base / "CLAUDE.md", "config_directory")
        for directory, kind in (("rules", "rule"), ("agents", "agent"), ("commands", "command")):
            if (base / directory).exists():
                inv.markdown_dir(base / directory, kind, "config_directory")
        registry = base / "plugins/installed_plugins.json"
        data = r.structured(registry, optional=True)
        if data is None:
            r.gap(registry, "plugin_registry_unavailable")
        else:
            inv.plugin_list(data, registry)
        r.gap(base, "managed_overrides_and_synced_skills_not_resolved")
    for p in args.skills_dir:
        inv.skills_dir(normalize(p), "explicit_skills_directory")
    for p in args.plugin_dir:
        inv.plugin(normalize(p))
    for p in args.plugin_list:
        inv.plugin_list(r.structured(normalize(p)), normalize(p))
    for p in args.rules_file:
        inv.rule(normalize(p), "explicit_rule")
    for p in args.session:
        inv.session(normalize(p))
    if args.observations:
        try:
            if args.observations == "-":
                raw = sys.stdin.buffer.read(args.per_file + 1)
                if len(raw) > args.per_file:
                    raise ValueError("too large")
                obj = json.loads(raw)
            else:
                obj = r.structured(normalize(args.observations))
            inv.observations(obj)
        except (ValueError, RecursionError):
            r.gap("observations", "invalid_or_oversized_observation_document")
    print(json.dumps(inv.report(args.offset, args.limit), ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
