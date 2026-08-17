import unittest

from stitchlife import (
    DensityShaper,
    ElementaryRule,
    Knitter,
    LifeRule,
    Pattern,
    RowBlock,
    Shaping,
    SurfaceAutomaton,
    layout,
    render_text,
)


def taper(cast_on=24, rows=12, every=2, kind="dec"):
    return Pattern(
        "taper",
        cast_on=cast_on,
        blocks=(RowBlock(count=rows, shape=Shaping(kind, 1, "both"), every=every),),
    )


class TestKnitting(unittest.TestCase):
    def test_starts_on_the_cast_on_row(self):
        knitter = Knitter(taper())
        self.assertEqual(knitter.current_row, 0)
        self.assertEqual(knitter.graph.n_stitches, 24)
        self.assertFalse(knitter.done)

    def test_knit_all_reaches_the_last_planned_row(self):
        knitter = Knitter(taper()).knit_all()
        self.assertTrue(knitter.done)
        self.assertEqual(knitter.current_row, len(knitter.plan) - 1)

    def test_every_row_lands_on_its_planned_stitch_count(self):
        knitter = Knitter(taper(cast_on=40, rows=20, every=2)).knit_all()
        self.assertEqual(knitter.stitch_counts(), [spec.stitches for spec in knitter.plan])

    def test_state_stays_aligned_with_the_graph(self):
        knitter = Knitter(taper()).knit_all()
        self.assertEqual(len(knitter.state), knitter.graph.n_stitches)

    def test_increases_widen_the_fabric(self):
        knitter = Knitter(taper(cast_on=6, rows=10, kind="inc")).knit_all()
        counts = knitter.stitch_counts()
        self.assertEqual(counts[0], 6)
        self.assertGreater(counts[-1], counts[0])
        self.assertEqual(knitter.graph.max_row_len, counts[-1])

    def test_knitting_past_the_end_is_a_no_op(self):
        knitter = Knitter(taper()).knit_all()
        self.assertEqual(knitter.knit_row(), -1)
        self.assertTrue(knitter.done)


class TestTimeline(unittest.TestCase):
    def test_stepping_back_then_forward_reproduces_the_fabric(self):
        original = Knitter(taper(cast_on=32, rows=16)).knit_all()
        expected_state = list(original.state)
        expected_counts = original.stitch_counts()

        original.step(-6)
        self.assertEqual(original.current_row, len(original.plan) - 7)
        original.step(6)

        self.assertEqual(list(original.state), expected_state)
        self.assertEqual(original.stitch_counts(), expected_counts)

    def test_unknitting_past_the_cast_on_is_a_no_op(self):
        knitter = Knitter(taper())
        self.assertEqual(knitter.unknit_row(), -1)
        self.assertEqual(knitter.current_row, 0)

    def test_goto_row_moves_in_both_directions(self):
        knitter = Knitter(taper(cast_on=30, rows=14))
        self.assertEqual(knitter.goto_row(9), 9)
        self.assertEqual(knitter.graph.n_rows, 10)
        self.assertEqual(knitter.goto_row(3), 3)
        self.assertEqual(knitter.graph.n_rows, 4)

    def test_goto_row_clamps_to_the_plan(self):
        knitter = Knitter(taper())
        self.assertEqual(knitter.goto_row(10_000), len(knitter.plan) - 1)
        self.assertEqual(knitter.goto_row(-5), 0)

    def test_reset_returns_to_the_cast_on_row(self):
        knitter = Knitter(taper()).knit_all()
        knitter.reset()
        self.assertEqual(knitter.current_row, 0)
        self.assertEqual(knitter.graph.n_stitches, 24)

    def test_a_rerun_is_identical(self):
        pattern = taper(cast_on=28, rows=14)
        first = Knitter(pattern, ElementaryRule(30), seed=5, seed_kind="random").knit_all()
        second = Knitter(pattern, ElementaryRule(30), seed=5, seed_kind="random").knit_all()
        self.assertEqual(list(first.state), list(second.state))
        self.assertEqual(first.ops_by_row, second.ops_by_row)


class TestAutomatonShaping(unittest.TestCase):
    def test_shaped_fabric_still_meets_the_pattern_counts(self):
        pattern = taper(cast_on=44, rows=24, every=2)
        knitter = Knitter(
            pattern,
            ElementaryRule(30),
            shaper=DensityShaper(),
            seed=3,
            seed_kind="random",
        ).knit_all()
        self.assertEqual(knitter.stitch_counts(), [spec.stitches for spec in knitter.plan])

    def test_shaping_moves_off_the_conventional_positions(self):
        pattern = taper(cast_on=44, rows=24, every=2)
        plain = Knitter(pattern, ElementaryRule(30), seed=3, seed_kind="random").knit_all()
        shaped = Knitter(
            pattern,
            ElementaryRule(30),
            shaper=DensityShaper(),
            seed=3,
            seed_kind="random",
        ).knit_all()
        self.assertNotEqual(plain.ops_by_row, shaped.ops_by_row)

    def test_shaped_timeline_is_still_reversible(self):
        knitter = Knitter(
            taper(cast_on=40, rows=20),
            ElementaryRule(30),
            shaper=DensityShaper(),
            seed=1,
            seed_kind="random",
        ).knit_all()
        expected = list(knitter.state)
        knitter.step(-8)
        knitter.step(8)
        self.assertEqual(list(knitter.state), expected)


