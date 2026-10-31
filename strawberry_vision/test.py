"""Independent test-set evaluation, preserving the original test screenshot flow."""

import argparse
from common import require_file, check_data, new_run, runtime_data, save_metrics


def main():
    parser = argparse.ArgumentParser(description="Evaluate on the independent test split")
    parser.add_argument("--model", required=True)
    parser.add_argument("--data", default="data.yaml")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    if min(args.imgsz, args.batch) <= 0:
        parser.error("imgsz and batch must be positive")
    weights = require_file(args.model)
    check_data(args.data, ("train", "val", "test"))
    from ultralytics import YOLO

    run = new_run(args.name)
    data = runtime_data(args.data, ("train", "val", "test"), run)
    metrics = YOLO(str(weights), task="detect").val(
        data=str(data), split="test", device=args.device,
        imgsz=args.imgsz, batch=args.batch, workers=0,
        project=str(run), name="test", exist_ok=False,
        plots=True, verbose=True,
    )
    save_metrics(metrics, weights, data, "test")


if __name__ == "__main__":
    main()
