import os
import sys
import glob
import argparse

# Ensure stdout and stderr handle utf-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Try importing Rich Progress; provide context manager fallback if not installed
try:
    from rich.progress import Progress, SpinnerColumn, TextColumn
    HAS_RICH_PROGRESS = True
except ImportError:
    HAS_RICH_PROGRESS = False

class DummyProgress:
    """Fallback progress manager when Rich is not installed."""
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    def add_task(self, description: str, total=None):
        print(f"--> {description}")
        return 1

# Ensure FaceSearchX directory is in python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from face import FaceDetector, FaceVerifier
from search import GoogleLensSearcher, CandidateDownloader
from evidence import EvidenceFingerprinter
from utils import print_banner, print_message, print_step, print_matches_table, print_evidence_card

try:
    from blockchain.eth_client import EthClient
    from evidence.verifier import BlockchainVerifier
    HAS_BLOCKCHAIN = True
except ImportError:
    HAS_BLOCKCHAIN = False

RESOURCES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Resources"))
DEFAULT_SERPAPI_KEY = "66193a82af48b33a7363ed3ae7eed9ef70fea3d0d5ae4c50353e99cf7e127383"

def get_default_resources_image() -> str:
    """Find screenshots under Resources directory."""
    if os.path.exists(RESOURCES_DIR):
        pngs = glob.glob(os.path.join(RESOURCES_DIR, "*.png"))
        jpgs = glob.glob(os.path.join(RESOURCES_DIR, "*.jpg"))
        screenshots = sorted(pngs + jpgs)
        if screenshots:
            return screenshots[0]
    return ""

def get_progress_ctx(description: str):
    """Return Rich progress context or DummyProgress fallback."""
    if HAS_RICH_PROGRESS:
        p = Progress(SpinnerColumn(), TextColumn("[cyan]{task.description}"), transient=True)
        p.add_task(description=description, total=None)
        return p
    return DummyProgress()

def run_pipeline(
    image_source: str,
    threshold: float = 0.50,
    api_key: str = DEFAULT_SERPAPI_KEY,
    max_candidates: int = 25,
    output_dir: str = "output",
    publish_blockchain: bool = False,
    session_id: str = None
):
    """Execute end-to-end FaceSearchX pipeline."""
    print_banner()

    import time, hashlib
    if not session_id:
        session_id = f"{int(time.time())}_{os.urandom(4).hex()}"

    if not image_source:
        image_source = get_default_resources_image()
        if not image_source:
            print_message("Error: No image source provided and no screenshots found under Resources directory.", "danger")
            sys.exit(1)
        print_message(f"No image specified. Defaulting to Resources screenshot: {os.path.basename(image_source)}", "warning")

    print_message(f"Target Image Source: {image_source}", "info")
    print_message(f"Session ID: {session_id}", "info")
    print_message(f"Cosine Similarity Threshold: {threshold:.2f}", "info")
    print_message(f"SerpApi Key Loaded: {api_key[:6]}...{api_key[-4:]}\n", "info")

    # Step 1: Face Detection & Vector Embedding
    print_step(1, "Input Face Detection & InsightFace 512-d Embedding")
    detector = FaceDetector()
    try:
        input_data = detector.detect_and_encode(image_source)
        print_message("+ Face detected successfully!", "success")
        print_message(f"  * Bounding Box: {input_data['bbox'].tolist()}", "info")
        print_message(f"  * Detection Score: {input_data['det_score']:.4f}", "info")
        print_message(f"  * Embedding Vector Shape: {input_data['norm_embedding'].shape}", "info")
    except Exception as e:
        print_message(f"x Face Detection Failed: {e}", "danger")
        sys.exit(1)

    # Step 2: Google Lens Reverse Search via SerpApi
    print_step(2, "Google Lens Reverse Search (SerpApi)")
    searcher = GoogleLensSearcher(api_key=api_key)
    try:
        with get_progress_ctx("Querying Google Lens SerpApi engine..."):
            search_results = searcher.search(input_data["face_crop"])

        print_message("+ Reverse image search completed!", "success")
        print_message(f"  * Public Face Crop URL: {search_results['public_image_url']}", "info")
        print_message(f"  * Visual Matches Extracted: {search_results['visual_matches_count']}", "success")
        print_message(f"  * Exact Matches Extracted: {search_results['exact_matches_count']}", "success")
        print_message(f"  * Total Candidates Discovered: {search_results['total_matches']}", "warning")
    except Exception as e:
        print_message(f"x SerpApi Search Failed: {e}", "danger")
        sys.exit(1)

    if not search_results["matches"]:
        print_message("No visual matches returned from Google Lens.", "warning")
        sys.exit(0)

    # Step 3: Download Candidate Images
    print_step(3, f"Downloading Top {min(max_candidates, len(search_results['matches']))} Candidate Images")
    candidates_dir = os.path.join(output_dir, "candidates", session_id)
    downloader = CandidateDownloader(output_dir=candidates_dir)

    with get_progress_ctx("Fetching candidate images..."):
        downloaded_candidates = downloader.download_candidates(search_results["matches"], max_candidates=max_candidates)

    print_message(f"+ Downloaded {len(downloaded_candidates)} candidate images locally.", "success")

    # Step 4 & 5: Candidate Verification & Cosine Similarity Filtering
    print_step(4, "InsightFace Verification & Cosine Similarity Evaluation")
    verifier = FaceVerifier(detector=detector)
    verified_matches = []
    target_emb = input_data["norm_embedding"]

    with get_progress_ctx("Evaluating cosine similarity..."):
        for cand in downloaded_candidates:
            res = verifier.verify_candidate(target_emb, cand["local_path"], threshold=threshold)
            if res["is_match"]:
                match_item = dict(cand)
                match_item["similarity"] = res["similarity"]
                match_item["similarity_pct"] = res["similarity_pct"]
                match_item["det_score"] = res["det_score"]
                verified_matches.append(match_item)

    # Sort verified matches by cosine similarity score descending
    verified_matches.sort(key=lambda x: x["similarity"], reverse=True)
    for rank, m in enumerate(verified_matches, start=1):
        m["rank"] = rank

    print_message("+ Face Verification Complete!", "success")
    print_message(f"  * Threshold Applied: {threshold:.2f}", "warning")
    print_message(f"  * Verified Actual Face Matches: {len(verified_matches)} out of {len(downloaded_candidates)} candidates", "success")

    # Step 6: Print Source & Image URLs
    print_step(5, "Source URLs + Image URLs of Verified Matches")
    if verified_matches:
        print_matches_table(verified_matches)
    else:
        print_message("No candidate images met the similarity threshold criteria.", "warning")

    # Step 7: Generate Evidence Fingerprint
    print_step(6, "Evidence Fingerprint Generation")
    evidence_dir = os.path.join(output_dir, "evidence")
    fingerprinter = EvidenceFingerprinter(output_dir=evidence_dir)

    evidence_record = fingerprinter.create_evidence_record(
        input_source=image_source,
        input_face_data=input_data,
        verified_matches=verified_matches,
        threshold_used=threshold,
        session_id=session_id
    )

    print_evidence_card(evidence_record)
    
    # Step 7: Blockchain Publication
    if publish_blockchain:
        print_step(7, "Blockchain Evidence Publication")
        if not HAS_BLOCKCHAIN:
            print_message("Blockchain modules are not installed/available.", "danger")
        else:
            try:
                eth_client = EthClient()
                if not eth_client.contract_address:
                    print_message("No contract address found. Deploying new EvidenceRegistry...", "warning")
                    eth_client.deploy_contract()
                    
                payload = evidence_record["payload"]
                with get_progress_ctx("Publishing to Ethereum/Anvil..."):
                    tx_hash = eth_client.publish_evidence(
                        evidence_id=evidence_record["evidence_hash"],
                        evidence_hash=evidence_record["evidence_hash"],
                        target_url=payload.get("input_source", ""),
                        input_file_hash=payload.get("input_file_sha256", "")
                    )
                if tx_hash:
                    print_message(f"+ Evidence published to blockchain!", "success")
                    print_message(f"  * Transaction Hash: {tx_hash}", "highlight")
                    print_message(f"  * Contract Address: {eth_client.contract_address}", "highlight")
                else:
                    print_message("+ Evidence already existed on the blockchain.", "info")
            except Exception as e:
                print_message(f"x Blockchain Publication Failed: {e}", "danger")

    print_message("Pipeline execution completed successfully!\n", "success")
    
    return {
        "session_id": session_id,
        "verified_matches": verified_matches,
        "evidence_record": evidence_record
    }

