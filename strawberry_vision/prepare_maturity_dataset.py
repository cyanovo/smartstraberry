"""Build a reproducible provisional detection split without modifying originals."""

from collections import Counter, defaultdict
import csv
import hashlib
import json
import random
import shutil

import cv2
import numpy as np
import yaml

from common import ROOT


def main():
    source = ROOT / "datasets/kaggle_ripeness_v1/all"
    output = ROOT / "dataset_maturity"
    config_path = ROOT / "data_maturity_platform.yaml"
    if output.exists() or config_path.exists():
        raise FileExistsError("Output already exists; preserve the existing split.")
    mapping = {0: 2, 1: 1, 2: 0}
    records = []
    images = sorted((source / "images").glob("*.jpg"))
    if not images:
        raise ValueError("No source images")
    if {p.stem for p in images} != {p.stem for p in (source / "labels").glob("*.txt")}:
        raise ValueError("Image/label pairing mismatch")
    for path in images:
        raw = path.read_bytes()
        image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError(f"Unreadable image: {path}")
        small = cv2.resize(image, (9, 8), interpolation=cv2.INTER_AREA)
        dhash = int.from_bytes(np.packbits(small[:, 1:] > small[:, :-1]).tobytes(), "big")
        label = source / "labels" / f"{path.stem}.txt"
        boxes, counts = [], Counter()
        for line in label.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            parts = line.split()
            category = mapping[int(parts[0])]
            coords = np.array([float(v) for v in parts[1:]])
            if len(coords) < 6 or len(coords) % 2 or not np.isfinite(coords).all():
                raise ValueError(f"Invalid polygon: {label}")
            if np.any(coords < 0) or np.any(coords > 1):
                raise ValueError(f"Coordinate out of bounds: {label}")
            points = coords.reshape(-1, 2)
            low, high = points.min(axis=0), points.max(axis=0)
            width, height = high - low
            if min(width, height) <= 0:
                raise ValueError(f"Degenerate box: {label}")
            x, y = (low + high) / 2
            boxes.append(f"{category} {x:.8f} {y:.8f} {width:.8f} {height:.8f}")
            counts[category] += 1
        records.append(dict(path=path, sha256=hashlib.sha256(raw).hexdigest(),
                            dhash=dhash, boxes=boxes, counts=counts,
                            label_sha256=hashlib.sha256(label.read_bytes()).hexdigest()))

    # Keep connected components of exact/perceptual duplicates in one split.
    parents = list(range(len(records)))

    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    for i, first in enumerate(records):
        for j in range(i):
            second = records[j]
            if first["sha256"] == second["sha256"] or (first["dhash"] ^ second["dhash"]).bit_count() <= 6:
                parents[find(i)] = find(j)
    groups = defaultdict(list)
    for i in range(len(records)):
        groups[find(i)].append(i)
    total = np.array([len(records)] + [sum(r["counts"][c] for r in records) for c in range(3)])
    ratios = np.array([0.7, 0.2, 0.1])
    target = ratios[:, None] * total
    best = None
    # Search fixed-seed group assignments for image and per-class balance.
    for attempt in range(500):
        order = list(groups.values())
        random.Random(20261025 + attempt).shuffle(order)
        order.sort(key=len, reverse=True)
        totals = np.zeros((3, 4), dtype=int)
        assignments = []
        for group in order:
            vector = np.array([len(group)] + [sum(records[i]["counts"][c] for i in group) for c in range(3)])
            scores = []
            for split in range(3):
                candidate = totals.copy()
                candidate[split] += vector
                scores.append(np.sum(((candidate - target) / np.maximum(target, 1)) ** 2))
            selected = int(np.argmin(scores))
            totals[selected] += vector
            assignments.append((selected, group))
        if np.any(totals == 0):
            continue
        score = float(np.sum(((totals - target) / np.maximum(target, 1)) ** 2))
        if best is None or score < best[0]:
            best = score, assignments, totals
    if best is None:
        raise ValueError("Insufficient independent groups for all classes in each split")
    names = ["train", "val", "test"]
    for split in names:
        for kind in ("images", "labels"):
            (output / kind / split).mkdir(parents=True)
    manifest = []
    for selected, group in best[1]:
        split = names[selected]
        group_id = f"group_{min(group):04d}"
        for i in group:
            record = records[i]
            path = record["path"]
            shutil.copy2(path, output / "images" / split / path.name)
            converted = "\n".join(record["boxes"]) + "\n"
            converted_path = output / "labels" / split / f"{path.stem}.txt"
            converted_path.write_text(converted, encoding="utf-8")
            manifest.append(dict(image=path.name, split=split, group=group_id,
                                 source_sha256=record["sha256"], source_label_sha256=record["label_sha256"],
                                 converted_label_sha256=hashlib.sha256(converted_path.read_bytes()).hexdigest()))
    with (output / "manifest.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest[0]))
        writer.writeheader()
        writer.writerows(sorted(manifest, key=lambda row: row["image"]))
    config = dict(path="dataset_maturity", train="images/train", val="images/val", test="images/test",
                  names={0: "Unripe", 1: "Half-ripe", 2: "Ripe"})
    config_path.write_text("# Provisional mapping; human semantic review pending.\n" + yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    report = dict(status="Provisional training baseline; human review pending", seed=20261025,
                  source="https://www.kaggle.com/datasets/mahyeks/multi-class-strawberry-ripeness-detection-dataset",
                  source_version=1, original_to_platform_id=mapping, groups=len(groups),
                  multi_image_groups=sum(len(g) > 1 for g in groups.values()),
                  grouping="Exact SHA256 or 64-bit dHash Hamming distance <= 6; connected components",
                  splits={name: dict(images=int(row[0]), objects_by_id={c: int(row[c+1]) for c in range(3)})
                          for name, row in zip(names, best[2])},
                  limitations=["Class mapping based on visual sample, not author confirmation",
                               "Perceptual hashing cannot guarantee scene or plant independence",
                               "No exhaustive label review; not a certified benchmark",
                               "No disease data included; no original files modified"])
    (output / "split_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
