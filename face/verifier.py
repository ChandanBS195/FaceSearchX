import cv2
import numpy as np
import insightface
from typing import Dict, Any, List, Optional
from .detector import FaceDetector

class FaceVerifier:
    def __init__(self, detector: Optional[FaceDetector] = None):
        """Initialize Face Verifier with shared or new FaceDetector."""
        self.detector = detector if detector is not None else FaceDetector()

    @staticmethod
    def compute_cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Calculate cosine similarity between two feature vectors."""
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        sim = float(np.dot(emb1, emb2) / (norm1 * norm2))
        return max(0.0, min(1.0, sim))

    def verify_candidate(
        self,
        target_norm_embedding: np.ndarray,
        candidate_image_path: str,
        threshold: float = 0.50
    ) -> Dict[str, Any]:
        """
        Detect face in candidate image and compare cosine similarity against target embedding.
        Returns verification result dictionary.
        """
        try:
            cand_result = self.detector.detect_and_encode(candidate_image_path)
            cand_embedding = cand_result["norm_embedding"]
            similarity = self.compute_cosine_similarity(target_norm_embedding, cand_embedding)
            is_match = similarity >= threshold

            return {
                "success": True,
                "face_detected": True,
                "similarity": similarity,
                "similarity_pct": round(similarity * 100, 2),
                "is_match": is_match,
                "det_score": cand_result["det_score"],
                "candidate_bbox": cand_result["bbox"].tolist(),
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "face_detected": False,
                "similarity": 0.0,
                "similarity_pct": 0.0,
                "is_match": False,
                "det_score": 0.0,
                "candidate_bbox": None,
                "error": str(e)
            }
