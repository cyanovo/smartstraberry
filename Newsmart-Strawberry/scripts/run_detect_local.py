"""
Local Detection Server for Windows
Uses laptop camera directly

Usage:
  pip install ultralytics opencv-python fastapi uvicorn pydantic
  python scripts/run_detect_local.py

API Docs: http://localhost:8081/docs
"""

import sys
import os
import uuid
import base64
import threading
import time
from datetime import datetime
from pathlib import Path

# Add model path
MODEL_DIR = Path(__file__).parent.parent / "backend" / "package" / "yuxi" / "detect" / "models"
MODEL_PATH = MODEL_DIR / "best.pt"

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn

# Try to import YOLO
try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False
    print("WARNING: ultralytics not installed. Run: pip install ultralytics")

app = FastAPI(title="Strawberry Detection Service (Local)")

# CORS - allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model instance
model = None
model_loaded = False

# Camera stream management
camera_streams = {}
camera_locks = {}


def load_model():
    global model, model_loaded
    if not HAS_YOLO:
        print("ERROR: ultralytics not available")
        return False
    if not MODEL_PATH.exists():
        print(f"ERROR: Model file not found: {MODEL_PATH}")
        return False
    try:
        print(f"Loading model: {MODEL_PATH}")
        model = YOLO(str(MODEL_PATH))
        model_loaded = True
        print("Model loaded successfully!")
        if hasattr(model, 'names'):
            print(f"Classes: {model.names}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to load model: {e}")
        return False


# Class names for maturity detection
CLASS_NAMES = {0: "ripe", 1: "half-ripe", 2: "unripe"}
CLASS_NAMES_CN = {0: "成熟", 1: "半成熟", 2: "未成熟"}
CLASS_COLORS = {0: (0, 0, 200), 1: (0, 200, 200), 2: (0, 200, 0)}


class CameraDetectRequest(BaseModel):
    camera_id: int = Field(default=0, description="Camera ID (0=internal, 1+=USB)")
    zone: str = Field(default="A", description="Zone (A/B/C)")
    conf_threshold: float = Field(default=0.5, description="Confidence threshold")


@app.on_event("startup")
async def startup():
    load_model()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model_ready": model_loaded,
        "model_path": str(MODEL_PATH),
        "model_exists": MODEL_PATH.exists(),
    }


@app.get("/cameras")
async def list_cameras():
    """List available cameras"""
    cameras = []
    for cam_id in range(10):
        try:
            cap = cv2.VideoCapture(cam_id)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    name = f"Internal Camera (ID: {cam_id})" if cam_id == 0 else f"USB Camera (ID: {cam_id})"
                    cameras.append({
                        "id": cam_id,
                        "name": f"{name}, {width}x{height}",
                        "resolution": f"{width}x{height}",
                    })
            cap.release()
        except:
            continue
    return cameras


def generate_frames(camera_id: int):
    """Generate MJPEG frames from camera"""
    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Encode frame to JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_bytes = buffer.tobytes()

            # Yield MJPEG frame
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            # Limit to ~15 fps
            time.sleep(0.066)
    finally:
        cap.release()


