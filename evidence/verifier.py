import json
import hashlib
import os
from typing import Dict, Any, Tuple
from blockchain.eth_client import EthClient

class BlockchainVerifier:
    def __init__(self, eth_client: EthClient = None):
        """Initialize with an EthClient. If None, it will try to create one."""
        self.eth_client = eth_client or EthClient()

    @staticmethod
    def calculate_local_hash(evidence_payload: Dict[str, Any]) -> str:
        """Calculates the SHA-256 hash of the evidence payload."""
        canonical_json_str = json.dumps(evidence_payload, sort_keys=True)
        return hashlib.sha256(canonical_json_str.encode("utf-8")).hexdigest()

    def verify_evidence_file(self, file_path: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Verifies a local evidence JSON file against the blockchain.
        Returns (is_valid, message, details).
        """
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}", {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            return False, "Invalid JSON file format.", {}

        claimed_hash = data.get("evidence_hash")
        payload = data.get("payload")

        if not claimed_hash or not payload:
            return False, "Invalid evidence format. Missing evidence_hash or payload.", {}

        # 1. Local Tamper Check
        computed_local_hash = self.calculate_local_hash(payload)
        if computed_local_hash != claimed_hash:
            return False, "LOCAL TAMPERING DETECTED: The payload hash does not match the evidence_hash in the file.", {
                "claimed_hash": claimed_hash,
                "computed_hash": computed_local_hash
            }

        # 2. Blockchain Verification
        on_chain_record = self.eth_client.get_evidence(claimed_hash)
        if not on_chain_record:
            return False, "ON-CHAIN RECORD NOT FOUND: This evidence hash is not registered on the blockchain.", {
                "claimed_hash": claimed_hash
            }

        on_chain_hash = on_chain_record["evidenceHash"]
        if on_chain_hash != claimed_hash:
            return False, "BLOCKCHAIN TAMPERING DETECTED: The on-chain hash does not match the local hash.", {
                "claimed_hash": claimed_hash,
                "on_chain_hash": on_chain_hash
            }

        return True, "VERIFIED ✓: The evidence is intact and successfully matched with the immutable blockchain record.", {
            "evidence_hash": claimed_hash,
            "on_chain_timestamp": on_chain_record["timestamp"],
            "publisher": on_chain_record["publisher"],
            "contract_address": self.eth_client.contract_address
        }