class TestSerialisation(unittest.TestCase):
    def test_to_dict_captures_every_row(self):
        knitter = Knitter(taper(cast_on=20, rows=8)).knit_all()
        data = knitter.to_dict()
        self.assertEqual(len(data["rows"]), knitter.graph.n_rows)
        self.assertEqual(data["rows"][0]["ops"], [])
        for row in data["rows"]:
            self.assertEqual(len(row["states"]), row["stitches"])
        self.assertEqual(data["pattern"]["castOn"], 20)

    def test_op_names_are_readable(self):
        knitter = Knitter(taper(cast_on=20, rows=4, every=1)).knit_all()
        names = set(data for row in knitter.to_dict()["rows"] for data in row["ops"])
        self.assertIn("knit", names)
        self.assertIn("dec", names)


class TestSurface(unittest.TestCase):
    def test_generation_advances_and_rewinds(self):
        knitter = Knitter(taper(cast_on=30, rows=20), seed=2, seed_kind="random").knit_all()
        automaton = SurfaceAutomaton(knitter.graph, LifeRule(), knitter.state)

        automaton.step(5)
        self.assertEqual(automaton.generation, 5)
        fifth = list(automaton.state)

        automaton.back(3)
        self.assertEqual(automaton.generation, 2)
        automaton.step(3)
        self.assertEqual(list(automaton.state), fifth)

    def test_keyframes_do_not_change_the_result(self):
        knitter = Knitter(taper(cast_on=24, rows=16), seed=4, seed_kind="random").knit_all()
        dense = SurfaceAutomaton(knitter.graph, LifeRule(), knitter.state, keyframe_every=1)
        sparse = SurfaceAutomaton(knitter.graph, LifeRule(), knitter.state, keyframe_every=8)
        dense.step(20)
        sparse.step(20)
        self.assertEqual(list(dense.state), list(sparse.state))

        dense.goto(7)
        sparse.goto(7)
        self.assertEqual(list(dense.state), list(sparse.state))

    def test_reset_and_clamping(self):
        knitter = Knitter(taper(), seed=1, seed_kind="random").knit_all()
        automaton = SurfaceAutomaton(knitter.graph, LifeRule(), knitter.state)
        initial = list(automaton.state)
        automaton.step(4)
        self.assertEqual(automaton.back(100), 0)
        self.assertEqual(list(automaton.state), initial)
        automaton.step(2)
        automaton.reset()
        self.assertEqual(automaton.generation, 0)

    def test_rejects_a_mismatched_initial_state(self):
        knitter = Knitter(taper()).knit_all()
        with self.assertRaises(ValueError):
            SurfaceAutomaton(knitter.graph, LifeRule(), [0, 1, 0])


class TestChart(unittest.TestCase):
    def test_layout_has_one_centre_per_stitch(self):
        knitter = Knitter(taper(cast_on=6, rows=8, kind="inc")).knit_all()
        centres = layout(knitter.graph, knitter.pattern.gauge)
        self.assertEqual(len(centres), knitter.graph.n_stitches)

    def test_layout_centres_narrow_rows_over_wide_ones(self):
        knitter = Knitter(taper(cast_on=24, rows=10, every=1)).knit_all()
        centres = layout(knitter.graph)
        widest = knitter.graph.row_indices(0)
        narrowest = knitter.graph.row_indices(knitter.graph.n_rows - 1)
        wide_span = centres[widest[-1]][0] - centres[widest[0]][0]
        narrow_span = centres[narrowest[-1]][0] - centres[narrowest[0]][0]
        self.assertGreater(wide_span, narrow_span)
        wide_mid = (centres[widest[0]][0] + centres[widest[-1]][0]) / 2
        narrow_mid = (centres[narrowest[0]][0] + centres[narrowest[-1]][0]) / 2
        self.assertAlmostEqual(wide_mid, narrow_mid, places=6)

    def test_layout_grows_upward_from_the_cast_on(self):
        knitter = Knitter(taper()).knit_all()
        centres = layout(knitter.graph)
        self.assertLess(centres[0][1], centres[-1][1])

    def test_render_text_puts_the_cast_on_row_last(self):
        knitter = Knitter(taper(cast_on=12, rows=6)).knit_all()
        lines = render_text(knitter.graph, knitter.state).splitlines()
        self.assertEqual(len(lines), knitter.graph.n_rows)
        self.assertEqual(len(lines[-1].strip()), 12)

    def test_render_text_marks_shaping(self):
        knitter = Knitter(taper(cast_on=20, rows=6, every=1)).knit_all()
        marked = render_text(knitter.graph, knitter.state, mark_shaping=True)
        plain = render_text(knitter.graph, knitter.state, mark_shaping=False)
        self.assertTrue(set("Aa`").intersection(marked))
        self.assertFalse(set("Aa`").intersection(plain))

    def test_render_text_can_annotate_counts(self):
        knitter = Knitter(taper(cast_on=16, rows=4, every=1)).knit_all()
        text = render_text(knitter.graph, knitter.state, show_counts=True)
        self.assertIn("sts  row 0", text)
        self.assertIn("16 sts", text)


if __name__ == "__main__":
    unittest.main()
