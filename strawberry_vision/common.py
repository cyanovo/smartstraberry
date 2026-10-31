"""Local paths and dataset checks shared by the training entry points."""

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent


def local_path(value):
    path = Path(value).expanduser()
    return (path if path.is_absolute() else ROOT / path).resolve()


def require_file(value):
    path = local_path(value)
    if not path.is_file():
        raise FileNotFoundError(f"Required local file not found: {path}")
    return path


def check_data(value, splits):
    import yaml

    path = require_file(value)
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("Dataset YAML must be a mapping.")
    if "download" in config:
        raise ValueError("Remove the dataset download directive; use verified local data.")
    names = config.get("names")
    if isinstance(names, dict):
        if set(names) != set(range(len(names))):
            raise ValueError("Class IDs must be consecutive integers starting at 0.")
        names = [names[index] for index in range(len(names))]
    if not isinstance(names, list) or not names:
        raise ValueError("Fill names with the confirmed ordered class list before training.")
    if any(not isinstance(name, str) or not name.strip() for name in names):
        raise ValueError("Class names must be nonempty strings.")
    if len(set(names)) != len(names):
        raise ValueError("Class names must be unique.")
    root = Path(config.get("path") or ".")
    root = (root if root.is_absolute() else path.parent / root).resolve()
    # This small teaching project intentionally uses directories, not image-list files.
    for split in splits:
        entry = config.get(split)
        if not isinstance(entry, str) or not entry:
            raise ValueError(f"Missing dataset directory: {split}")
        directory = (root / entry).resolve()
        if not directory.is_dir():
            raise FileNotFoundError(f"Missing {split} directory: {directory}")
        extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
        if not any(p.is_file() and p.suffix.lower() in extensions for p in directory.rglob("*")):
            raise ValueError(f"No candidate images found in {directory}")
    return path, config, root


def runtime_data(value, splits, destination):
    import yaml

    _, config, root = check_data(value, splits)
    config["path"] = str(root)
    path = destination / "dataset.resolved.yaml"
    path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def new_run(name):
    if not name or Path(name).name != name or name in {".", ".."} or ":" in name:
        raise ValueError("Run name must be a single directory name.")
    path = ROOT / "runs" / name
    path.mkdir(parents=True, exist_ok=False)
    return path


def save_metrics(metrics, weights, data, split):
    import ultralytics

    destination = Path(metrics.save_dir)
    report = {
        "weights": str(weights), "data": str(data), "split": split,
        "ultralytics": ultralytics.__version__,
        "metrics": {str(k): float(v) for k, v in metrics.results_dict.items()},
        "speed_ms_per_image": metrics.speed,
        "class_names": metrics.names,
    }
    (destination / "metrics.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Metrics saved to: {destination / 'metrics.json'}")
