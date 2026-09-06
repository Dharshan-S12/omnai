import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.sandbox.run_code import run_code, SANDBOX_LOG_PATH

def test_sandbox_security():
    print("=" * 70)
    print("   TEST: AST Python Sandbox Security & Isolation Gating              ")
    print("=" * 70)

    # 1. Attempt to import subprocess
    code_sub = "import subprocess\nsubprocess.run(['dir'])"
    res_sub = run_code(code_sub)
    print(f" -> Subprocess attempt: Blocked={res_sub['security_blocked']}, Msg='{res_sub['stderr']}'")
    assert res_sub["security_blocked"] is True, "Subprocess import must be blocked"

    # 2. Attempt to import os
    code_os = "import os\nprint(os.listdir('.'))"
    res_os = run_code(code_os)
    print(f" -> OS import attempt: Blocked={res_os['security_blocked']}, Msg='{res_os['stderr']}'")
    assert res_os["security_blocked"] is True, "OS module import must be blocked"

    # 3. Attempt to import socket
    code_sock = "import socket\ns = socket.socket()"
    res_sock = run_code(code_sock)
    print(f" -> Socket import attempt: Blocked={res_sock['security_blocked']}, Msg='{res_sock['stderr']}'")
    assert res_sock["security_blocked"] is True, "Socket module import must be blocked"

    # 4. Attempt dynamic eval / exec
    code_eval = "code_str = '1 + 1'\nprint(eval(code_str))"
    res_eval = run_code(code_eval)
    print(f" -> Eval builtin attempt: Blocked={res_eval['security_blocked']}, Msg='{res_eval['stderr']}'")
    assert res_eval["security_blocked"] is True, "eval() builtin must be blocked"

    # 5. Legitimate safe math & calculation using standard library / numpy
    code_safe = """
import math
readings = [2.1, 3.5, 5.8, 6.2]
mean = sum(readings) / len(readings)
rms = math.sqrt(sum(x**2 for x in readings) / len(readings))
print(f"MEAN: {mean:.2f}, RMS: {rms:.2f}")
"""
    res_safe = run_code(code_safe)
    print(f" -> Safe math computation: ExitCode={res_safe['exit_code']}, Stdout='{res_safe['stdout'].strip()}'")
    assert res_safe["exit_code"] == 0, "Safe calculation must succeed"
    assert "RMS: 4.71" in res_safe["stdout"], "Safe calculation must output correct mathematical result"

    # 6. Verify security rejection log
    assert os.path.exists(SANDBOX_LOG_PATH), f"Sandbox log not found at {SANDBOX_LOG_PATH}"
    print(f" -> Verified security rejection audit events logged to {SANDBOX_LOG_PATH}")

    print("\n[PASS] AST Sandbox successfully blocked all restricted imports and executed safe code!")
    print("=" * 70)

if __name__ == "__main__":
    test_sandbox_security()