def verify_pipeline(evidence_file: str):
    print_banner()
    print_step(1, f"Verifying Evidence File: {evidence_file}")
    if not HAS_BLOCKCHAIN:
        print_message("Blockchain modules are not installed/available.", "danger")
        sys.exit(1)
        
    try:
        verifier = BlockchainVerifier()
        is_valid, message, details = verifier.verify_evidence_file(evidence_file)
        if is_valid:
            print_message(message, "success")
            for k, v in details.items():
                print_message(f"  * {k}: {v}", "info")
        else:
            print_message(message, "danger")
            for k, v in details.items():
                print_message(f"  * {k}: {v}", "warning")
    except Exception as e:
        print_message(f"x Verification Failed: {e}", "danger")

def main():
    parser = argparse.ArgumentParser(description="FaceSearchX - Visual Face Search & Evidence Pipeline")
    parser.add_argument("--image", "-i", type=str, default="", help="Path to input face image or remote URL (default: searches Resources screenshots)")
    parser.add_argument("--threshold", "-t", type=float, default=0.50, help="Cosine similarity threshold for face verification (default: 0.50)")
    parser.add_argument("--api-key", "-k", type=str, default=DEFAULT_SERPAPI_KEY, help="SerpApi API Key")
    parser.add_argument("--max-candidates", "-m", type=int, default=25, help="Maximum candidates to download and verify (default: 25)")
    parser.add_argument("--output-dir", "-o", type=str, default="output", help="Output directory for candidates and evidence")
    parser.add_argument("--publish", action="store_true", help="Publish evidence fingerprint to the blockchain")
    parser.add_argument("--verify-evidence", type=str, help="Verify a generated JSON evidence file for tampering against the blockchain")

    args = parser.parse_args()
    
    if args.verify_evidence:
        verify_pipeline(args.verify_evidence)
    else:
        run_pipeline(
            image_source=args.image,
            threshold=args.threshold,
            api_key=args.api_key,
            max_candidates=args.max_candidates,
            output_dir=args.output_dir,
            publish_blockchain=args.publish
        )

if __name__ == "__main__":
    main()
