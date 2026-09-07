// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract EvidenceRegistry {
    struct Evidence {
        string evidenceHash; // The overall SHA-256 hash of the evidence JSON payload
        string targetImageUrl; // The URL/source of the target image
        string inputFileSha256; // The SHA-256 of the original local file (if available)
        uint256 timestamp; // UNIX timestamp when published
        address publisher; // Address that published the evidence
        bool exists; // Flag to check if it exists
    }

    // Mapping from a unique evidence ID (which could be the evidenceHash itself) to the Evidence struct
    mapping(string => Evidence) public evidences;

    event EvidencePublished(
        string indexed evidenceId,
        string evidenceHash,
        address indexed publisher,
        uint256 timestamp
    );

    /**
     * @dev Publish a new evidence record to the blockchain.
     * @param _evidenceId A unique identifier for the evidence (e.g., the JSON's SHA-256 hash).
     * @param _evidenceHash The SHA-256 hash of the evidence payload.
     * @param _targetImageUrl The source URL or local path of the target image.
     * @param _inputFileSha256 The SHA-256 hash of the target image file.
     */
    function publishEvidence(
        string memory _evidenceId,
        string memory _evidenceHash,
        string memory _targetImageUrl,
        string memory _inputFileSha256
    ) public {
        require(!evidences[_evidenceId].exists, "Evidence ID already exists");

        evidences[_evidenceId] = Evidence({
            evidenceHash: _evidenceHash,
            targetImageUrl: _targetImageUrl,
            inputFileSha256: _inputFileSha256,
            timestamp: block.timestamp,
            publisher: msg.sender,
            exists: true
        });

        emit EvidencePublished(_evidenceId, _evidenceHash, msg.sender, block.timestamp);
    }

    /**
     * @dev Retrieves an evidence record by its ID.
     */
    function getEvidence(string memory _evidenceId) public view returns (
        string memory evidenceHash,
        string memory targetImageUrl,
        string memory inputFileSha256,
        uint256 timestamp,
        address publisher
    ) {
        require(evidences[_evidenceId].exists, "Evidence ID not found");
        Evidence memory e = evidences[_evidenceId];
        return (e.evidenceHash, e.targetImageUrl, e.inputFileSha256, e.timestamp, e.publisher);
    }
}
