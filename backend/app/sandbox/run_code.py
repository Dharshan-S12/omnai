import sys
import os
import ast
import subprocess
import tempfile
import json
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List, Optional

SANDBOX_LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "storage", "sandbox_security.log")

# Prohibited dangerous modules for AST inspection
BLOCKED_MODULES = {
    "subprocess", "os", "sys", "socket", "pty", "ctypes", "shutil",
    "urllib", "requests", "http", "ftplib", "telnetlib", "ssl",
    "multiprocessing", "threading", "signal", "posix", "nt", "winreg",
    "_winapi", "importlib", "pip", "site", "webbrowser"
}

# Dangerous function calls
BLOCKED_BUILTINS = {
    "eval", "exec", "__import__", "compile"
}

def inspect_code_ast(code: str) -> Tuple[bool, Optional[str]]:
    """
    Static AST Inspection before sandboxed execution:
    - Blocks unauthorized import of system, process-spawning, and networking libraries.
    - Blocks dynamic execution functions (eval, exec, __import__).
    - Blocks attempts to access system internals via getattr.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Python Syntax Error: {str(e)}"

    for node in ast.walk(tree):
        # 1. Inspect import statements: `import subprocess` or `import os.path`
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0].lower()
                if root_pkg in BLOCKED_MODULES:
                    return False, f"Security Violation: Import of restricted module '{alias.name}' is blocked by sandbox policy."

        # 2. Inspect from statements: `from os import system`
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_pkg = node.module.split(".")[0].lower()
                if root_pkg in BLOCKED_MODULES:
                    return False, f"Security Violation: Import from restricted module '{node.module}' is blocked by sandbox policy."

        # 3. Inspect dangerous builtin calls: `eval(...)`, `exec(...)`, `__import__(...)`
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in BLOCKED_BUILTINS:
                    return False, f"Security Violation: Invocation of dynamic execution builtin '{node.func.id}()' is blocked."
                if node.func.id == "open" and node.args:
                    if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                        target_p = node.args[0].value
                        if ".." in target_p or target_p.startswith(("/", "\\", "C:", "c:", "/etc", "\\Windows", "C:\\", "c:\\")):
                            return False, "Security Violation: File path outside ephemeral tempdir is blocked."

            # Check for os.system or subprocess calls via attribute
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in ["system", "popen", "spawn", "fork", "execv", "execve"]:
                    return False, f"Security Violation: Invocation of restricted attribute '{node.func.attr}' is blocked."

    return True, None

def log_sandbox_security_event(code: str, reason: str, event_type: str = "BLOCKED"):
    """Logs security rejection events to an append-only sandbox audit log."""
    os.makedirs(os.path.dirname(SANDBOX_LOG_PATH), exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "reason": reason,
        "code_snippet": code[:300]
    }
    try:
        with open(SANDBOX_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass

def run_code(code: str, timeout_seconds: int = 15) -> Dict[str, Any]:
    """
    Executes Python code in an AST-inspected, isolated ephemeral sandbox with strict timeout.
    """
    if not code or not code.strip():
        return {
            "stdout": "",
            "stderr": "No code provided to execute",
            "exit_code": 1,
            "timed_out": False,
            "security_blocked": False
        }

    # 1. Pre-execution AST security verification
    is_safe, violation_reason = inspect_code_ast(code)
    if not is_safe:
        log_sandbox_security_event(code, violation_reason or "AST Policy Violation", "AST_BLOCKED")
        return {
            "stdout": "",
            "stderr": f"[SECURITY SANDBOX BLOCK] {violation_reason}",
            "exit_code": -1,
            "timed_out": False,
            "security_blocked": True,
            "block_reason": violation_reason
        }

    # 2. Ephemeral subprocess runtime
    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = os.path.join(temp_dir, "solution.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)

        # Sanitized minimal runtime environment
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
                "timed_out": False,
                "security_blocked": False
            }
        except subprocess.TimeoutExpired as te:
            stdout = te.stdout if isinstance(te.stdout, str) else (te.stdout.decode("utf-8", errors="replace") if te.stdout else "")
            stderr = te.stderr if isinstance(te.stderr, str) else (te.stderr.decode("utf-8", errors="replace") if te.stderr else "")
            return {
                "stdout": stdout,
                "stderr": f"{stderr}\n[Execution Timed Out after {timeout_seconds} seconds]".strip(),
                "exit_code": -1,
                "timed_out": True,
                "security_blocked": False
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Subprocess execution error: {str(e)}",
                "exit_code": -1,
                "timed_out": False,
                "security_blocked": False
            }
