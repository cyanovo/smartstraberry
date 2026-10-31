"""Build review-only YOLO labels and overlays, without inventing train/test splits."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="annotation_review_v01")
    args = parser.parse_args()
    import cv2
    import numpy as np

    root = Path(__file__).resolve().parent
    source = root.parent / "strawberry_project" / "images"
    specification = json.loads((root / "annotations_draft.json").read_text(encoding="utf-8"))
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    loaded = []
    counts = [0] * len(specification["classes"])
    for item in specification["images"]:
        image_path = source / item["file"]
        image = cv2.imdecode(np.fromfile(str(image_path), dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"Cannot read {image_path}")
        height, width = image.shape[:2]
        if [width, height] != item["size"]:
            raise ValueError(f"Unexpected dimensions for {image_path}: {width}x{height}")
        for category, x1, y1, x2, y2 in item["boxes"]:
            if not (0 <= category < len(counts) and 0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
                raise ValueError(f"Invalid box for {image_path}")
            counts[category] += 1
        loaded.append((item, image_path, image))
    output.mkdir(parents=True, exist_ok=False)
    for folder in ("images", "labels", "previews"):
        (output / folder).mkdir()
    manifest = []
    for item, image_path, image in loaded:
        width, height = item["size"]
        lines = []
        for category, x1, y1, x2, y2 in item["boxes"]:
            lines.append(f"{category} {(x1+x2)/(2*width):.6f} {(y1+y2)/(2*height):.6f} {(x2-x1)/width:.6f} {(y2-y1)/height:.6f}")
            color = [(70, 180, 50), (0, 180, 255), (50, 50, 230)][category]
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
            cv2.putText(image, specification["classes"][category], (x1, max(14, y1-4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
        shutil.copy2(image_path, output / "images" / image_path.name)
        (output / "labels" / f"{image_path.stem}.txt").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        ok, encoded = cv2.imencode(".jpg", image)
        if not ok:
            raise RuntimeError(f"Cannot encode preview: {image_path}")
        encoded.tofile(str(output / "previews" / f"{image_path.stem}.jpg"))
        manifest.append({"file": image_path.name, "sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(), "boxes": len(lines), "status": "pending_human_review", "note": item["note"]})
    report = {"status": specification["status"], "image_count": len(loaded), "class_counts": dict(zip(specification["classes"], counts)), "manifest": manifest, "excluded": specification["excluded"], "split": "none_review_only"}
    (output / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy2(root / "classes.txt", output / "classes.txt")
    print(json.dumps({"output": str(output.resolve()), "images": len(loaded), "class_counts": report["class_counts"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
