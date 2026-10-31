import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vision_gui import Workbench


class WorkbenchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.app = Workbench()
        except Exception as exc:
            raise unittest.SkipTest(f"Desktop display unavailable: {exc}") from exc
        cls.app.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.app.close()

    def test_scan_does_not_block_ui(self):
        with tempfile.TemporaryDirectory() as directory:
            self.app.source.set(directory)

            def slow_scan(_source):
                time.sleep(.25)
                return [], {}, ["No images found"]

            with patch("vision_gui.inspect", side_effect=slow_scan):
                start = time.monotonic()
                self.app.scan()
                self.assertLess(time.monotonic() - start, .15)
                self.assertTrue(self.app.data_busy)
                self.app.update()
                deadline = time.monotonic() + 2
                while self.app.data_busy and time.monotonic() < deadline:
                    self.app.update()
                    time.sleep(.02)
            self.assertFalse(self.app.data_busy)
            self.assertIn("问题 1 项", self.app.summary.get())

    def test_chart_reuses_decoded_image(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as directory:
            Image.new("RGB", (400, 200), "red").save(Path(directory) / "results.png")
            self.app.run_dir.set(directory)
            self.app.load_charts()
            image = self.app.chart_image
            self.app.show_chart()
            self.assertIs(self.app.chart_image, image)

    def test_data_controls_fit_minimum_window(self):
        self.app.deiconify()
        self.app.geometry("780x570")
        self.app.update()
        self.assertLessEqual(self.app.make_button.winfo_rootx() + self.app.make_button.winfo_width(),
                             self.app.winfo_rootx() + self.app.winfo_width())
        self.assertLessEqual(self.app.make_button.winfo_rooty() + self.app.make_button.winfo_height(),
                             self.app.winfo_rooty() + self.app.winfo_height())
        self.app.withdraw()


if __name__ == "__main__":
    unittest.main()
