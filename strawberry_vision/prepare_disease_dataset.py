"""Convert the verified Strawberry Disease Data polygon ZIP to YOLO detection boxes."""

import argparse
from collections import Counter
import json
import math
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent
PREFIX = "Strawberry Disease Data"
SPLITS = ("train", "val", "test")
NAMES = (
    "angular_leafspot",
    "anthracnose_fruit_rot",
    "blossom_blight",
    "gray_mold",
    "leaf_spot",
    "powdery_mildew_fruit",
    "powdery_mildew_leaf",
)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def polygon_to_box(line, location):
    parts = line.split()
    if len(parts) < 7 or (len(parts) - 1) % 2:
        raise ValueError(f"{location}: expected a class ID and at least 3 polygon points")
    try:
        class_id = int(parts[0])
        coordinates = [float(item) for item in parts[1:]]
    except ValueError as exc:
        raise ValueError(f"{location}: invalid class or coordinate") from exc
    if not 0 <= class_id < len(NAMES) or not all(math.isfinite(v) for v in coordinates):
        raise ValueError(f"{location}: invalid class ID or non-finite coordinate")
    clipped = any(v < 0 or v > 1 for v in coordinates)
    x = [min(1.0, max(0.0, v)) for v in coordinates[::2]]
    y = [min(1.0, max(0.0, v)) for v in coordinates[1::2]]
    left, right, top, bottom = min(x), max(x), min(y), max(y)
    if left >= right or top >= bottom:
        raise ValueError(f"{location}: polygon has no valid box after clipping")
    box = (class_id, (left + right) / 2, (top + bottom) / 2, right - left, bottom - top)
    return f"{box[0]} " + " ".join(f"{v:.8f}" for v in box[1:]), class_id, clipped


def inspect(archive):
    images, labels = {}, {}
    for info in archive.infolist():
        if info.is_dir():
            continue
        name = PurePosixPath(info.filename)
        parts = name.parts
        if (len(parts) != 4 or parts[0] != PREFIX or parts[1] not in SPLITS
                or parts[2] not in ("images", "labels")
                or not parts[3] or parts[3] in (".", "..")
                or (info.external_attr >> 16) & 0o170000 == 0o120000):
            raise ValueError(f"Unexpected or unsafe ZIP entry: {info.filename}")
        if parts[2] == "images" and name.suffix.lower() in IMAGE_EXTENSIONS:
            target = images
        elif parts[2] == "labels" and name.suffix.lower() == ".txt":
            target = labels
        else:
            raise ValueError(f"Unexpected file type: {info.filename}")
        key = (parts[1], name.stem.casefold())
        if key in target:
            raise ValueError(f"Duplicate filename stem: {info.filename}")
        target[key] = info
    if not images or images.keys() != labels.keys():
        raise ValueError(f"Image/label mismatch: {len(images)} images, {len(labels)} labels")
    if any(not any(split == item[0] for item in images) for split in SPLITS):
        raise ValueError("train, val and test must each have images")

    converted = {}
    classes = Counter()
    clipped = []
    for key in sorted(labels):
        info = labels[key]
        try:
            text = archive.read(info).decode("utf-8-sig")
        except UnicodeError as exc:
            raise ValueError(f"{info.filename}: invalid UTF-8 label") from exc
        lines = []
        for number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            box, class_id, was_clipped = polygon_to_box(line, f"{info.filename}:{number}")
            lines.append(box)
            classes[NAMES[class_id]] += 1
            if was_clipped:
                clipped.append(f"{info.filename}:{number}")
        if not lines:
            raise ValueError(f"{info.filename}: empty label")
        converted[key] = "\n".join(lines) + "\n"
    return images, converted, classes, clipped


def prepare(source, destination):
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if destination.exists():
        raise FileExistsError(destination)
    if destination == source.parent or destination in source.parents:
        raise ValueError("Output cannot contain or replace the source archive")
    if not destination.parent.is_dir():
        raise FileNotFoundError(destination.parent)

    with zipfile.ZipFile(source) as archive:
        images, converted, classes, clipped = inspect(archive)
        counts = Counter(split for split, _ in images)
        report = {
            "source": source.name,
            "images_by_split": {split: counts[split] for split in SPLITS},
            "instances_by_class": {name: classes[name] for name in NAMES},
            "clipped_polygon_lines": clipped,
            "note": "Polygon coordinates clipped to [0,1]; boxes are polygon envelopes. Review source annotations.",
        }
        with tempfile.TemporaryDirectory(prefix=".disease-build-", dir=destination.parent) as temporary:
            staged = Path(temporary) / "dataset"
            for key, info in images.items():
                split, _ = key
                stem = PurePosixPath(info.filename).stem
                image = staged / "images" / split / (stem + PurePosixPath(info.filename).suffix)
                image.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as original, image.open("xb") as output:
                    shutil.copyfileobj(original, output)
                label = staged / "labels" / split / (stem + ".txt")
                label.parent.mkdir(parents=True, exist_ok=True)
                label.write_text(converted[key], encoding="ascii")
            (staged / "conversion_report.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            if destination.exists():
                raise FileExistsError(destination)
            staged.rename(destination)
    return report


def main():
    parser = argparse.ArgumentParser(description="Prepare separate strawberry disease detection data")
    parser.add_argument("--source", default=str(ROOT / "downloads" / "strawberry-disease-caozhihao-v1.zip"))
    parser.add_argument("--output", default=str(ROOT / "dataset_disease"))
    args = parser.parse_args()
    report = prepare(args.source, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
