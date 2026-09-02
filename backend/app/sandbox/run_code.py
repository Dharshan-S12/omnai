import sys
import os
import subprocess
import tempfile
from typing import Dict, Any

def run_code(code: str, timeout_seconds: int = 15) -> Dict[str, Any]:
    """
    Execute Python code in an isolated temporary directory using a subprocess with a strict execution timeout.
    
    Security & Isolation Note:
    - Code runs in an ephemeral temporary directory isolated from the repository root.
    - Standard environment variables are sanitized to prevent accidental credential leakage.
    - Note on Windows network isolation: Windows subprocesses do not natively support Linux-style network namespaces
      without containerization (Docker/Hyper-V/AppContainer). For this on-prem prototype, subprocess execution is isolated
      to the temp directory with restricted environment; production air-gapped isolation is enforced via network policies.
    """
    if not code or not code.strip():
        return {
            "stdout": "",
            "stderr": "No code provided to execute",
            "exit_code": 1,
            "timed_out": False
        }

    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = os.path.join(temp_dir, "solution.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)

        # Sanitized environment: only include necessary runtime vars
        clean_env = {
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
            "WINDIR": os.environ.get("WINDIR", "C:\\Windows"),
            "PATH": os.environ.get("PATH", ""),
            "TEMP": temp_dir,
            "TMP": temp_dir,
            "PYTHONUNBUFFERED": "1",
            "PYTHONIOENCODING": "utf-8",
        }

        try:
            process = subprocess.run(
                [sys.executable, "-u", script_path],
                cwd=temp_dir,
                env=clean_env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )
            return {
                "stdout": process.stdout,
                "stderr": process.stderr,
                "exit_code": process.returncode,
                "timed_out": False
            }
        except subprocess.TimeoutExpired as te:
            stdout = te.stdout if isinstance(te.stdout, str) else (te.stdout.decode("utf-8", errors="replace") if te.stdout else "")
            stderr = te.stderr if isinstance(te.stderr, str) else (te.stderr.decode("utf-8", errors="replace") if te.stderr else "")
            return {
                "stdout": stdout,
                "stderr": f"{stderr}\n[Execution Timed Out after {timeout_seconds} seconds]".strip(),
                "exit_code": -1,
                "timed_out": True
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Subprocess execution error: {str(e)}",
                "exit_code": -1,
                "timed_out": False
            }
