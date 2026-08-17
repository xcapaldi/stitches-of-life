import json
import unittest

from stitchlife import Gauge, Pattern, PatternError, RowBlock, Shaping, pattern_json_schema


class TestShaping(unittest.TestCase):
    def test_delta_counts_both_ends_twice(self):
        self.assertEqual(Shaping("dec", 1, "both").delta, -2)
        self.assertEqual(Shaping("inc", 1, "both").delta, 2)
        self.assertEqual(Shaping("dec", 2, "left").delta, -2)
        self.assertEqual(Shaping("inc", 3, "center").delta, 3)

    def test_rejects_nonsense(self):
        with self.assertRaises(PatternError):
            Shaping(kind="sideways")
        with self.assertRaises(PatternError):
            Shaping(at="diagonally")
        with self.assertRaises(PatternError):
            Shaping(count=0)


class TestRowBlock(unittest.TestCase):
    def test_shaping_fires_on_first_row_then_every_n(self):
        block = RowBlock(count=12, shape=Shaping("dec"), every=4)
        fired = [i for i in range(1, 13) if block.fires_on(i)]
        self.assertEqual(fired, [1, 5, 9])

    def test_plain_block_never_fires(self):
        block = RowBlock(count=5)
        self.assertFalse(any(block.fires_on(i) for i in range(1, 6)))


class TestPattern(unittest.TestCase):
    def test_row_plan_length_includes_cast_on(self):
        pattern = Pattern("p", cast_on=10, blocks=(RowBlock(count=4),))
        self.assertEqual(pattern.n_rows, 5)
        self.assertEqual(len(pattern.row_plan()), 5)

    def test_row_plan_tracks_stitch_counts(self):
        pattern = Pattern(
            "p",
            cast_on=20,
            blocks=(RowBlock(count=6, shape=Shaping("dec"), every=2),),
        )
        counts = [spec.stitches for spec in pattern.row_plan()]
        # Shaping fires on rows 1, 3 and 5 of the block, taking 2 sts each time.
        self.assertEqual(counts, [20, 18, 18, 16, 16, 14, 14])

    def test_increases_widen(self):
        pattern = Pattern("p", cast_on=4, blocks=(RowBlock(count=3, shape=Shaping("inc")),))
        self.assertEqual([s.stitches for s in pattern.row_plan()], [4, 6, 8, 10])

    def test_rejects_piece_that_narrows_away(self):
        with self.assertRaises(PatternError) as caught:
            Pattern("p", cast_on=6, blocks=(RowBlock(count=10, shape=Shaping("dec")),))
        self.assertIn("narrows", str(caught.exception))

    def test_rejects_tiny_cast_on(self):
        with self.assertRaises(PatternError):
            Pattern("p", cast_on=1)

    def test_json_round_trip(self):
        original = Pattern(
            "raglan",
            cast_on=48,
            blocks=(
                RowBlock(count=10, label="hem"),
                RowBlock(count=12, shape=Shaping("dec", 1, "both"), every=4, label="waist"),
            ),
            gauge=Gauge(2.4, 3.1),
        )
        restored = Pattern.from_json(original.to_json())
        self.assertEqual(restored, original)
        self.assertEqual(restored.row_plan(), original.row_plan())

    def test_from_dict_reports_missing_keys(self):
        with self.assertRaises(PatternError) as caught:
            Pattern.from_dict({"rows": []})
        self.assertIn("castOn", str(caught.exception))

    def test_from_json_reports_bad_json(self):
        with self.assertRaises(PatternError):
            Pattern.from_json("{not json")

    def test_describe_round_trips_to_prose(self):
        pattern = Pattern(
            "sleeve",
            cast_on=40,
            blocks=(RowBlock(count=8, shape=Shaping("inc", 1, "both"), every=4),),
        )
        text = pattern.describe()
        self.assertIn("Cast on 40 sts.", text)
        self.assertIn("increase 1 st at each end", text)
        self.assertIn("every 4 rows", text)
        self.assertIn("Bind off all 44 sts.", text)


class TestGauge(unittest.TestCase):
    def test_aspect_makes_stitches_wider_than_tall(self):
        self.assertAlmostEqual(Gauge(2.0, 3.0).aspect, 1.5)

    def test_size_in_cm(self):
        width, height = Gauge(2.0, 4.0).size_cm(stitches=40, rows=80)
        self.assertAlmostEqual(width, 20.0)
        self.assertAlmostEqual(height, 20.0)

    def test_rejects_zero(self):
        with self.assertRaises(PatternError):
            Gauge(0, 3.0)


class TestSchema(unittest.TestCase):
    def test_schema_is_serialisable_and_covers_the_ir(self):
        schema = pattern_json_schema()
        json.dumps(schema)
        self.assertEqual(schema["required"], ["castOn", "rows"])
        row = schema["properties"]["rows"]["items"]["properties"]
        self.assertIn("shape", row)
        self.assertEqual(row["shape"]["properties"]["kind"]["enum"], ["inc", "dec"])


if __name__ == "__main__":
    unittest.main()
