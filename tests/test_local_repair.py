"""Offline behavioral checks; no account, private media, or paid generation."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / "skills/xhs-neowow-delivery/scripts/repair_local.py"
SPEC = importlib.util.spec_from_file_location("repair_local", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        yy, xx = np.indices((80, 80))
        self.source = np.stack([xx * 3, yy * 3, (xx + yy) % 256], axis=-1).astype("uint8")
        self.target = np.full((80, 80, 3), 7, dtype="uint8")
        self.mask = np.zeros((80, 80), dtype="uint8")
        self.mask[20:40, 20:40] = 255
        self.save("source.png", self.source)
        self.save("target.png", self.target)
        self.save("mask.png", self.mask)

    def save(self, name, array):
        Image.fromarray(array).save(self.root / name)

    def run_repair(self, **kwargs):
        return MODULE.repair(self.root / "source.png", self.root / "target.png",
                             self.root / "mask.png", self.root / "result.png", **kwargs)

    def points(self, source, target):
        path = self.root / "points.json"
        path.write_text(json.dumps({"source_points": source, "target_points": target}))
        return path

    def test_aligned_replacement_and_unmasked_preservation(self):
        report = self.run_repair(aligned=True)
        result = np.array(Image.open(self.root / "result.png"))
        np.testing.assert_array_equal(result[self.mask > 0], self.source[self.mask > 0])
        np.testing.assert_array_equal(result[self.mask == 0], self.target[self.mask == 0])
        self.assertEqual(report["changed_pixels"], 400)
        self.assertTrue(report["outside_mask_unchanged"])

    def test_feather_stays_inside_mask(self):
        self.run_repair(aligned=True, feather=4)
        result = np.array(Image.open(self.root / "result.png"))
        np.testing.assert_array_equal(result[self.mask == 0], self.target[self.mask == 0])
        np.testing.assert_array_equal(result[25:35, 25:35], self.source[25:35, 25:35])
        self.assertFalse(np.array_equal(result[20, 20], self.source[20, 20]))

    def test_known_translation_restores_correct_coordinates(self):
        src = [[10, 10], [50, 10], [50, 50], [10, 50]]
        dst = [[15, 13], [55, 13], [55, 53], [15, 53]]
        self.run_repair(points_path=self.points(src, dst))
        result = np.array(Image.open(self.root / "result.png"))
        np.testing.assert_array_equal(result[20:40, 20:40], self.source[17:37, 15:35])
        np.testing.assert_array_equal(result[self.mask == 0], self.target[self.mask == 0])

    def test_collinear_points_rejected(self):
        pts = [[10, 10], [20, 20], [30, 30], [40, 40]]
        with self.assertRaisesRegex(ValueError, "collinear"):
            self.run_repair(points_path=self.points(pts, pts))
        self.assertFalse((self.root / "result.png").exists())

    def test_uncovered_mask_rejected(self):
        self.mask[:] = 255
        self.save("mask.png", self.mask)
        src = [[10, 10], [50, 10], [50, 50], [10, 50]]
        dst = [[15, 13], [55, 13], [55, 53], [15, 53]]
        with self.assertRaisesRegex(ValueError, "source coverage"):
            self.run_repair(points_path=self.points(src, dst))

    def test_wrong_mask_size_rejected(self):
        self.save("mask.png", np.ones((12, 12), dtype="uint8") * 255)
        with self.assertRaisesRegex(ValueError, "dimensions"):
            self.run_repair(aligned=True)

    def test_existing_output_not_overwritten(self):
        out = self.root / "result.png"
        out.write_bytes(b"existing version")
        with self.assertRaises(FileExistsError):
            self.run_repair(aligned=True)
        self.assertEqual(out.read_bytes(), b"existing version")


if __name__ == "__main__":
    unittest.main()
