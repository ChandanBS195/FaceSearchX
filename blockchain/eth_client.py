import os
import json
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# Load environment variables
load_dotenv()

class EthClient:
    def __init__(self, rpc_url=None, private_key=None):
        self.rpc_url = rpc_url or os.getenv("RPC_URL", "http://127.0.0.1:8545")
        self.private_key = private_key or os.getenv("PRIVATE_KEY")
        self.contract_address = os.getenv("CONTRACT_ADDRESS")
        
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        # Inject POA middleware for networks like Sepolia or Anvil
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to Ethereum node at {self.rpc_url}")
            
        if self.private_key:
            self.account = self.w3.eth.account.from_key(self.private_key)
            self.w3.eth.default_account = self.account.address
        else:
            self.account = None

        self._load_contract_interface()
        
        if self.contract_address:
            checksum_addr = self.w3.to_checksum_address(self.contract_address)
            code = self.w3.eth.get_code(checksum_addr)
            if code == b'' or code == b'\x00':
                print(f"Warning: No contract found at {self.contract_address} (did the local node restart?). It will be redeployed.")
                self.contract_address = None
                self.contract = None
            else:
                self.contract = self.w3.eth.contract(
                    address=checksum_addr,
                    abi=self.abi
                )
        else:
            self.contract = None

    def _load_contract_interface(self):
        """Loads the ABI and Bytecode from Foundry compilation output."""
        base_dir = Path(__file__).parent
        artifact_path = base_dir / "out" / "EvidenceRegistry.sol" / "EvidenceRegistry.json"
        
        if not artifact_path.exists():
            raise FileNotFoundError(f"Contract artifact not found at {artifact_path}. Did you run 'forge build'?")
            
        with open(artifact_path, "r") as f:
            data = json.load(f)
            self.abi = data["abi"]
            self.bytecode = data["bytecode"]["object"]

    def deploy_contract(self) -> str:
        """Deploys the EvidenceRegistry contract and returns its address."""
        if not self.account:
            raise ValueError("Private key is required to deploy a contract.")
            
        print("Deploying EvidenceRegistry contract...")
        contract = self.w3.eth.contract(abi=self.abi, bytecode=self.bytecode)
        
        tx = contract.constructor().build_transaction({
            "from": self.account.address,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "gasPrice": self.w3.eth.gas_price
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        print(f"Deployment transaction sent: {tx_hash.hex()}")
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        self.contract_address = tx_receipt.contractAddress
        self.contract = self.w3.eth.contract(
            address=self.contract_address,
            abi=self.abi
        )
        print(f"Contract deployed at: {self.contract_address}")
        
        # Save to .env automatically
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            with open(env_path, "r") as f:
                lines = f.readlines()
            with open(env_path, "w") as f:
                for line in lines:
                    if line.startswith("CONTRACT_ADDRESS="):
                        f.write(f"CONTRACT_ADDRESS={self.contract_address}\n")
                    else:
                        f.write(line)
                        
        return self.contract_address

    def publish_evidence(self, evidence_id: str, evidence_hash: str, target_url: str, input_file_hash: str) -> str:
        """Publishes an evidence record to the blockchain."""
        if not self.contract:
            raise ValueError("Contract not deployed or address not set.")
        if not self.account:
            raise ValueError("Private key is required to send transactions.")

        # Ensure strings aren't None
        target_url = target_url or ""
        input_file_hash = input_file_hash or ""

        # Check if already exists to avoid revert
        try:
            existing = self.contract.functions.getEvidence(evidence_id).call()
            # If we reach here, it exists (because getEvidence reverts if not found)
            print(f"Evidence ID {evidence_id} is already published on-chain.")
            return None
        except Exception:
            pass # Expected if it doesn't exist

        tx = self.contract.functions.publishEvidence(
            evidence_id,
            evidence_hash,
            target_url,
            input_file_hash
        ).build_transaction({
            "from": self.account.address,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "gasPrice": self.w3.eth.gas_price
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return tx_hash.hex()

    def get_evidence(self, evidence_id: str):
        """Retrieves an evidence record from the blockchain."""
        if not self.contract:
            raise ValueError("Contract not deployed or address not set.")
            
        try:
            result = self.contract.functions.getEvidence(evidence_id).call()
            return {
                "evidenceHash": result[0],
                "targetImageUrl": result[1],
                "inputFileSha256": result[2],
                "timestamp": result[3],
                "publisher": result[4]
            }
        except Exception as e:
            # Contract reverts with "Evidence ID not found" if it doesn't exist
            return None
