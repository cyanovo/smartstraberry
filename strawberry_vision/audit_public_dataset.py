"""Audit the downloaded Kaggle v1 archive without guessing class names."""

from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parent


def main():
    source = ROOT / "datasets/kaggle_ripeness_v1/all"
    output = ROOT / "datasets/kaggle_ripeness_v1/audit"
    output.mkdir(exist_ok=True)
    counts = Counter()
    hashes = defaultdict(list)
    errors = []
    previews = []
    images = sorted((source / "images").glob("*.jpg"))
    labels = sorted((source / "labels").glob("*.txt"))
    empty = 0
    crops = defaultdict(list)
    for path in images:
        raw = path.read_bytes()
        hashes[hashlib.sha256(raw).hexdigest()].append(path.name)
        image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            errors.append(f"Unreadable image: {path.name}")
            continue
        height, width = image.shape[:2]
        label = source / "labels" / (path.stem + ".txt")
        if not label.is_file():
            errors.append(f"Missing label: {path.name}")
            continue
        lines = [line for line in label.read_text().splitlines() if line.strip()]
        empty += not lines
        annotated = image.copy()
        for number, line in enumerate(lines, 1):
            try:
                parts = line.split()
                class_id = int(parts[0])
                values = [float(value) for value in parts[1:]]
                if class_id not in (0, 1, 2):
                    raise ValueError("Unknown class ID")
                if len(values) < 6 or len(values) % 2:
                    raise ValueError("Not a YOLO polygon")
                if any(not math.isfinite(v) or not 0 <= v <= 1 for v in values):
                    raise ValueError("Invalid normalized coordinate")
                points = np.array(values).reshape(-1, 2)
                if np.any(np.ptp(points, axis=0) <= 0):
                    raise ValueError("Degenerate extent")
                counts[class_id] += 1
                pixels = np.rint(points * [width - 1, height - 1]).astype(np.int32)
                color = [(50, 70, 230), (0, 190, 230), (80, 180, 50)][class_id]
                cv2.polylines(annotated, [pixels], True, color, 2)
                x, y = pixels.min(axis=0)
                x2, y2 = pixels.max(axis=0)
                cv2.putText(annotated, f"ID {class_id}", (int(x), max(18, int(y))),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                if len(crops[class_id]) < 12 and x2 - x >= 30 and y2 - y >= 30:
                    crop = image[y:y2 + 1, x:x2 + 1]
                    tile = np.full((180, 180, 3), 245, dtype=np.uint8)
                    scale = min(160 / crop.shape[1], 140 / crop.shape[0])
                    resized = cv2.resize(crop, None, fx=scale, fy=scale)
                    tile[30:30 + resized.shape[0], 10:10 + resized.shape[1]] = resized
                    cv2.putText(tile, f"Source ID {class_id}", (8, 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (30, 30, 30), 1)
                    crops[class_id].append(tile)
            except (ValueError, IndexError) as exc:
                errors.append(f"{label.name}:{number}: {exc}")
        if len(previews) < 6:
            destination = output / f"preview_{len(previews) + 1}.jpg"
            destination.write_bytes(cv2.imencode(".jpg", annotated)[1].tobytes())
            previews.append({"file": destination.name, "source": path.name})
    orphan = sorted({p.stem for p in labels} - {p.stem for p in images})
    if all(len(crops[c]) == 12 for c in range(3)):
        sheet = np.vstack([np.hstack(crops[c][offset:offset + 6])
                           for c in range(3) for offset in (0, 6)])
        (output / "class_id_contact_sheet.jpg").write_bytes(
            cv2.imencode(".jpg", sheet)[1].tobytes())
    archive = ROOT / "downloads/strawberry-ripeness-kaggle-v1.zip"
    report = {
        "source": "https://www.kaggle.com/datasets/mahyeks/multi-class-strawberry-ripeness-detection-dataset",
        "version": 1,
        "archive_bytes": archive.stat().st_size,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "images": len(images), "labels": len(labels), "empty_labels": empty,
        "format": "YOLO polygons, not five-column detection boxes",
        "objects_by_original_id": dict(sorted(counts.items())),
        "objects": sum(counts.values()), "errors": errors, "orphan_labels": orphan,
        "exact_duplicate_groups": [v for v in hashes.values() if len(v) > 1],
        "previews": previews,
        "class_mapping": "Not supplied in archive; not verified from author",
        "split": "Only all/ supplied; no official split files",
        "paper_objects": 1169,
        "status": "Downloaded and structurally audited; semantic mapping and split pending",
        "limitations": ["No exhaustive semantic review", "No near-duplicate detection",
                        "Do not report paper metrics as local results"],
    }
    (output / "audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if errors or orphan:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
