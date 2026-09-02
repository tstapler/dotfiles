import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from pct_breakdown import compute_breakdown  # noqa: E402


class TestComputeBreakdown(unittest.TestCase):
    def test_leaf_is_last_frame_not_first(self):
        # Regression test: collapsed-stacks format is root-first/leaf-last
        # (stackcollapse-go.pl convention). An earlier version of this script
        # took stack.split(";")[0] and silently ranked by the *root* frame.
        lines = ["main.main;main.work;main.fib 50"]
        rows = compute_breakdown(lines)
        self.assertEqual(rows, [(100.0, 50, "main.fib")])

    def test_aggregates_same_leaf_across_stacks(self):
        lines = [
            "main.a;main.helper 10",
            "main.b;main.helper 5",
        ]
        rows = compute_breakdown(lines)
        self.assertEqual(rows, [(100.0, 15, "main.helper")])

    def test_percentages_and_sort_order(self):
        lines = [
            "main.main;main.fib 50",
            "main.main;main.other 10",
            "main.main;main.work;main.fib2 5",
        ]
        rows = compute_breakdown(lines)
        self.assertEqual([r[2] for r in rows], ["main.fib", "main.other", "main.fib2"])
        self.assertAlmostEqual(rows[0][0], 76.923, places=2)
        self.assertEqual(rows[0][1], 50)

    def test_top_limits_result_count(self):
        lines = [f"main.f{i} {i + 1}" for i in range(5)]
        rows = compute_breakdown(lines, top=2)
        self.assertEqual(len(rows), 2)

    def test_blank_lines_are_ignored(self):
        lines = ["", "main.a;main.leaf 3", "   ", "main.a;main.leaf 2"]
        rows = compute_breakdown(lines)
        self.assertEqual(rows, [(100.0, 5, "main.leaf")])

    def test_empty_input_raises(self):
        with self.assertRaises(ValueError):
            compute_breakdown([])


if __name__ == "__main__":
    unittest.main()
