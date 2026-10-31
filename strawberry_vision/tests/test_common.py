import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common


class LocalChecks(unittest.TestCase):
    def test_missing_model_is_not_downloaded(self):
        with self.assertRaises(FileNotFoundError):
            common.require_file("does-not-exist.pt")

    def test_unique_run_and_path_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(common, "ROOT", Path(directory)):
                common.new_run("round01")
                with self.assertRaises(FileExistsError):
                    common.new_run("round01")
                for name in ("..", "../escape", "a/b", "C:"):
                    with self.assertRaises(ValueError):
                        common.new_run(name)

    def test_class_list_and_absolute_resolution(self):
        import yaml
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "data.yaml"
            config.write_text("names: []\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                common.check_data(config, ("train",))
            images = root / "dataset" / "images" / "train"
            images.mkdir(parents=True)
            (images / "candidate.jpg").touch()
            config.write_text("path: dataset\ntrain: images/train\nnames: [ripe]\n", encoding="utf-8")
            _, _, resolved = common.check_data(config, ("train",))
            self.assertEqual(resolved, root / "dataset")
            output = common.runtime_data(config, ("train",), root)
            self.assertTrue(Path(yaml.safe_load(output.read_text())["path"]).is_absolute())
            with self.assertRaises(ValueError):
                common.check_data(config, ("test",))


if __name__ == "__main__":
    unittest.main()
