import os
import cv2
import requests
import tempfile
import numpy as np
from typing import Dict, Any, List, Optional

DEFAULT_SERPAPI_KEY = "66193a82af48b33a7363ed3ae7eed9ef70fea3d0d5ae4c50353e99cf7e127383"

class GoogleLensSearcher:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize SerpApi Google Lens searcher with API Key."""
        self.api_key = api_key or os.environ.get("SERPAPI_API_KEY") or DEFAULT_SERPAPI_KEY

    def upload_image_to_public_url(self, image_input) -> str:
        """
        Upload local image file path or numpy array face crop to Catbox / Litterbox.
        Returns a publicly accessible image URL.
        """
        temp_file_path = None
        if isinstance(image_input, str):
            if image_input.startswith("http://") or image_input.startswith("https://"):
                return image_input
            temp_file_path = image_input
        elif isinstance(image_input, np.ndarray):
            fd, temp_file_path = tempfile.mkstemp(suffix=".jpg")
            os.close(fd)
            cv2.imwrite(temp_file_path, image_input)
        else:
            raise ValueError("image_input must be a URL string, local path string, or numpy ndarray image.")

        public_url = None

        # Attempt 1: Catbox.moe
        try:
            with open(temp_file_path, "rb") as f:
                res = requests.post(
                    "https://catbox.moe/user/api.php",
                    data={"reqtype": "fileupload"},
                    files={"fileToUpload": f},
                    timeout=12
                )
                if res.status_code == 200 and res.text.strip().startswith("http"):
                    public_url = res.text.strip()
        except Exception as e:
            pass

        # Attempt 2: Litterbox (fallback if Catbox fails)
        if not public_url:
            try:
                with open(temp_file_path, "rb") as f:
                    res = requests.post(
                        "https://litterbox.catbox.moe/resources/internals/api.php",
                        data={"reqtype": "fileupload", "time": "1h"},
                        files={"fileToUpload": f},
                        timeout=12
                    )
                    if res.status_code == 200 and res.text.strip().startswith("http"):
                        public_url = res.text.strip()
            except Exception as e:
                pass

        # Clean up temporary crop file if created
        if isinstance(image_input, np.ndarray) and temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass

        if not public_url:
            raise RuntimeError("Failed to upload local image to a public URL for SerpApi Google Lens processing.")

        return public_url

    def search(self, image_input) -> Dict[str, Any]:
        """
        Execute Google Lens SerpApi search for the given image input.
        Returns parsed search results including visual matches and exact matches.
        """
        public_url = self.upload_image_to_public_url(image_input)
        
        params = {
            "engine": "google_lens",
            "url": public_url,
            "api_key": self.api_key
        }

        response = requests.get("https://serpapi.com/search.json", params=params, timeout=25)
        if response.status_code != 200:
            raise RuntimeError(f"SerpApi HTTP Error {response.status_code}: {response.text}")

        data = response.json()
        if "error" in data:
            raise RuntimeError(f"SerpApi returned error: {data['error']}")

        raw_visual_matches = data.get("visual_matches", [])
        raw_exact_matches = data.get("exact_matches", []) + data.get("organic_results", [])

        visual_matches = []
        for i, match in enumerate(raw_visual_matches):
            title = match.get("title", f"Visual Match #{i+1}")
            link = match.get("link", "")
            image_url = match.get("image", match.get("thumbnail", ""))
            thumbnail_url = match.get("thumbnail", image_url)
            source = match.get("source", "Web Source")

            if image_url or link:
                visual_matches.append({
                    "position": match.get("position", i + 1),
                    "title": title,
                    "link": link,
                    "image": image_url,
                    "thumbnail": thumbnail_url,
                    "source": source,
                    "is_exact": False
                })

        exact_matches = []
        for i, match in enumerate(raw_exact_matches):
            title = match.get("title", f"Exact Match #{i+1}")
            link = match.get("link", "")
            image_url = match.get("image", match.get("thumbnail", ""))
            thumbnail_url = match.get("thumbnail", image_url)
            source = match.get("source", "Web Source")

            if image_url or link:
                exact_matches.append({
                    "position": match.get("position", i + 1),
                    "title": title,
                    "link": link,
                    "image": image_url,
                    "thumbnail": thumbnail_url,
                    "source": source,
                    "is_exact": True
                })

        all_matches = exact_matches + visual_matches

        return {
            "public_image_url": public_url,
            "search_metadata": data.get("search_metadata", {}),
            "visual_matches_count": len(visual_matches),
            "exact_matches_count": len(exact_matches),
            "total_matches": len(all_matches),
            "matches": all_matches
        }
