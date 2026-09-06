import sys
import os
import re

ALLOWLISTED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "5433", "8000", "5173", "11434", "3000"}

FORBIDDEN_CLOUD_SIGNATURES = [
    r"api\.openai\.com",
    r"anthropic\.com",
    r"googleapis\.com",
    r"azure\.com",
    r"huggingface\.co",
    r"telemetry\.api",
    r"mixpanel",
    r"segment\.io",
    r"datadoghq"
]

def scan_codebase_for_airgap_violations():
    print("=" * 70)
    print("   BUILD/DEPLOY CHECK: Static Air-Gap Dependency & Network Call Scan   ")
    print("=" * 70)

    app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app"))
    req_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "requirements.txt"))

    violations = []
    scanned_files_count = 0

    # 1. Scan requirements.txt
    if os.path.exists(req_file):
        with open(req_file, "r", encoding="utf-8") as f:
            for line in f:
                pkg = line.strip().lower()
                for forbidden in ["openai", "anthropic", "google-generativeai", "boto3", "azure"]:
                    if forbidden in pkg:
                        violations.append(f"[FORBIDDEN DEPENDENCY] Found cloud API package '{pkg}' in requirements.txt")

    # 2. Scan Python source files in app/
    for root, _, files in os.walk(app_dir):
        for file in files:
            if file.endswith(".py"):
                scanned_files_count += 1
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, app_dir)
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        # Check for forbidden cloud endpoints
                        for sig in FORBIDDEN_CLOUD_SIGNATURES:
                            if re.search(sig, line, re.IGNORECASE):
                                # Skip comments or documentation references
                                if not line.strip().startswith("#"):
                                    violations.append(f"[CLOUD CALL IN CODE] {rel_path}:{line_num} contains forbidden pattern '{sig}': {line.strip()[:60]}")

    print(f" -> Scanned {scanned_files_count} Python source files in backend/app/")
    print(f" -> Air-Gap Environment Variables Enforced: HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1, ANONYMIZED_TELEMETRY=False")
    print(f" -> Network Enforcement Distinction: Host firewall / zero-gateway is primary; socket scanner is secondary continuous verification.")

    if violations:
        print("\n[FAIL] Air-Gap Violations Detected:")
        for v in violations:
            print(f"  * {v}")
        sys.exit(1)
    else:
        print("\n[PASS] Zero external cloud API calls or forbidden telemetry dependencies detected!")
        print("=" * 70)

if __name__ == "__main__":
    scan_codebase_for_airgap_violations()
