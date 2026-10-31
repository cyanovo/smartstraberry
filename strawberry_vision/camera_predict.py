"""Live camera demonstration; not an accuracy evaluation."""

import argparse
from datetime import datetime
import os

from common import ROOT, require_file


def run_camera(model, args):
    import cv2

    backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY
    camera = cv2.VideoCapture(args.camera, backend)
    window = "YOLO camera - Q/Esc: quit, S: save"
    try:
        if not camera.isOpened():
            raise RuntimeError("Cannot open camera. Check permissions, camera index and other apps.")
        cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        print("Live preview only, not accuracy measurement. Q/Esc: quit; S: save.")
        while True:
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError("Camera frame unavailable. Check the camera connection.")
            result = model.predict(
                source=frame, device=args.device, conf=args.conf,
                imgsz=args.imgsz, verbose=False,
            )[0]
            annotated = result.plot()
            cv2.imshow(window, annotated)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q"), ord("Q")):
                break
            if cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                break
            if key in (ord("s"), ord("S")):
                destination = ROOT / "runs" / "camera_snapshots"
                destination.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                for suffix, image in (("original", frame), ("detected", annotated)):
                    path = destination / f"{stamp}_{suffix}.jpg"
                    encoded, data = cv2.imencode(".jpg", image)
                    if not encoded:
                        raise RuntimeError(f"Failed to encode snapshot: {path}")
                    path.write_bytes(data.tobytes())
                print(f"Saved original and detected images: {destination / stamp}")
    finally:
        camera.release()
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="Live detection with a local webcam")
    parser.add_argument("--model", default="weights/yolo26n.pt")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--imgsz", type=int, default=640)
    args = parser.parse_args()
    if args.camera < 0 or args.imgsz <= 0 or not 0 <= args.conf <= 1:
        parser.error("camera must be nonnegative, imgsz positive, conf between 0 and 1")
    weights = require_file(args.model)
    from ultralytics import YOLO

    model = YOLO(str(weights))
    if model.task != "detect":
        parser.error("Use a trusted detection model, not classification or segmentation weights")
    print(f"Model: {weights}\nClasses: {model.names}")
    try:
        run_camera(model, args)
    except KeyboardInterrupt:
        print("Camera stopped.")


if __name__ == "__main__":
    main()
