"""Separate single-image demonstration; this does not measure accuracy."""

import argparse
from common import require_file, new_run


def main():
    parser = argparse.ArgumentParser(description="Predict one local image")
    parser.add_argument("--model", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    if not 0 <= args.conf <= 1:
        parser.error("conf must be between 0 and 1")
    weights, image = require_file(args.model), require_file(args.source)
    if image.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}:
        parser.error("source must be a local image")
    from ultralytics import YOLO

    run = new_run(args.name)
    results = YOLO(str(weights), task="detect").predict(
        source=str(image), device=args.device, conf=args.conf,
        save=True, save_txt=True, save_conf=True,
        project=str(run), name="predict", exist_ok=False,
    )
    print(f"Prediction saved to: {results[0].save_dir}")


if __name__ == "__main__":
    main()
