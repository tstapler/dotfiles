import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from annotate_tree import build_tree, parse_raw, render, top_self  # noqa: E402

# Minimal fixture mirroring real `go tool pprof -raw` output: two samples
# sharing a root/mid call path and diverging into two different leaves.
# Location ids are listed leaf-first in Samples, per pprof's actual format
# (verified against `go tool pprof -raw` on a real CPU profile).
RAW_FIXTURE = """\
PeriodType: cpu nanoseconds
Period: 10000000
Time: 2026-09-02 00:00:00.000000 -0700 PDT
Duration: 100.
Samples:
samples/count cpu/nanoseconds
          1   10000000: 1 2 3
          1   10000000: 4 2 3
Locations
     1: 0x1 M=1 main.leafA /f.go:1:0 s=1
     2: 0x2 M=1 main.mid /f.go:2:0 s=1
     3: 0x3 M=1 main.root /f.go:3:0 s=1
     4: 0x4 M=1 main.leafB /f.go:4:0 s=1
Mappings
1: 0x1/0x2/0x0 /bin/example  [FN]
"""


class TestParseRaw(unittest.TestCase):
    def test_parses_samples_and_locations(self):
        samples, locations = parse_raw(RAW_FIXTURE)
        self.assertEqual(samples, [(1, [1, 2, 3]), (1, [4, 2, 3])])
        self.assertEqual(
            locations,
            {1: "main.leafA", 2: "main.mid", 3: "main.root", 4: "main.leafB"},
        )

    def test_ignores_mappings_section(self):
        samples, locations = parse_raw(RAW_FIXTURE)
        # No location id 0 exists as a leftover from the Mappings line.
        self.assertNotIn(0, locations)


class TestBuildTree(unittest.TestCase):
    def test_shared_prefix_merges_into_one_path(self):
        samples, locations = parse_raw(RAW_FIXTURE)
        root, total = build_tree(samples, locations)
        self.assertEqual(total, 2)

        # root -> main.root -> main.mid -> {main.leafA, main.leafB}
        main_root = root.children["main.root"]
        self.assertEqual(main_root.cum_count, 2)
        main_mid = main_root.children["main.mid"]
        self.assertEqual(main_mid.cum_count, 2)
        self.assertEqual(main_mid.self_count, 0)

        leaf_a = main_mid.children["main.leafA"]
        leaf_b = main_mid.children["main.leafB"]
        self.assertEqual(leaf_a.self_count, 1)
        self.assertEqual(leaf_a.cum_count, 1)
        self.assertEqual(leaf_b.self_count, 1)
        self.assertEqual(leaf_b.cum_count, 1)


class TestRender(unittest.TestCase):
    def test_hotspot_marker_and_percentages(self):
        samples, locations = parse_raw(RAW_FIXTURE)
        root, total = build_tree(samples, locations)
        lines = render(root, total, min_pct=0, hotspot_pct=40, max_depth=10)
        joined = "\n".join(lines)

        self.assertIn("main.root", joined)
        self.assertIn("main.mid", joined)
        # Each leaf is 50% self -- above the 40% hotspot threshold.
        self.assertIn("main.leafA  ◀ HOTSPOT", joined)
        self.assertIn("main.leafB  ◀ HOTSPOT", joined)
        # main.mid has 0% self -- should not be marked.
        self.assertNotIn("main.mid  ◀ HOTSPOT", joined)

    def test_min_pct_prunes_low_weight_subtrees(self):
        samples, locations = parse_raw(RAW_FIXTURE)
        root, total = build_tree(samples, locations)
        # main.root and main.mid are 100% cum (both samples pass through them);
        # the two leaves split 50/50. A 60% floor should prune both leaves but
        # keep the shared root/mid path.
        lines = render(root, total, min_pct=60, hotspot_pct=100, max_depth=10)
        joined = "\n".join(lines)
        self.assertIn("main.root", joined)
        self.assertIn("main.mid", joined)
        self.assertNotIn("main.leafA", joined)
        self.assertNotIn("main.leafB", joined)

    def test_max_depth_truncates_tree(self):
        samples, locations = parse_raw(RAW_FIXTURE)
        root, total = build_tree(samples, locations)
        lines = render(root, total, min_pct=0, hotspot_pct=100, max_depth=1)
        self.assertEqual(len(lines), 1)
        self.assertIn("main.root", lines[0])


class TestTopSelf(unittest.TestCase):
    def test_flat_leaderboard_across_call_sites(self):
        samples, locations = parse_raw(RAW_FIXTURE)
        root, total = build_tree(samples, locations)
        ranked = top_self(root, total, n=10)
        self.assertEqual(len(ranked), 2)
        names = {name for _, name in ranked}
        self.assertEqual(names, {"main.leafA", "main.leafB"})
        for pct, _ in ranked:
            self.assertAlmostEqual(pct, 50.0)


if __name__ == "__main__":
    unittest.main()
