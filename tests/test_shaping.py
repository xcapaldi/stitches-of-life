import unittest

from stitchlife import (
    DEC,
    INC,
    KNIT,
    DensityShaper,
    Occupancy,
    Proposal,
    ShapingError,
    build_row_ops,
    consumed,
    produced,
)


def positions_of(ops, kind):
    """Columns in the row below where `kind` was placed."""
    out = []
    column = 0
    for op in ops:
        if op == kind:
            out.append(column)
        column += 2 if op == DEC else 1
    return out


class TestOccupancy(unittest.TestCase):
    def test_spacing_blocks_nearby_positions(self):
        occupancy = Occupancy(10, min_spacing=2)
        self.assertTrue(occupancy.fits(4, 1))
        occupancy.take(4, 1)
        for position in (2, 3, 4, 5, 6):
            self.assertFalse(occupancy.fits(position, 1), position)
        self.assertTrue(occupancy.fits(7, 1))

    def test_ops_may_not_run_off_the_end(self):
        occupancy = Occupancy(5, min_spacing=0)
        self.assertTrue(occupancy.fits(4, 1))
        self.assertFalse(occupancy.fits(4, 2))
        self.assertFalse(occupancy.fits(-1, 1))

    def test_snapshot_and_restore(self):
        occupancy = Occupancy(8, min_spacing=1)
        saved = occupancy.snapshot()
        occupancy.take(3, 2)
        self.assertFalse(occupancy.fits(3, 1))
        occupancy.restore(saved)
        self.assertTrue(occupancy.fits(3, 1))


class TestPatternPlacement(unittest.TestCase):
    def test_even_row_is_all_knit(self):
        ops = build_row_ops(prev_len=12, delta=0)
        self.assertEqual(ops, [KNIT] * 12)

    def test_decrease_at_both_ends(self):
        ops = build_row_ops(prev_len=20, delta=-2, at="both")
        self.assertEqual(consumed(ops), 20)
        self.assertEqual(produced(ops), 18)
        placed = positions_of(ops, DEC)
        self.assertEqual(len(placed), 2)
        # One near each end, and off the very edge so a selvedge survives.
        self.assertLess(placed[0], 4)
        self.assertGreater(placed[1], 14)

    def test_increase_at_both_ends(self):
        ops = build_row_ops(prev_len=20, delta=2, at="both")
        self.assertEqual(consumed(ops), 20)
        self.assertEqual(produced(ops), 22)
        self.assertEqual(len(positions_of(ops, INC)), 2)

    def test_left_and_right_placement_differ(self):
        left = positions_of(build_row_ops(24, -1, at="left"), DEC)
        right = positions_of(build_row_ops(24, -1, at="right"), DEC)
        self.assertLess(left[0], 4)
        self.assertGreater(right[0], 18)

    def test_center_placement_lands_mid_row(self):
        placed = positions_of(build_row_ops(25, 1, at="center"), INC)
        self.assertEqual(len(placed), 1)
        self.assertTrue(9 < placed[0] < 15, placed)

    def test_large_delta_spreads_across_the_row(self):
        ops = build_row_ops(prev_len=40, delta=-6, at="both")
        placed = positions_of(ops, DEC)
        self.assertEqual(len(placed), 6)
        self.assertEqual(produced(ops), 34)
        gaps = [b - a for a, b in zip(placed, placed[1:])]
        self.assertTrue(all(gap >= 3 for gap in gaps), placed)

    def test_narrow_rows_relax_spacing_rather_than_refusing(self):
        # Six stitches cannot hold two decreases at the preferred margin, but
        # the pattern's count is a requirement, so the margin gives way.
        ops = build_row_ops(prev_len=6, delta=-2, at="both", min_spacing=2)
        self.assertEqual(consumed(ops), 6)
        self.assertEqual(produced(ops), 4)
        self.assertEqual(len(positions_of(ops, DEC)), 2)

    def test_relaxation_does_not_leak_into_proposal_handling(self):
        # A tight cluster of proposals still gets thinned by spacing, even
        # though the pattern shaping in the same row had to pack tighter.
        proposals = [Proposal(p, DEC, 1.0) for p in (2, 3, 4, 5)]
        ops = build_row_ops(prev_len=8, delta=-2, proposals=proposals, min_spacing=3)
        self.assertEqual(produced(ops), 6)
        self.assertEqual(len(positions_of(ops, DEC)), 2)

    def test_impossible_row_is_reported(self):
        with self.assertRaises(ShapingError):
            build_row_ops(prev_len=6, delta=-6, at="both", min_spacing=3)
        with self.assertRaises(ShapingError):
            build_row_ops(prev_len=0, delta=0)


