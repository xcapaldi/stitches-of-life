import unittest

from stitchlife import DEC, INC, KNIT, GraphError, StitchGraph, consumed, produced


def rectangle(width: int, rows: int) -> StitchGraph:
    graph = StitchGraph()
    graph.cast_on(width)
    for _ in range(rows - 1):
        graph.add_row([KNIT] * width)
    return graph


class TestOpArithmetic(unittest.TestCase):
    def test_consumed_and_produced(self):
        ops = [KNIT, INC, DEC, KNIT]
        self.assertEqual(consumed(ops), 1 + 1 + 2 + 1)
        self.assertEqual(produced(ops), 1 + 2 + 1 + 1)


class TestConstruction(unittest.TestCase):
    def test_cast_on_stitches_have_no_parents(self):
        graph = StitchGraph()
        graph.cast_on(6)
        self.assertEqual(graph.n_rows, 1)
        self.assertEqual(graph.n_stitches, 6)
        for i in range(6):
            self.assertEqual(graph.parents(i), ())

    def test_cast_on_twice_is_rejected(self):
        graph = StitchGraph()
        graph.cast_on(4)
        with self.assertRaises(GraphError):
            graph.cast_on(4)

    def test_row_must_consume_the_whole_row_below(self):
        graph = rectangle(6, 1)
        with self.assertRaises(GraphError) as caught:
            graph.add_row([KNIT] * 5)
        self.assertIn("consume", str(caught.exception))

    def test_decrease_joins_two_parents_to_one_child(self):
        graph = rectangle(4, 1)
        graph.add_row([DEC, KNIT, KNIT])
        self.assertEqual(graph.row_len[1], 3)
        child = graph.row_start[1]
        self.assertEqual(graph.parents(child), (0, 1))
        self.assertEqual(graph.children(0), (child,))
        self.assertEqual(graph.children(1), (child,))

    def test_increase_splits_one_parent_into_two_children(self):
        graph = rectangle(4, 1)
        graph.add_row([INC, KNIT, KNIT, KNIT])
        self.assertEqual(graph.row_len[1], 5)
        first, second = graph.row_start[1], graph.row_start[1] + 1
        self.assertEqual(graph.children(0), (first, second))
        self.assertEqual(graph.parents(first), (0,))
        self.assertEqual(graph.parents(second), (0,))

    def test_unknown_op_is_rejected(self):
        graph = rectangle(3, 1)
        with self.assertRaises(GraphError):
            graph.add_row([KNIT, KNIT, 99])


class TestIndexing(unittest.TestCase):
    def test_row_and_column_recover_from_index(self):
        graph = rectangle(5, 4)
        for row in range(4):
            for column, index in enumerate(graph.row_indices(row)):
                self.assertEqual(graph.row_of(index), row)
                self.assertEqual(graph.column_of(index), column)

    def test_row_of_handles_variable_widths(self):
        graph = StitchGraph()
        graph.cast_on(3)
        graph.add_row([INC, KNIT, KNIT])  # 4
        graph.add_row([DEC, KNIT, KNIT])  # 3
        widths = [3, 4, 3]
        self.assertEqual(list(graph.row_len), widths)
        for row in range(3):
            for index in graph.row_indices(row):
                self.assertEqual(graph.row_of(index), row)

    def test_siblings_stop_at_row_edges(self):
        graph = rectangle(4, 2)
        first, last = 0, 3
        self.assertEqual(graph.left(first), -1)
        self.assertEqual(graph.right(last), -1)
        self.assertEqual(graph.right(first), 1)


class TestNeighborhood(unittest.TestCase):
    def test_interior_of_a_rectangle_is_the_moore_neighbourhood(self):
        width, rows = 7, 7
        graph = rectangle(width, rows)
        row, column = 3, 3
        index = graph.row_start[row] + column
        neighbors = set(graph.neighbors(index))

        expected = set()
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                expected.add(graph.row_start[row + dr] + column + dc)

        self.assertEqual(len(neighbors), 8)
        self.assertEqual(neighbors, expected)

    def test_corner_has_fewer_neighbours(self):
        graph = rectangle(7, 7)
        self.assertEqual(len(graph.neighbors(0)), 3)

    def test_a_stitch_is_never_its_own_neighbour(self):
        graph = rectangle(5, 5)
        for i in range(graph.n_stitches):
            self.assertNotIn(i, graph.neighbors(i))

    def test_neighbours_are_unique(self):
        graph = StitchGraph()
        graph.cast_on(6)
        graph.add_row([DEC, KNIT, KNIT, KNIT, KNIT])
        graph.add_row([INC, KNIT, KNIT, KNIT, KNIT])
        for i in range(graph.n_stitches):
            found = graph.neighbors(i)
            self.assertEqual(len(found), len(set(found)))

    def test_decrease_gives_its_child_a_wider_neighbourhood(self):
        graph = StitchGraph()
        graph.cast_on(7)
        graph.add_row([KNIT, KNIT, DEC, KNIT, KNIT, KNIT])
        child = graph.row_start[1] + 2
        # Both consumed parents and their siblings are adjacent to the child.
        self.assertEqual(len(graph.parents(child)), 2)
        neighbors = set(graph.neighbors(child))
        self.assertTrue({2, 3}.issubset(neighbors))
        self.assertTrue({1, 4}.issubset(neighbors))


class TestPopRow(unittest.TestCase):
    def test_pop_restores_the_previous_row_exactly(self):
        graph = rectangle(5, 3)
        before = (graph.n_stitches, list(graph.row_len), list(graph.child_a))

        graph.add_row([INC, KNIT, KNIT, DEC])
        popped = graph.pop_row()

        self.assertEqual(popped, 5)
        self.assertEqual(graph.n_stitches, before[0])
        self.assertEqual(list(graph.row_len), before[1])
        self.assertEqual(list(graph.child_a), before[2])

    def test_top_row_has_no_children_after_pop(self):
        graph = rectangle(4, 2)
        graph.add_row([KNIT] * 4)
        graph.pop_row()
        for index in graph.row_indices(graph.n_rows - 1):
            self.assertEqual(graph.children(index), ())

    def test_cannot_pop_the_cast_on_row(self):
        graph = rectangle(4, 1)
        with self.assertRaises(GraphError):
            graph.pop_row()

    def test_rebuilding_after_pop_matches_the_original(self):
        ops = [INC, KNIT, DEC, KNIT]
        first = rectangle(5, 2)
        first.add_row(ops)
        snapshot = (list(first.parent_a), list(first.parent_b), list(first.child_a))

        first.pop_row()
        first.add_row(ops)
        self.assertEqual(
            (list(first.parent_a), list(first.parent_b), list(first.child_a)), snapshot
        )


if __name__ == "__main__":
    unittest.main()
