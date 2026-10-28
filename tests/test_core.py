"""kosha's logic that needs no network: versions, dependency order, changelogs, the registry."""
import os
import sys
import tempfile
import tomllib
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kosha import core

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def reg(spec):
    return {n: core.Package(n, {"repo": f"x/{n}", **d}) for n, d in spec.items()}


class Versions(unittest.TestCase):
    def test_order(self):
        tags = ["v0.1.10", "v0.1.2", "v1.0.0", "v0.2.0"]
        self.assertEqual(sorted(tags, key=core.vkey), ["v0.1.2", "v0.1.10", "v0.2.0", "v1.0.0"])

    def test_not_a_release(self):
        self.assertEqual(core.vkey("nightly"), (-1, -1, -1))
        self.assertEqual(core.vkey("2.0.1"), (2, 0, 1))


class Resolve(unittest.TestCase):
    def test_dependencies_first(self):
        r = reg({"vyom": {}, "ganit": {"requires": ["vyom"]}, "dvara": {"requires": ["vyom"]}})
        self.assertEqual(core.resolve(["ganit", "dvara"], r), ["vyom", "ganit", "dvara"])

    def test_cycle(self):
        r = reg({"a": {"requires": ["b"]}, "b": {"requires": ["a"]}})
        with self.assertRaises(core.KoshaError):
            core.resolve(["a"], r)

    def test_unknown(self):
        with self.assertRaises(core.KoshaError):
            core.resolve(["nope"], reg({}))


class Paths(unittest.TestCase):
    def test_kinds(self):
        r = reg({"vyom": {"kind": "vyom"}, "ganit": {"kind": "vyom-tool"}, "nada": {"kind": "app"},
                 "sangam": {"kind": "tmux-plugin"}})
        self.assertTrue(r["vyom"].path.endswith("vyom/core"))
        self.assertTrue(r["ganit"].path.endswith("vyom/plugins/ganit"))
        self.assertTrue(r["nada"].path.endswith("/nada"))
        self.assertTrue(r["sangam"].path.endswith(".tmux/plugins/sangam"))
        self.assertIsNone(r["ganit"].bin_target)
        self.assertEqual(r["ganit"].reload, "vyom reload")


class Changelog(unittest.TestCase):
    def test_between(self):
        d = tempfile.mkdtemp()
        open(os.path.join(d, "CHANGELOG.md"), "w").write(
            "# Changelog\n\n## v0.3.0 -- x\n\n- three\n\n## v0.2.0 -- x\n\n- two\n\n## v0.1.0 -- x\n\n- one\n")
        p = core.Package("t", {"repo": "x/t"})
        p.__class__ = type("P", (core.Package,), {"path": property(lambda self: d)})
        out = core.changelog_between(p, "v0.1.0", "v0.3.0")
        self.assertIn("three", out)
        self.assertIn("two", out)
        self.assertNotIn("one", out)


class Registry(unittest.TestCase):
    def test_registry_is_valid(self):
        data = tomllib.load(open(os.path.join(ROOT, "registry.toml"), "rb"))
        pkgs = data["packages"]
        kinds = {"vyom", "vyom-tool", "app", "tmux-plugin"}
        for name, d in pkgs.items():
            self.assertIn("repo", d, name)
            self.assertIn(d.get("kind", "app"), kinds, name)
            self.assertTrue(d.get("description"), name)
            for dep in d.get("requires", []):
                self.assertIn(dep, pkgs, f"{name} requires unknown {dep}")
        r = {n: core.Package(n, d) for n, d in pkgs.items()}
        core.resolve(list(r), r)   # no cycles



class Fetch(unittest.TestCase):
    def test_registry_diff(self):
        old = {"a": {"repo": "x/a"}, "b": {"repo": "x/b", "post": "make"}, "gone": {"repo": "x/gone"}}
        new = {"a": {"repo": "x/a"}, "b": {"repo": "x/b", "post": "make install", "arch": ["go"]},
               "fresh": {"repo": "x/fresh"}}
        self.assertEqual(core.registry_diff(old, new),
                         {"added": ["fresh"], "removed": ["gone"], "changed": {"b": ["arch", "post"]}})

    def test_registry_diff_from_nothing(self):
        self.assertEqual(core.registry_diff({}, {"a": {"repo": "x/a"}})["added"], ["a"])

    def test_commits_past(self):
        self.assertEqual(core.commits_past("v0.2.0-2-gf807d5e"), 2)
        self.assertEqual(core.commits_past("v0.2.0"), 0)
        self.assertEqual(core.commits_past("a491c38"), 0)
        self.assertEqual(core.commits_past(None), 0)

if __name__ == "__main__":
    unittest.main()
