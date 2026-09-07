import os
import json
import time
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

SOCIAL_MEDIA_DOMAINS = {
    "instagram.com": "Instagram",
    "instagr.am": "Instagram",
    "facebook.com": "Facebook",
    "fb.com": "Facebook",
    "fb.watch": "Facebook",
    "x.com": "X (Twitter)",
    "twitter.com": "X (Twitter)",
    "t.co": "X (Twitter)",
    "linkedin.com": "LinkedIn",
    "youtube.com": "YouTube",
    "youtu.be": "YouTube",
    "tiktok.com": "TikTok",
    "pinterest.com": "Pinterest",
    "pin.it": "Pinterest",
    "reddit.com": "Reddit",
    "threads.net": "Threads",
    "telegram.org": "Telegram",
    "t.me": "Telegram",
    "quora.com": "Quora",
    "medium.com": "Medium",
    "snapchat.com": "Snapchat",
    "whatsapp.com": "WhatsApp",
    "wa.me": "WhatsApp",
    "tumblr.com": "Tumblr",
    "flickr.com": "Flickr",
    "vk.com": "VK",
    "discord.com": "Discord",
    "discord.gg": "Discord",
    "twitch.tv": "Twitch",
    "bsky.app": "Bluesky"
}

def classify_social_domain(domain_str: Optional[str], url_str: Optional[str]) -> tuple[str, bool]:
    """Classify domain as social media platform or general web."""
    from urllib.parse import urlparse
    
    d_lower = (domain_str or "").lower()
    u_lower = (url_str or "").lower()
    
    # Extract hostname from URL to avoid false substring matches (like 't.co' in 'pinterest.com')
    hostname = ""
    if u_lower:
        try:
            parsed = urlparse(u_lower)
            if not parsed.scheme:
                parsed = urlparse("http://" + u_lower)
            hostname = parsed.hostname or ""
        except Exception:
            pass

    for pattern, name in SOCIAL_MEDIA_DOMAINS.items():
        if hostname == pattern or hostname.endswith("." + pattern):
            return name, True
        if d_lower == pattern or d_lower.endswith("." + pattern):
            return name, True
            
    return domain_str or "Web Domain", False

class EvidenceFingerprinter:
    def __init__(self, output_dir: str = "output/evidence"):
        """Initialize Evidence Fingerprinter and output directory."""
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    @staticmethod
    def calculate_file_sha256(filepath: str) -> Optional[str]:
        """Compute SHA-256 hash of a local file."""
        if not os.path.exists(filepath):
            return None
        sha = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                sha.update(chunk)
        return sha.hexdigest()

    def create_evidence_record(
        self,
        input_source: str,
        input_face_data: Dict[str, Any],
        verified_matches: List[Dict[str, Any]],
        threshold_used: float,
        api_engine: str = "google_lens",
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        Build a canonical evidence record and generate a SHA-256 fingerprint hash.
        Saves the evidence record JSON to the output directory.
        """
        timestamp_iso = datetime.now(timezone.utc).isoformat()
        timestamp_unix = int(time.time())

        # Compute hash of input image if local
        input_file_hash = None
        if os.path.exists(input_source):
            input_file_hash = self.calculate_file_sha256(input_source)

        # Compute hash of face embedding
        emb_bytes = input_face_data["norm_embedding"].tobytes()
        embedding_sha256 = hashlib.sha256(emb_bytes).hexdigest()

        # Build clean verified match items & classify social media domains
        clean_matches = []
        social_matches_count = 0
        general_web_count = 0
        social_platforms_detected: Dict[str, int] = {}

        for m in verified_matches:
            cand_hash = None
            if m.get("local_path"):
                cand_hash = self.calculate_file_sha256(m["local_path"])

            platform_name, is_social = classify_social_domain(m.get("source"), m.get("link"))

            if is_social:
                social_matches_count += 1
                social_platforms_detected[platform_name] = social_platforms_detected.get(platform_name, 0) + 1
            else:
                general_web_count += 1

            clean_matches.append({
                "rank": m.get("rank"),
                "similarity_score": round(m.get("similarity", 0.0), 4),
                "similarity_percentage": f"{m.get('similarity_pct', 0.0):.1f}%",
                "source_title": m.get("title"),
                "source_url": m.get("link"),
                "image_url": m.get("image"),
                "source_domain": m.get("source"),
                "platform": platform_name,
                "is_social_media": is_social,
                "candidate_image_sha256": cand_hash
            })

        evidence_payload = {
            "evidence_version": "1.1",
            "timestamp_utc": timestamp_iso,
            "timestamp_unix": timestamp_unix,
            "search_engine": api_engine,
            "verification_threshold": threshold_used,
            "input_source": input_source,
            "input_file_sha256": input_file_hash,
            "face_detection": {
                "det_score": input_face_data.get("det_score"),
                "embedding_sha256": embedding_sha256,
                "bbox": input_face_data.get("bbox", []).tolist() if hasattr(input_face_data.get("bbox"), "tolist") else input_face_data.get("bbox")
            },
            "verified_matches_count": len(clean_matches),
            "social_media_summary": {
                "total_social_matches": social_matches_count,
                "total_general_web_matches": general_web_count,
                "platforms_detected": social_platforms_detected
            },
            "matches": clean_matches
        }

        # Generate canonical fingerprint hash over the payload JSON string
        canonical_json_str = json.dumps(evidence_payload, sort_keys=True)
        evidence_hash = hashlib.sha256(canonical_json_str.encode("utf-8")).hexdigest()

        evidence_record = {
            "evidence_hash": evidence_hash,
            "payload": evidence_payload
        }

        # Save to evidence file using session_id if provided
        if session_id:
            filename = f"evidence_{session_id}.json"
        else:
            filename = f"evidence_{timestamp_unix}_{evidence_hash[:8]}.json"
            
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(evidence_record, f, indent=2)

        evidence_record["saved_filepath"] = filepath
        return evidence_record
