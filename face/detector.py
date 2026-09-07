import cv2
import numpy as np
import insightface
from typing import Dict, Any, Optional, Tuple

class FaceDetector:
    def __init__(self, model_name: str = "buffalo_l", det_size: Tuple[int, int] = (640, 640)):
        """Initialize InsightFace analysis app."""
        self.app = insightface.app.FaceAnalysis(name=model_name, providers=['CPUExecutionProvider'])
        self.app.prepare(ctx_id=0, det_size=det_size)

    def detect_and_encode(self, image_input) -> Dict[str, Any]:
        """
        Detect face in image (file path or numpy array) and extract 512-d normalized embedding.
        Returns dictionary with bbox, score, raw embedding, normalized embedding, crop image, and dimensions.
        """
        if isinstance(image_input, str):
            img = cv2.imread(image_input)
            if img is None:
                raise ValueError(f"Unable to read image file at: {image_input}")
        elif isinstance(image_input, np.ndarray):
            img = image_input
        else:
            raise ValueError("Input must be a file path string or numpy ndarray image.")

        faces = self.app.get(img)
        if not faces:
            raise ValueError("No face detected in the provided image.")

        # Select the primary (largest bounding box area) face
        primary_face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        
        raw_embedding = primary_face.embedding.astype(np.float32)
        norm = np.linalg.norm(raw_embedding)
        norm_embedding = raw_embedding / norm if norm > 0 else raw_embedding

        bbox = primary_face.bbox.astype(int)
        h, w, _ = img.shape
        
        # Add 20% padding around bounding box for clean face crop
        bw = bbox[2] - bbox[0]
        bh = bbox[3] - bbox[1]
        pad_x = int(bw * 0.15)
        pad_y = int(bh * 0.15)

        x1 = max(0, bbox[0] - pad_x)
        y1 = max(0, bbox[1] - pad_y)
        x2 = min(w, bbox[2] + pad_x)
        y2 = min(h, bbox[3] + pad_y)

        face_crop = img[y1:y2, x1:x2]

        return {
            "bbox": bbox,
            "det_score": float(primary_face.det_score),
            "raw_embedding": raw_embedding,
            "norm_embedding": norm_embedding,
            "face_crop": face_crop,
            "image_shape": img.shape,
            "total_faces_detected": len(faces)
        }
