"""Validate Pascal VOC pairs and prepare a YOLO detection dataset."""

from collections import Counter, defaultdict
from pathlib import Path
import csv
import hashlib
import random
import shutil
import xml.etree.ElementTree as ET

from PIL import Image

from common import ROOT

EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
CLASSES = ("unripe", "turning", "ripe")
SPLITS = ("train", "val", "test")


def inspect(source):
    source = Path(source).resolve()
    if not source.is_dir():
        raise ValueError("Source folder does not exist")
    images = sorted(p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS)
    xmls = sorted(source.rglob("*.xml"))
    by_stem = defaultdict(list)
    for path in images:
        by_stem[path.stem.lower()].append(path)
    labels = defaultdict(list)
    for path in xmls:
        labels[path.stem.lower()].append(path)
    issues = []
    for stem, paths in by_stem.items():
        if len(paths) != 1:
            issues.append(f"Duplicate image name: {stem}")
        if len(labels[stem]) != 1:
            issues.append(f"Missing/duplicate XML: {stem}")
    for stem in labels.keys() - by_stem.keys():
        issues.append(f"XML without image: {stem}")
    if not images:
        issues.append("No images found")
    records = []
    for image in images:
        if len(by_stem[image.stem.lower()]) != 1 or len(labels[image.stem.lower()]) != 1:
            continue
        xml = labels[image.stem.lower()][0]
        try:
            root = ET.parse(xml).getroot()
            if root.tag != "annotation":
                raise ValueError("not a VOC annotation")
            with Image.open(image) as opened:
                width, height = opened.size
                opened.verify()
            declared = (int(root.findtext("size/width")), int(root.findtext("size/height")))
            if declared != (width, height):
                raise ValueError(f"XML size {declared} differs from image size {(width, height)}")
            filename = root.findtext("filename")
            if filename and filename.lower() != image.name.lower():
                raise ValueError("XML filename differs from image")
            boxes = []
            for obj in root.findall("object"):
                name = (obj.findtext("name") or "").strip()
                if not name:
                    raise ValueError("empty class name")
                box = obj.find("bndbox")
                if box is None:
                    raise ValueError("object without bndbox")
                coords = tuple(float(box.findtext(key)) for key in ("xmin", "ymin", "xmax", "ymax"))
                x1, y1, x2, y2 = coords
                if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
                    raise ValueError(f"invalid box {coords}")
                boxes.append((name, coords))
            if not boxes:
                raise ValueError("empty XML: confirm negatives separately")
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            records.append((image, xml, width, height, boxes, digest))
        except (ET.ParseError, OSError, ValueError, TypeError, AttributeError) as exc:
            issues.append(f"{xml.name}: {exc}")
    counts = Counter(name for _, _, _, _, boxes, _ in records for name, _ in boxes)
    return records, counts, sorted(issues)


def prepare(records, mapping, destination=None, seed=20261027):
    destination = Path(destination or ROOT / "dataset").resolve()
    if destination.exists():
        raise FileExistsError(f"Dataset already exists: {destination}")
    if destination != (ROOT / "dataset").resolve():
        raise ValueError("Only the dataset directory used by data.yaml is supported")
    if not records or set(mapping) != {name for row in records for name, _ in row[4]}:
        raise ValueError("Confirm a mapping for every source class")
    if any(value not in CLASSES for value in mapping.values()):
        raise ValueError("Unknown target class")
    names = [row[0].name.lower() for row in records]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate output image names")
    for image, xml, width, height, boxes, digest in records:
        if not image.is_file() or not xml.is_file() or hashlib.sha256(image.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Source changed since inspection: {image}")
    groups = defaultdict(list)
    for row in records:
        groups[row[5]].append(row)
    if len(groups) < 10:
        raise ValueError("At least 10 independent images/groups are needed for a 7:2:1 split")
    ordered = list(groups.values())
    random.Random(seed).shuffle(ordered)
    # Largest remainder, with a minimum of one independent group per split.
    n = len(ordered)
    train, val = round(n * .7), round(n * .2)
    test = n - train - val
    if min(train, val, test) < 1:
        raise ValueError("Not enough independent groups for each split")
    allocations = dict(zip(SPLITS, (train, val, test)))
    assignments = {}
    offset = 0
    for split, size in allocations.items():
        for group in ordered[offset:offset + size]:
            for row in group:
                assignments[row[0]] = split
        offset += size
    # Do not create the destination until all validation has finished.
    rows = []
    try:
        destination.mkdir(parents=False, exist_ok=False)
        for split in SPLITS:
            for kind in ("images", "labels"):
                (destination / kind / split).mkdir(parents=True, exist_ok=True)
        for image, xml, width, height, boxes, digest in records:
            split = assignments[image]
            shutil.copy2(image, destination / "images" / split / image.name)
            lines = []
            for name, (x1, y1, x2, y2) in boxes:
                lines.append(f"{CLASSES.index(mapping[name])} {(x1+x2)/(2*width):.8f} {(y1+y2)/(2*height):.8f} {(x2-x1)/width:.8f} {(y2-y1)/height:.8f}")
            (destination / "labels" / split / f"{image.stem}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
            rows.append((image.name, split, digest, hashlib.sha256(xml.read_bytes()).hexdigest()))
        with (destination / "manifest.csv").open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream)
            writer.writerow(("image", "split", "source_sha256", "xml_sha256"))
            writer.writerows(sorted(rows))
    except Exception:
        # Preserve partial output for diagnosis; never remove user data automatically.
        raise
    return Counter(assignments.values())
