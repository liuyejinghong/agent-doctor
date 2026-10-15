"""Runtime archive tests: no installation into agent directories."""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('package', ROOT / 'tools/package.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.base = Path(self.t.name).resolve()
        self.root = self.base / 'source'
        for name in p.RUNTIME:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)

    def test_versions_files_and_no_legacy_runtime(self):
        files, version = p.collect(self.root)
        self.assertEqual(version, '2.0.0')
        self.assertEqual(len(files), 9)
        self.assertFalse(any('workflow-and-decisions' in n or 'eval-cases' in n for n in files))

    def test_check_does_not_write(self):
        before = {str(f): f.read_bytes() for f in self.root.rglob('*') if f.is_file()}
        p.collect(self.root)
        self.assertEqual(before, {str(f): f.read_bytes() for f in self.root.rglob('*') if f.is_file()})

    def test_refuses_broken_links(self):
        path = self.root / 'SKILL.md'
        path.write_text(path.read_text() + '\n[bad](missing.md)\n')
        with self.assertRaisesRegex(ValueError, 'link missing'):
            p.collect(self.root)

    def test_policy_and_growth_guards(self):
        path = self.root / 'SKILL.md'
        original = path.read_text()
        path.write_text(original.replace(p.FLAG, ''))
        with self.assertRaises(ValueError):
            p.collect(self.root)
        path.write_text(original + ' ' * 4001)
        with self.assertRaises(ValueError):
            p.collect(self.root)

    def test_archive_parity_and_reproducibility(self):
        one = p.build(self.root, self.base / 'one')
        two = p.build(self.root, self.base / 'two')
        results = []
        for a, b in zip(one, two):
            self.assertEqual(a.read_bytes(), b.read_bytes())
            with zipfile.ZipFile(a) as z:
                self.assertIsNone(z.testzip())
                self.assertEqual(len(z.namelist()), 9)
                self.assertTrue(all(n.startswith('agent-doctor/') and '..' not in Path(n).parts for n in z.namelist()))
                results.append({n: z.read(n) for n in z.namelist()})
        key = 'agent-doctor/SKILL.md'
        results[0][key] = results[0][key].replace(p.FLAG.encode(), b'', 1)
        self.assertEqual(results[0], results[1])

    def test_no_overwrite(self):
        paths = p.build(self.root, self.base / 'out')
        before = [x.read_bytes() for x in paths]
        with self.assertRaises(FileExistsError):
            p.build(self.root, self.base / 'out')
        self.assertEqual(before, [x.read_bytes() for x in paths])


if __name__ == '__main__':
    unittest.main()