@app.get("/video/stream/{camera_id}")
async def video_stream(camera_id: int):
    """MJPEG video stream endpoint"""
    return StreamingResponse(
        generate_frames(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/video/snapshot/{camera_id}")
async def video_snapshot(camera_id: int):
    """Get a single frame from camera"""
    try:
        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail=f"Cannot open camera (id={camera_id})")

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        # Warm up
        for _ in range(3):
            cap.read()

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            raise HTTPException(status_code=500, detail="Camera capture failed")

        # Encode to JPEG
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return StreamingResponse(
            iter([buffer.tobytes()]),
            media_type="image/jpeg"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Camera error: {str(e)}")


@app.post("/detect/camera")
async def detect_from_camera(req: CameraDetectRequest):
    """Capture from camera and detect"""
    if not model_loaded:
        raise HTTPException(status_code=503, detail="Model not ready")

    # Capture frame
    try:
        cap = cv2.VideoCapture(req.camera_id)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail=f"Cannot open camera (id={req.camera_id})")

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        # Warm up - discard first few frames
        for _ in range(3):
            cap.read()

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            raise HTTPException(status_code=500, detail="Camera capture failed")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Camera error: {str(e)}")

    return do_detect(frame, req.zone, req.conf_threshold)


@app.post("/detect/image")
async def detect_from_image(
    file: UploadFile,
    zone: str = "A",
    conf_threshold: float = 0.5,
):
    """Upload image for detection"""
    if not model_loaded:
        raise HTTPException(status_code=503, detail="Model not ready")

    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise HTTPException(status_code=400, detail="Cannot decode image")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image read failed: {str(e)}")

    return do_detect(image, zone, conf_threshold)


def do_detect(image: np.ndarray, zone: str, conf_threshold: float) -> dict:
    """Run detection and return results"""
    global model

    # Run YOLO inference
    results = model(image, conf=conf_threshold, verbose=False)

    detections = []
    for result in results:
        if result.boxes is None:
            continue
        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            confidence = float(box.conf[0].cpu().numpy())
            class_id = int(box.cls[0].cpu().numpy())
            detections.append({
                "class_id": class_id,
                "class_name": CLASS_NAMES_CN.get(class_id, "unknown"),
                "confidence": round(confidence, 4),
                "box": [int(x1), int(y1), int(x2), int(y2)],
            })

    # Statistics
    total = len(detections)
    ripe = sum(1 for d in detections if d["class_id"] == 0)
    half = sum(1 for d in detections if d["class_id"] == 1)
    unripe = sum(1 for d in detections if d["class_id"] == 2)
    maturity_ratio = round((ripe / total * 100) if total > 0 else 0, 2)

    # Annotate image
    annotated = image.copy()
    for det in detections:
        x1, y1, x2, y2 = det["box"]
        color = CLASS_COLORS.get(det["class_id"], (255, 255, 255))
        label = f"{det['class_name']} {det['confidence']:.2f}"

        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        cv2.putText(annotated, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # Encode annotated image to base64
    _, buffer = cv2.imencode(".jpg", annotated)
    annotated_base64 = base64.b64encode(buffer).decode("utf-8")

    # Generate recommendation
    if total == 0:
        recommendation = "未检测到番茄，请检查摄像头画面"
    elif ripe / total > 0.7:
        recommendation = "大量番茄已成熟，建议立即采摘！"
    elif ripe / total > 0.4:
        recommendation = "部分番茄已成熟，建议分批采摘"
    elif ripe / total > 0.2:
        recommendation = "番茄正在成熟中，预计 3-5 天可采摘"
    else:
        recommendation = "番茄尚在生长期，请继续培育"

    return {
        "id": uuid.uuid4().hex[:16],
        "zone": zone,
        "camera_id": 0,
        "total_count": total,
        "ripe_count": ripe,
        "half_ripe_count": half,
        "unripe_count": unripe,
        "maturity_ratio": maturity_ratio,
        "confidence_threshold": conf_threshold,
        "recommendation": recommendation,
        "annotated_image_base64": annotated_base64,
        "created_at": datetime.now().isoformat(),
        "detections": detections,
    }


if __name__ == "__main__":
    port = int(os.environ.get("DETECT_PORT", "8081"))
    print("=" * 50)
    print("  Strawberry Maturity Detection Service")
    print("=" * 50)
    print(f"  Model: {MODEL_PATH}")
    print(f"  Model exists: {MODEL_PATH.exists()}")
    print(f"  YOLO available: {HAS_YOLO}")
    print(f"  API Docs: http://localhost:{port}/docs")
    print(f"  Video Stream: http://localhost:{port}/video/stream/0")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=port)