class TestProposalReconciliation(unittest.TestCase):
    def test_row_lands_on_the_pattern_count_whatever_is_proposed(self):
        proposals = [Proposal(p, INC, 1.0) for p in range(0, 30, 2)]
        ops = build_row_ops(prev_len=30, delta=-2, at="both", proposals=proposals)
        self.assertEqual(consumed(ops), 30)
        self.assertEqual(produced(ops), 28)

    def test_automaton_placement_is_preferred_over_the_conventional_one(self):
        proposals = [Proposal(15, DEC, 1.0)]
        ops = build_row_ops(prev_len=30, delta=-1, at="both", proposals=proposals)
        self.assertEqual(positions_of(ops, DEC), [15])

    def test_highest_scoring_proposals_win(self):
        proposals = [
            Proposal(5, DEC, 0.2),
            Proposal(20, DEC, 0.9),
            Proposal(25, DEC, 0.5),
        ]
        ops = build_row_ops(prev_len=30, delta=-1, proposals=proposals)
        self.assertEqual(positions_of(ops, DEC), [20])

    def test_shortfall_falls_back_to_conventional_placement(self):
        # Only one usable proposal, but the pattern needs two decreases.
        ops = build_row_ops(
            prev_len=30, delta=-2, at="both", proposals=[Proposal(14, DEC, 1.0)]
        )
        placed = positions_of(ops, DEC)
        self.assertEqual(len(placed), 2)
        self.assertIn(14, placed)
        self.assertEqual(produced(ops), 28)

    def test_proposals_of_the_wrong_direction_are_ignored(self):
        ops = build_row_ops(
            prev_len=30, delta=-1, proposals=[Proposal(i, INC, 1.0) for i in range(30)]
        )
        self.assertEqual(produced(ops), 29)
        self.assertEqual(positions_of(ops, INC), [])

    def test_spacing_is_respected_across_accepted_proposals(self):
        proposals = [Proposal(p, DEC, 1.0) for p in (10, 11, 12, 13)]
        ops = build_row_ops(prev_len=40, delta=-2, proposals=proposals, min_spacing=4)
        placed = positions_of(ops, DEC)
        self.assertEqual(len(placed), 2)
        self.assertGreaterEqual(placed[1] - placed[0], 4)

    def test_texture_pairs_add_shaping_without_changing_the_count(self):
        proposals = [Proposal(8, INC, 0.9), Proposal(24, DEC, 0.9)]
        plain = build_row_ops(prev_len=40, delta=0, proposals=proposals, texture_pairs=0)
        paired = build_row_ops(prev_len=40, delta=0, proposals=proposals, texture_pairs=1)

        self.assertEqual(produced(plain), 40)
        self.assertEqual(produced(paired), 40)
        self.assertEqual(plain, [KNIT] * 40)
        self.assertEqual(positions_of(paired, INC), [8])
        self.assertEqual(positions_of(paired, DEC), [24])

    def test_a_pair_that_cannot_both_fit_is_dropped_whole(self):
        # The two proposals are too close together to coexist.
        proposals = [Proposal(10, INC, 0.9), Proposal(11, DEC, 0.9)]
        ops = build_row_ops(
            prev_len=40, delta=0, proposals=proposals, min_spacing=5, texture_pairs=1
        )
        self.assertEqual(produced(ops), 40)
        self.assertEqual(ops, [KNIT] * 40)


class TestDensityShaper(unittest.TestCase):
    def test_dense_regions_propose_increases(self):
        shaper = DensityShaper(window=2, inc_threshold=0.8, dec_threshold=0.2)
        states = [1] * 12
        kinds = {p.kind for p in shaper.propose(states)}
        self.assertEqual(kinds, {INC})

    def test_empty_regions_propose_decreases(self):
        shaper = DensityShaper(window=2, inc_threshold=0.8, dec_threshold=0.2)
        kinds = {p.kind for p in shaper.propose([0] * 12)}
        self.assertEqual(kinds, {DEC})

    def test_mixed_fabric_proposes_nothing(self):
        shaper = DensityShaper(window=2, inc_threshold=0.9, dec_threshold=0.1)
        self.assertEqual(shaper.propose([0, 1] * 8), [])

    def test_decrease_is_never_proposed_on_the_last_column(self):
        shaper = DensityShaper(window=1, inc_threshold=0.9, dec_threshold=0.5)
        states = [0] * 6
        self.assertTrue(all(p.position + 1 < len(states) for p in shaper.propose(states)))

    def test_rejects_crossed_thresholds(self):
        with self.assertRaises(ValueError):
            DensityShaper(inc_threshold=0.2, dec_threshold=0.8)

    def test_density_is_a_fraction_of_the_sampled_window(self):
        shaper = DensityShaper(window=1)
        self.assertAlmostEqual(shaper.density([1, 1, 1, 0, 0], 1), 1.0)
        self.assertAlmostEqual(shaper.density([1, 1, 1, 0, 0], 3), 1 / 3)


if __name__ == "__main__":
    unittest.main()
