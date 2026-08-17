import unittest
from array import array

from stitchlife import DEC, INC, KNIT, ElementaryRule, LifeRule, StitchGraph, seed_row

from .test_graph import rectangle


def reference_elementary(rule: int, row: list[int]) -> list[int]:
    """A plain 1D elementary CA, independent of the graph machinery."""
    width = len(row)
    out = []
    for i in range(width):
        left = row[i - 1] if i > 0 else 0
        right = row[i + 1] if i + 1 < width else 0
        out.append((rule >> ((left << 2) | (row[i] << 1) | right)) & 1)
    return out


class TestElementaryRule(unittest.TestCase):
    def test_matches_a_reference_implementation_on_plain_rows(self):
        for number in (30, 90, 110, 184, 250):
            rule = ElementaryRule(number)
            row = seed_row(21, "center")
            for _ in range(20):
                expected = reference_elementary(number, row)
                self.assertEqual(rule.next_row(row, [KNIT] * len(row)), expected, number)
                row = expected

    def test_rule_0_and_255_are_constant(self):
        row = seed_row(9, "random", seed=3)
        self.assertEqual(ElementaryRule(0).next_row(row, [KNIT] * 9), [0] * 9)
        self.assertEqual(ElementaryRule(255).next_row(row, [KNIT] * 9), [1] * 9)

    def test_rejects_out_of_range_numbers(self):
        for bad in (-1, 256):
            with self.assertRaises(ValueError):
                ElementaryRule(bad)

    def test_increase_gives_both_children_the_same_state(self):
        rule = ElementaryRule(110)
        row = [1, 1, 0, 1, 0]
        out = rule.next_row(row, [INC, KNIT, KNIT, KNIT, KNIT])
        self.assertEqual(len(out), 6)
        self.assertEqual(out[0], out[1])

    def test_decrease_ors_its_two_parents(self):
        rule = ElementaryRule(110)
        # Only the centre bit differs between these two rows.
        self.assertEqual(rule.cell([0, 1, 0, 0], 1, 2), rule.cell([0, 0, 1, 0], 1, 2))
        self.assertEqual(rule.cell([0, 1, 1, 0], 1, 2), rule.cell([0, 1, 0, 0], 1, 2))

    def test_row_length_follows_the_ops(self):
        rule = ElementaryRule(110)
        row = [1, 0, 1, 1, 0, 0]
        self.assertEqual(len(rule.next_row(row, [INC, KNIT, DEC, KNIT, KNIT])), 6)
        self.assertEqual(len(rule.next_row(row, [DEC, DEC, KNIT, KNIT])), 4)

    def test_rejects_unknown_ops(self):
        with self.assertRaises(ValueError):
            ElementaryRule(110).next_row([0, 0], [KNIT, 99])


class TestLifeRule(unittest.TestCase):
    def blinker(self, width=7, rows=7):
        graph = rectangle(width, rows)
        state = array("B", bytes(graph.n_stitches))
        centre_row = rows // 2
        for column in (2, 3, 4):
            state[graph.row_start[centre_row] + column] = 1
        return graph, state

    def live_cells(self, graph, state):
        return {
            (graph.row_of(i), graph.column_of(i)) for i in range(len(state)) if state[i]
        }

    def test_blinker_oscillates_with_period_two(self):
        graph, state = self.blinker()
        rule = LifeRule()
        horizontal = self.live_cells(graph, state)

        after_one = rule.next_state(graph, state)
        vertical = self.live_cells(graph, after_one)
        self.assertEqual(vertical, {(2, 3), (3, 3), (4, 3)})

        after_two = rule.next_state(graph, after_one)
        self.assertEqual(self.live_cells(graph, after_two), horizontal)

    def test_block_is_still_life(self):
        graph = rectangle(6, 6)
        state = array("B", bytes(graph.n_stitches))
        for row in (2, 3):
            for column in (2, 3):
                state[graph.row_start[row] + column] = 1
        self.assertEqual(list(LifeRule().next_state(graph, state)), list(state))

    def test_empty_surface_stays_empty(self):
        graph = rectangle(5, 5)
        state = array("B", bytes(graph.n_stitches))
        self.assertEqual(sum(LifeRule().next_state(graph, state)), 0)

    def test_normalization_only_changes_reduced_degree_stitches(self):
        graph = rectangle(7, 7)
        state = array("B", bytes(graph.n_stitches))
        # A full edge row: interior cells see 8 live neighbours either way.
        for index in graph.row_indices(3):
            state[index] = 1
        plain = LifeRule(normalize=False).next_state(graph, state)
        scaled = LifeRule(normalize=True).next_state(graph, state)
        self.assertNotEqual(list(plain), list(scaled))

    def test_from_string_parses_bs_notation(self):
        rule = LifeRule.from_string("B36/S23")
        self.assertEqual(rule.born, frozenset({3, 6}))
        self.assertEqual(rule.survive, frozenset({2, 3}))

    def test_from_string_rejects_junk(self):
        for bad in ("nonsense", "3/23", "B3-S23"):
            with self.assertRaises(ValueError):
                LifeRule.from_string(bad)

    def test_shaping_changes_neighbourhood_degree(self):
        graph = StitchGraph()
        graph.cast_on(7)
        graph.add_row([KNIT, KNIT, DEC, KNIT, KNIT, KNIT])
        graph.add_row([KNIT] * 6)
        degrees = {len(graph.neighbors(i)) for i in graph.row_indices(1)}
        self.assertNotEqual(degrees, {8})


class TestSeedRow(unittest.TestCase):
    def test_center_lights_one_stitch(self):
        row = seed_row(9, "center")
        self.assertEqual(sum(row), 1)
        self.assertEqual(row[4], 1)

    def test_edges_lights_both_ends(self):
        self.assertEqual(seed_row(5, "edges"), [1, 0, 0, 0, 1])

    def test_full_lights_everything(self):
        self.assertEqual(seed_row(4, "full"), [1, 1, 1, 1])

    def test_random_is_reproducible_from_its_seed(self):
        self.assertEqual(seed_row(32, "random", 11), seed_row(32, "random", 11))
        self.assertNotEqual(seed_row(32, "random", 11), seed_row(32, "random", 12))

    def test_rejects_unknown_kind(self):
        with self.assertRaises(ValueError):
            seed_row(5, "spiral")


if __name__ == "__main__":
    unittest.main()
