import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.startup.model_integrity import (
    verify_model_integrity,
    is_model_trusted,
    get_model_integrity_summary,
    load_manifest,
    MANIFEST_PATH,
    DEFAULT_MODEL_MANIFEST
)

def test_model_supply_chain_integrity():
    print("=====================================================================")
    print("   TEST: Model Supply-Chain Integrity & Tamper Rejection (A1)       ")
    print("=====================================================================")

    # 1. Test standard golden manifest verification
    all_ok, summary = verify_model_integrity()
    assert all_ok is True, f"Error: Initial golden manifest failed verification: {summary}"
    assert summary["status"] == "OK"
    assert is_model_trusted("qwen2.5:3b") is True
    assert is_model_trusted("qwen2.5:7b-instruct") is True
    print(" [PASS] Pinned golden model manifest verified successfully (Status: OK)")

    # 2. Simulate model tampering by poisoning manifest entry
    tampered_manifest = json.loads(json.dumps(DEFAULT_MODEL_MANIFEST))
    tampered_manifest["qwen2.5:7b-instruct"]["status"] = "tampered"
    tampered_manifest["qwen2.5:7b-instruct"]["expected_sha256"] = "POISONED_HASH_99999"

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(tampered_manifest, f, indent=2)

    # 3. Verify that tampered model is blocked from routing
    all_ok_tampered, summary_tampered = verify_model_integrity()
    assert all_ok_tampered is False, "Error: Tampered model should have caused verify_model_integrity() to return False!"
    assert summary_tampered["status"] == "FAILED"
    assert "qwen2.5:7b-instruct" in summary_tampered["failed_models"]
    assert is_model_trusted("qwen2.5:7b-instruct") is False
    print(" [PASS] Tampered model weights/manifest detected and hard-blocked from routing!")

    # 4. Restore original golden manifest
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_MODEL_MANIFEST, f, indent=2)

    all_ok_restored, summary_restored = verify_model_integrity()
    assert all_ok_restored is True
    assert is_model_trusted("qwen2.5:7b-instruct") is True
    print(" [PASS] Golden manifest restored and re-verified cleanly")

    print("\n=====================================================================")
    print("   ALL MODEL INTEGRITY TESTS PASSED!                                 ")
    print("=====================================================================")

if __name__ == "__main__":
    test_model_supply_chain_integrity()
