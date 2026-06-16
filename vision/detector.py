from ultralytics import YOLO
import numpy as np

class Detector:
    def __init__(self, weights="yolov8n.pt"):
        self.model = YOLO(weights)

    def predict(self, image, conf=0.25, imgsz=640):
        """
        image: path or numpy array (BGR or RGB)
        returns: list of detections for the first frame: [{'xyxy': [x1,y1,x2,y2], 'conf': float, 'cls': int}, ...]
        """
        results = self.model.predict(source=image, conf=conf, imgsz=imgsz, verbose=False)
        if len(results) == 0:
            return []

        r = results[0] if isinstance(results, (list, tuple)) else results
        if not hasattr(r, "boxes") or r.boxes is None:
            return []

        boxes = []
        for box in r.boxes:
            xyxy = box.xyxy.tolist()
            if isinstance(xyxy, list) and len(xyxy) == 1:
                xyxy = xyxy[0]
            boxes.append({
                "xyxy": xyxy,
                "conf": float(box.conf),
                "cls": int(box.cls),
            })
        return boxes