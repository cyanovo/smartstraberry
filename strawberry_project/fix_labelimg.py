"""Run with the Python environment that contains LabelImg."""

import importlib.util
import shutil
from pathlib import Path


def main():
    spec = importlib.util.find_spec("libs.canvas")
    if spec is None or spec.origin is None:
        raise SystemExit("LabelImg is not installed in this Python environment.")
    path = Path(spec.origin)
    original = path.read_text(encoding="utf-8")
    replacements = {
        "p.drawRect(left_top.x(), left_top.y(), rect_width, rect_height)":
            "p.drawRect(int(left_top.x()), int(left_top.y()), int(rect_width), int(rect_height))",
        "p.drawLine(self.prev_point.x(), 0, self.prev_point.x(), self.pixmap.height())":
            "p.drawLine(int(self.prev_point.x()), 0, int(self.prev_point.x()), self.pixmap.height())",
        "p.drawLine(0, self.prev_point.y(), self.pixmap.width(), self.prev_point.y())":
            "p.drawLine(0, int(self.prev_point.y()), self.pixmap.width(), int(self.prev_point.y()))",
    }
    updated = original
    for old, new in replacements.items():
        if old not in updated and new not in updated:
            raise SystemExit("Unexpected LabelImg source version; no files changed.")
        updated = updated.replace(old, new)
    if updated == original:
        print("LabelImg drawing fix is already installed.")
        return
    backup = path.with_suffix(".py.before-coordinate-fix")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(updated, encoding="utf-8")
    print(f"Fixed: {path}")
    print(f"Backup: {backup}")
    print("Restart LabelImg to load the fix.")


if __name__ == "__main__":
    main()
