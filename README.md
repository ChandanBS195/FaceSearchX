# 🕵️ FaceSearchX

FaceSearchX is a powerful, enterprise-grade application for visual face discovery, automated web candidate extraction, facial embedding verification, and cryptographic blockchain evidence logging, made by **Chandan**. 

It leverages **Google Lens** to scour the web for matches, uses **InsightFace** to locally verify faces via cosine similarity, and securely records findings to a local **Ethereum** blockchain network for immutable tamper-proof evidence.

---

## ✨ What It Does

1. **Precision Web Search:** Temporarily hosts your target image to query Google Lens via SerpApi, scraping exact and visual matches across the web.
2. **Local AI Verification:** Downloads all candidate images from the web and uses the InsightFace `buffalo_l` model to extract 512-dimensional face embeddings. It strictly filters out false positives by running a cosine similarity check against your target face.
3. **Smart Categorization:** Automatically groups visual matches into Social Media (X/Twitter, Pinterest, Instagram, etc.) and General Web sources.
4. **Cryptographic Fingerprinting:** Generates a canonical SHA-256 fingerprint encompassing search metadata, verified matches, detection scores, and source URLs.
5. **Blockchain Evidence Registry:** Publishes the evidence hash and metadata immutably onto a smart contract.
6. **On-Chain Verification:** Cryptographically proves that an evidence JSON file has not been tampered with since its creation by verifying its payload against the blockchain record.

---

## 🛠️ The Tech Stack

- **Core AI:** InsightFace (512-d embeddings), OpenCV, ONNXRuntime
- **Search Engine:** Google Lens via SerpApi
- **Web UI:** Streamlit (`web.py`)
- **CLI Interface:** Rich library for beautiful terminal output (`cli.py`)
- **Blockchain:** Ethereum / Solidity / Web3.py
- **Local Network Node:** [Foundry Anvil](https://book.getfoundry.sh/anvil/)

---

## 🚀 How to Run It

### Prerequisites
1. **Python 3.9+**
2. **Foundry (Anvil):** You must have [Foundry installed](https://book.getfoundry.sh/getting-started/installation) to run the local blockchain node.
3. **SerpApi Key:** Needed to query Google Lens. Create a `.env` file based on `.env.example` and set `SERPAPI_KEY=your_key`.

### Installation
```bash
# Clone the repository and navigate into it
cd FaceSearchX

# Install the Python dependencies
pip install -r requirements.txt
```

### Option A: The Streamlit Web UI (Recommended)
FaceSearchX comes with a fully-featured, dynamic web interface.

1. **Start the local blockchain node** in a separate terminal:
   ```bash
   anvil
   ```
2. **Launch the Web UI:**
   ```bash
   python -m streamlit run web.py
   ```
3. Open your browser to `http://localhost:8501`. From the sidebar, you can verify your Anvil node connection, upload or paste an image directly into the app, adjust similarity thresholds, and execute the search!

### Option B: The CLI (Command-Line Interface)
If you prefer running automations or working in the terminal, the CLI provides a rich UI.

**1. Execute a Search & Publish Evidence:**
```bash
python cli.py --image "path/to/face.jpg" --publish
```

**2. Customize Thresholds & Candidates:**
```bash
python cli.py --image "path/to/face.jpg" --threshold 0.55 --max-candidates 30
```

**3. Verify an Evidence JSON File against the Blockchain:**
```bash
python cli.py --verify-evidence "output/evidence/evidence_1788766579_1207021d.json"
```

---

## 🔗 Blockchain Integration details

FaceSearchX uses a local Ethereum network powered by **Foundry's Anvil** running on `http://127.0.0.1:8545`. 
- An internal Smart Contract (`EvidenceRegistry.sol`) is used to store SHA-256 evidence hashes.
- If the app detects Anvil is running but the contract hasn't been deployed yet (e.g., if you restarted Anvil and the memory was wiped), the system will **automatically auto-deploy** a fresh contract for you during the next search.
- When an evidence file is verified, the system computes the local hash of the JSON payload and cross-checks it against the state held in the `EvidenceRegistry` contract to detect any tampering.

---

## ⚠️ Known Limitations

- **Temporary Hosting Reliance:** To query Google Lens with a local image, the image is temporarily uploaded to free anonymous file-hosting services (Catbox/Litterbox). These services can occasionally face downtime or rate limits.
- **Node Volatility:** Because Anvil is an in-memory local blockchain, restarting the `anvil` process wipes all previously published evidence. Real-world deployments should point the RPC URL to a persistent testnet (like Sepolia) or Ethereum Mainnet.
- **Hardware Requirements:** InsightFace model inference runs on the CPU by default unless ONNXRuntime-GPU is configured. While CPU inference is supported, scanning hundreds of web candidates may take a minute or two on older processors.
- **SerpApi Quotas:** The app relies on SerpApi for Google Lens results. You must have sufficient credits on your SerpApi account to fetch candidate URLs.