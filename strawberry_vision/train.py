"""Training flow adapted from the team's original PPT code screenshot."""

import argparse
from common import require_file, check_data, new_run, runtime_data, save_metrics
def main():
    parser = argparse.ArgumentParser(description="Train a local Ultralytics detection model")
    parser.add_argument("--model", default="weights/yolo26n.pt")
    parser.add_argument("--data", default="data.yaml")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--name", required=True)
    parser.add_argument("--degrees", type=float, default=0.0)
    parser.add_argument("--hsv-s", type=float, default=0.7)
    args = parser.parse_args()
    if min(args.epochs, args.batch, args.imgsz) <= 0:
        parser.error("epochs, batch and imgsz must be positive")
    if not 0 <= args.degrees <= 180 or not 0 <= args.hsv_s <= 1:
        parser.error("degrees must be in [0, 180], hsv-s in [0, 1]")
    weights = require_file(args.model)
    check_data(args.data, ("train", "val"))
    from ultralytics import YOLO

    run = new_run(args.name)
    data = runtime_data(args.data, ("train", "val"), run)
    # LIVE DEMO START: load, train, validate, and save real metrics.
    model = YOLO(str(weights), task="detect")
    print(f"Initial weights: {weights}")
    print(f"Resolved dataset: {data}")
    model.train(
        data=str(data),
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        workers=0,
        project=str(run),
        name="train",
        exist_ok=False,
        seed=0,
        deterministic=True,
        degrees=args.degrees,
        hsv_s=args.hsv_s,
        plots=True,
    )
    best = require_file(model.trainer.best)
    best_model = YOLO(str(best), task="detect")
    metrics = best_model.val(
        data=str(data),
        split="val",
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=0,
        project=str(run),
        name="validation",
        exist_ok=False,
        plots=True,
    )
    save_metrics(metrics, best, data, "val")
    print(f"Best weights: {best}")
    print(f"Precision: {metrics.box.mp:.4f}")
    print(f"Recall: {metrics.box.mr:.4f}")
    print(f"mAP50: {metrics.box.map50:.4f}")
    print(f"mAP50-95: {metrics.box.map:.4f}")
    # LIVE DEMO END


if __name__ == "__main__":
    main()
