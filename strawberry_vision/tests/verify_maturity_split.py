"""Check generated split integrity without training or changing data."""

from collections import defaultdict
import csv
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, check_data


def main():
    check_data("data_maturity_platform.yaml", ("train", "val", "test"))
    root = ROOT / "dataset_maturity"
    source = ROOT / "datasets/kaggle_ripeness_v1/all"
    with (root / "manifest.csv").open(encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    groups, hashes = defaultdict(set), defaultdict(set)
    names, objects = set(), 0
    assert len(rows) == 566
    for row in rows:
        groups[row["group"]].add(row["split"])
        hashes[row["source_sha256"]].add(row["split"])
        assert row["image"] not in names
        names.add(row["image"])
        image = root / "images" / row["split"] / row["image"]
        label = root / "labels" / row["split"] / f"{image.stem}.txt"
        assert hashlib.sha256(image.read_bytes()).hexdigest() == row["source_sha256"]
        assert hashlib.sha256((source / "images" / image.name).read_bytes()).hexdigest() == row["source_sha256"]
        assert hashlib.sha256((source / "labels" / label.name).read_bytes()).hexdigest() == row["source_label_sha256"]
        assert hashlib.sha256(label.read_bytes()).hexdigest() == row["converted_label_sha256"]
        for line in label.read_text().splitlines():
            parts = line.split()
            assert len(parts) == 5 and int(parts[0]) in (0, 1, 2)
            x, y, w, h = map(float, parts[1:])
            assert 0 < w <= 1 and 0 < h <= 1
            assert -1e-7 <= x-w/2 and x+w/2 <= 1.0000001
            assert -1e-7 <= y-h/2 and y+h/2 <= 1.0000001
            objects += 1
    assert all(len(s) == 1 for s in groups.values())
    assert all(len(s) == 1 for s in hashes.values())
    assert objects == 1734
    print("PASS: YAML, 566 image pairs, unchanged originals, 1734 boxes, group isolation")


if __name__ == "__main__":
    main()
