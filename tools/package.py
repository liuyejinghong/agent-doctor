#!/usr/bin/env python3
"""Offline runtime packager. Never used by the audit to inspect a target project."""
import argparse
import ast
import hashlib
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FLAG = "disable-model-invocation: true\n"
RUNTIME = ("SKILL.md", "README.md", "README.zh-CN.md", "agents/openai.yaml",
           "scripts/inspect_env.py", "references/collector.md", "references/platforms.md",
           "references/environment.md", "references/report-template.md")


def collect(root=ROOT):
    files = {}
    for name in RUNTIME:
        p = root / name
        if p.is_symlink() or root.resolve() not in p.resolve().parents:
            raise ValueError("unsafe runtime path: " + name)
        files[name] = p.read_bytes()
    skill = files["SKILL.md"].decode()
    match = re.match(r'---\n(.*?)\n---\n', skill, re.S)
    if not match or not re.search(r'^name: agent-doctor$', match[1], re.M):
        raise ValueError("skill metadata missing")
    version = re.search(r'^  version: "(\d+\.\d+\.\d+)"$', match[1], re.M)
    if not version or skill.count(FLAG) != 1:
        raise ValueError("version or explicit invocation missing")
    for setting in ('opencode/slash: "true"', 'opencode/autoinvoke: "false"'):
        if setting not in match[1]:
            raise ValueError("OpenCode policy missing")
    if 'allow_implicit_invocation: false' not in files['agents/openai.yaml'].decode():
        raise ValueError("Codex policy missing")
    if len(skill) > 4000 or '!`' in skill or '\nallowed-tools:' in skill:
        raise ValueError("entry growth or unexpected execution authorization")
    if sum(len(files[n].decode()) for n in RUNTIME if n == 'SKILL.md' or n.startswith('references/')) > 11000:
        raise ValueError("runtime instructions exceeded release size guard")
    for name, content in files.items():
        text = content.decode('utf-8')
        if name.endswith('.py'):
            ast.parse(text)
            if 'VERSION = "' + version[1] + '"' not in text:
                raise ValueError("collector version drift")
        if name.endswith('.md'):
            for target in re.findall(r'\[[^\]]+\]\(([^\s)]+)\)', text):
                if re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
                    continue
                local = (root / name).parent.joinpath(target.split('#')[0]).resolve()
                rel = local.relative_to(root.resolve()).as_posix()
                if rel not in files:
                    raise ValueError("link missing from runtime: " + name + " -> " + target)
    return files, version[1]


def build(root, output):
    files, version = collect(root)
    targets = [output / f'agent-doctor-{v}-v{version}.zip' for v in ('claude-code', 'portable')]
    if any(p.exists() for p in targets):
        raise FileExistsError('archive already exists; choose another output directory')
    output.mkdir(parents=True, exist_ok=True)
    for index, path in enumerate(targets):
        with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED) as z:
            for name, data in sorted(files.items()):
                if index == 1 and name == 'SKILL.md':
                    data = data.replace(FLAG.encode(), b'', 1)
                info = zipfile.ZipInfo('agent-doctor/' + name, (2026, 10, 15, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, data)
        with zipfile.ZipFile(path) as z:
            if z.testzip() is not None:
                raise ValueError('ZIP integrity failure')
    return targets


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true')
    p.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = p.parse_args()
    files, version = collect()
    print(f'Runtime structure OK: v{version}, {len(files)} files. Not an agent behavior test.')
    if not args.check:
        for path in build(ROOT, args.output):
            print(str(path) + ' sha256=' + hashlib.sha256(path.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
