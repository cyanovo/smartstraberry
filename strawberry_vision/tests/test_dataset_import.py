import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dataset_import as importer


class DatasetImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "incoming"
        self.source.mkdir()

    def sample(self, index, label="hmb"):
        name = f"sample_{index:02}"
        Image.new("RGB", (100, 80), (index * 20, 0, 0)).save(self.source / f"{name}.jpg")
        (self.source / f"{name}.xml").write_text(
            f"<annotation><filename>{name}.jpg</filename><size><width>100</width><height>80</height></size>"
            f"<object><name>{label}</name><bndbox><xmin>10</xmin><ymin>20</ymin>"
            "<xmax>50</xmax><ymax>60</ymax></bndbox></object></annotation>", encoding="utf-8")

    def test_missing_xml_is_reported(self):
        self.sample(0)
        (self.source / "extra.jpg").write_bytes(b"not an image")
        records, classes, issues = importer.inspect(self.source)
        self.assertEqual(len(records), 1)
        self.assertEqual(classes["hmb"], 1)
        self.assertTrue(any("Missing/duplicate XML" in item for item in issues))

    def test_conversion_split_and_no_overwrite(self):
        for n in range(10):
            self.sample(n)
        records, _, issues = importer.inspect(self.source)
        self.assertFalse(issues)
        with patch.object(importer, "ROOT", self.root):
            result = importer.prepare(records, {"hmb": "ripe"})
            self.assertEqual(result, {"train": 7, "val": 2, "test": 1})
            labels = list((self.root / "dataset" / "labels").rglob("*.txt"))
            self.assertEqual(len(labels), 10)
            self.assertTrue(all(p.read_text().strip() == "2 0.30000000 0.50000000 0.40000000 0.50000000" for p in labels))
            with self.assertRaises(FileExistsError):
                importer.prepare(records, {"hmb": "ripe"})

    def test_invalid_boxes_and_small_sample(self):
        self.sample(0)
        xml = self.source / "sample_00.xml"
        xml.write_text(xml.read_text().replace("<xmax>50", "<xmax>200"), encoding="utf-8")
        records, _, issues = importer.inspect(self.source)
        self.assertFalse(records)
        self.assertTrue(any("invalid box" in item for item in issues))
        self.sample(1)
        records, _, _ = importer.inspect(self.source)
        with patch.object(importer, "ROOT", self.root):
            with self.assertRaises(ValueError):
                importer.prepare(records, {"hmb": "ripe"})
        self.assertFalse((self.root / "dataset").exists())


if __name__ == "__main__":
    unittest.main()
