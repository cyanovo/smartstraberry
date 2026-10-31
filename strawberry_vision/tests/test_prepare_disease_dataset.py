import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prepare_disease_dataset import polygon_to_box, prepare


class DiseaseDatasetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.zip"
        self.output = self.root / "disease"

    def archive(self, labels=None, extra=None):
        labels = labels or {}
        with zipfile.ZipFile(self.source, "w") as archive:
            for split in ("train", "val", "test"):
                prefix = f"Strawberry Disease Data/{split}"
                archive.writestr(f"{prefix}/images/sample.jpg", b"image")
                archive.writestr(
                    f"{prefix}/labels/sample.txt",
                    labels.get(split, "6 0.2 0.3 0.4 0.3 0.4 0.7\n"),
                )
            if extra:
                archive.writestr(extra, b"unexpected")

    def test_conversion_and_no_overwrite(self):
        self.archive({"train": "5 -0.1 0.2 0.5 0.2 0.5 1.2\n"})
        result = prepare(self.source, self.output)
        self.assertEqual(result["images_by_split"]["train"], 1)
        self.assertEqual(len(result["clipped_polygon_lines"]), 1)
        self.assertEqual(
            (self.output / "labels/train/sample.txt").read_text().strip(),
            "5 0.25000000 0.60000000 0.50000000 0.80000000",
        )
        with self.assertRaises(FileExistsError):
            prepare(self.source, self.output)

    def test_reject_invalid_label_before_writing(self):
        self.archive({"val": "6 0.1 0.2 0.1 0.3 0.1 0.4\n"})
        with self.assertRaisesRegex(ValueError, "no valid box"):
            prepare(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_reject_unsafe_entry(self):
        self.archive(extra="Strawberry Disease Data/train/images/../escape.jpg")
        with self.assertRaisesRegex(ValueError, "unsafe"):
            prepare(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_reject_missing_pair(self):
        self.archive()
        with zipfile.ZipFile(self.source, "a") as archive:
            archive.writestr("Strawberry Disease Data/train/images/unpaired.jpg", b"image")
        with self.assertRaisesRegex(ValueError, "mismatch"):
            prepare(self.source, self.output)

    def test_reject_windows_case_collision(self):
        self.archive()
        with zipfile.ZipFile(self.source, "a") as archive:
            archive.writestr("Strawberry Disease Data/train/images/SAMPLE.jpg", b"image")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            prepare(self.source, self.output)

    def test_invalid_numbers(self):
        for label in ("9 0 0 1 0 1 1", "6 nan 0 1 0 1 1", "6 0 0 1"):
            with self.subTest(label=label), self.assertRaises(ValueError):
                polygon_to_box(label, "sample")


if __name__ == "__main__":
    unittest.main()
