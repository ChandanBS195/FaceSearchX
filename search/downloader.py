import os
import requests
import hashlib
from typing import List, Dict, Any

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

class CandidateDownloader:
    def __init__(self, output_dir: str = "candidates", timeout: int = 8):
        """Initialize candidate image downloader."""
        self.output_dir = output_dir
        self.timeout = timeout
        os.makedirs(self.output_dir, exist_ok=True)

    def download_image(self, url: str, candidate_id: str) -> str:
        """Download image from URL and save locally. Returns saved file path."""
        res = requests.get(url, headers=DEFAULT_HEADERS, timeout=self.timeout, stream=True)
        if res.status_code != 200:
            raise RuntimeError(f"HTTP Status {res.status_code}")

        content_type = res.headers.get("content-type", "").lower()
        ext = ".jpg"
        if "png" in content_type or url.lower().endswith(".png"):
            ext = ".png"
        elif "webp" in content_type or url.lower().endswith(".webp"):
            ext = ".webp"

        filename = f"candidate_{candidate_id}{ext}"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "wb") as f:
            for chunk in res.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        if os.path.getsize(filepath) < 100:
            os.remove(filepath)
            raise RuntimeError("Downloaded file too small or invalid.")

        return filepath

    def download_candidates(self, candidates: List[Dict[str, Any]], max_candidates: int = 30) -> List[Dict[str, Any]]:
        """
        Download candidate images for verification.
        Returns list of downloaded candidates with local 'local_path' field populated.
        """
        downloaded = []
        for i, cand in enumerate(candidates[:max_candidates]):
            cand_id = f"{i+1}_{hashlib.md5(cand['link'].encode('utf-8')).hexdigest()[:6]}"
            local_path = None

            # Attempt 1: Try primary image URL
            if cand.get("image"):
                try:
                    local_path = self.download_image(cand["image"], cand_id)
                except Exception:
                    local_path = None

            # Attempt 2: Fallback to Google thumbnail URL if main image fails
            if not local_path and cand.get("thumbnail"):
                try:
                    local_path = self.download_image(cand["thumbnail"], f"{cand_id}_thumb")
                except Exception:
                    local_path = None

            if local_path:
                cand_copy = dict(cand)
                cand_copy["candidate_id"] = cand_id
                cand_copy["local_path"] = local_path
                downloaded.append(cand_copy)

        return downloaded
