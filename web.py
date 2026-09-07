import streamlit as st
import os
import sys
import time
import subprocess
from web3 import Web3
from PIL import Image, ImageOps

# Ensure FaceSearchX is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from cli import run_pipeline, DEFAULT_SERPAPI_KEY

st.set_page_config(page_title="FaceSearchX", page_icon="🕵️", layout="wide")

def get_grid_image(img_path):
    """Format image to 3:4 ratio using transparent padding so it aligns nicely in a grid without stretching."""
    try:
        img = Image.open(img_path).convert("RGBA")
        # Scale to fit inside a 600x800 (3:4) bounding box with transparent padding
        return ImageOps.pad(img, (600, 800), color=(0, 0, 0, 0))
    except Exception:
        return img_path

def check_anvil_node():
    w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
    if not w3.is_connected():
        return False, None
    try:
        from blockchain.eth_client import EthClient
        client = EthClient()
        return True, client.contract_address
    except Exception:
        return True, None

def start_anvil_node():
    # Use subprocess.Popen to start anvil in the background
    subprocess.Popen(["anvil"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2) # Wait for it to spin up

st.title("🕵️ FaceSearchX - Visual Face Discovery")
st.markdown("Visual Face Discovery & Evidence Verification Pipeline Made By Chandan")

# Sidebar for Node Status and Settings
with st.sidebar:
    st.header("Node Status")
    is_running, contract_address = check_anvil_node()
    if is_running:
        st.success("🟢 Anvil Node Connected (127.0.0.1:8545)")
        if st.button("🛑 Stop Anvil Node", type="primary"):
            subprocess.run(["taskkill", "/F", "/IM", "anvil.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)
            st.rerun()
            
        if contract_address:
            st.info(f"**Contract Address**:\n`{contract_address}`")
        else:
            st.warning("Contract not deployed yet.")
    else:
        st.error("🔴 Anvil Node Offline")
        if st.button("🟢 Start Anvil Node"):
            start_anvil_node()
            st.rerun()

    st.header("Settings")
    threshold = st.slider("Similarity Threshold", 0.1, 1.0, 0.50, 0.05)
    max_candidates = st.number_input("Max Candidates", 1, 100, 25)
    publish_blockchain = st.checkbox("Publish Evidence to Blockchain", value=True)

st.header("1. Input Image")

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

col1, col2 = st.columns([1, 1])

with col1:
    uploaded_file = st.file_uploader(
        "Upload or Paste Image (Click here & press Ctrl+V)", 
        type=["jpg", "jpeg", "png"], 
        key=f"uploader_{st.session_state.uploader_key}"
    )

image_path = ""

if uploaded_file is not None:
    # Hide the file uploader once an image is uploaded
    st.markdown("""
        <style>
            [data-testid="stFileUploader"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Save uploaded file to a temp directory
    os.makedirs("temp_uploads", exist_ok=True)
    image_path = os.path.join("temp_uploads", uploaded_file.name)
    with open(image_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    with col1:
        st.image(Image.open(image_path), width=250)
        if st.button("🗑️ Remove / Replace Image"):
            st.session_state.uploader_key += 1
            st.rerun()

if st.button("Execute Search", type="primary"):
    if not image_path:
        st.warning("Please upload an image to start.")
    else:
        with st.spinner("Running FaceSearchX pipeline... This may take a minute."):
            try:
                results = run_pipeline(
                    image_source=image_path,
                    threshold=threshold,
                    api_key=DEFAULT_SERPAPI_KEY,
                    max_candidates=max_candidates,
                    publish_blockchain=publish_blockchain
                )
                if results:
                    st.session_state["results"] = results
                    st.success("Pipeline execution completed!")
            except SystemExit as e:
                if e.code == 0:
                    st.warning("Search finished but returned no visual matches.")
                else:
                    st.error("Pipeline encountered an error and exited.")
            except Exception as e:
                st.error(f"Error executing pipeline: {e}")

if "results" in st.session_state and st.session_state["results"]:
    from evidence.fingerprint import classify_social_domain
    results = st.session_state["results"]
    session_id = results.get("session_id", "Unknown")
    verified_matches = results.get("verified_matches", [])
    evidence_record = results.get("evidence_record", {})
    payload = evidence_record.get("payload", {})
    
    # Enrich verified matches with classification
    for match in verified_matches:
        platform, is_social = classify_social_domain(match.get("source"), match.get("link"))
        match["platform"] = platform
        match["is_social_media"] = is_social
    
    st.header("2. Evidence Summary")
    ev_path = evidence_record.get('saved_filepath', '')
    
    sm_summary = payload.get("social_media_summary", {})
    platforms_detected = sm_summary.get("platforms_detected", {})
    plat_str_list = [f"{plat} ({cnt})" for plat, cnt in platforms_detected.items()]
    plat_str = ", ".join(plat_str_list) if plat_str_list else "None"
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Evidence Fingerprint SHA-256:**\n`{evidence_record.get('evidence_hash')}`")
        st.markdown(f"**UTC Timestamp:** `{payload.get('timestamp_utc')}`")
        st.markdown(f"**Input Source:** `{payload.get('input_source')}`")
        st.markdown(f"**Detection Score:** `{payload.get('face_detection', {}).get('det_score', 0):.4f}`")
    with col2:
        st.markdown(f"**Verified Matches:** `{payload.get('verified_matches_count')}`")
        st.markdown(f"**Social Media Footprint:** `{sm_summary.get('total_social_matches', 0)} match(es) [{plat_str}]`")
        st.markdown(f"**General Web Matches:** `{sm_summary.get('total_general_web_matches', 0)}`")
        st.markdown(f"**Evidence File:** `{ev_path}`")

    with st.expander("View Raw Evidence JSON"):
        st.json(evidence_record)
    
    st.header("3. Verified Candidates Gallery")
    if verified_matches:
        cols = st.columns(4)
        for idx, match in enumerate(verified_matches):
            with cols[idx % 4]:
                local_path = match.get("local_path")
                if local_path and os.path.exists(local_path):
                    st.image(get_grid_image(local_path), caption=f"Score: {match.get('similarity_pct', 0.0):.1f}%", use_container_width=True)
                    st.markdown(f"**Source**: {match.get('source')}")
                    st.markdown(f"[View Full Image]({match.get('image')})")
    else:
        st.write("No verified candidates met the threshold.")
        
    st.header("4. Social Media Matches")
    social_matches = [m for m in verified_matches if m.get("is_social_media")]
    if social_matches:
        cols = st.columns(4)
        for idx, match in enumerate(social_matches):
            with cols[idx % 4]:
                local_path = match.get("local_path")
                if local_path and os.path.exists(local_path):
                    st.image(get_grid_image(local_path), caption=f"Score: {match.get('similarity_pct', 0.0):.1f}%", use_container_width=True)
                    st.markdown(f"**Platform**: {match.get('platform')}")
                    st.markdown(f"[View Page]({match.get('link')})")
    else:
        st.write("No social media matches found in this session.")
        
    st.header("5. General Web & News Matches")
    web_matches = [m for m in verified_matches if not m.get("is_social_media")]
    if web_matches:
        cols = st.columns(4)
        for idx, match in enumerate(web_matches):
            with cols[idx % 4]:
                local_path = match.get("local_path")
                if local_path and os.path.exists(local_path):
                    st.image(get_grid_image(local_path), caption=f"Score: {match.get('similarity_pct', 0.0):.1f}%", use_container_width=True)
                    st.markdown(f"**Domain**: {match.get('source')}")
                    st.markdown(f"[View Page]({match.get('link')})")
    else:
        st.write("No general web matches found in this session.")

# Append to sidebar after results are processed so it's guaranteed to show
if "results" in st.session_state and st.session_state["results"]:
    with st.sidebar:
        st.header("Current Session")
        st.code(st.session_state["results"].get("session_id", "Unknown"))
        
        ev_path = st.session_state["results"].get("evidence_record", {}).get("saved_filepath", "")
        if ev_path and os.path.exists(ev_path):
            if st.button("Verify Evidence on Blockchain"):
                with st.spinner("Verifying evidence on-chain..."):
                    from evidence.verifier import BlockchainVerifier
                    try:
                        verifier = BlockchainVerifier()
                        is_valid, message, details = verifier.verify_evidence_file(ev_path)
                        if is_valid:
                            st.success(message)
                            for k, v in details.items():
                                st.info(f"**{k}**: {v}")
                        else:
                            st.error(message)
                            for k, v in details.items():
                                st.warning(f"**{k}**: {v}")
                    except Exception as e:
                        st.error(f"Verification Error: {e}")
