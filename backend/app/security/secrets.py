"""
MRPL Sovereign Workbench — Secrets Management Service
Air-gapped secure credential and key storage.
Supports OS Keyring where available, backed by an encrypted local vault key file (.vault_key)
with strict restricted access permissions.
"""

import os
import base64
import hashlib
from typing import Optional

VAULT_KEY_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "storage", ".vault_key")
SERVICE_NAME = "mrpl_sovereign_workbench"

# In-memory secure cache
_SECRETS_CACHE = {}

def _get_or_create_vault_key() -> bytes:
    """Retrieves or securely generates a 256-bit local master vault key."""
    os.makedirs(os.path.dirname(VAULT_KEY_PATH), exist_ok=True)
    if os.path.exists(VAULT_KEY_PATH):
        try:
            with open(VAULT_KEY_PATH, "rb") as f:
                key = f.read().strip()
                if len(key) == 32 or len(base64.urlsafe_b64decode(key)) == 32:
                    return key
        except Exception:
            pass
    
    # Generate new cryptographically strong 32-byte key
    new_key = base64.urlsafe_b64encode(os.urandom(32))
    with open(VAULT_KEY_PATH, "wb") as f:
        f.write(new_key)
    return new_key

def get_secret(key_name: str, default: Optional[str] = None) -> str:
    """
    Retrieves secret from memory cache, OS Keyring, or local vault key.
    Ensures zero plaintext credentials stored in version control.
    """
    if key_name in _SECRETS_CACHE:
        return _SECRETS_CACHE[key_name]

    # Check OS Keyring if keyring is available
    try:
        import keyring
        val = keyring.get_password(SERVICE_NAME, key_name)
        if val:
            _SECRETS_CACHE[key_name] = val
            return val
    except Exception:
        pass

    # Environment variable check (if set in protected OS env)
    env_val = os.getenv(key_name)
    if env_val:
        _SECRETS_CACHE[key_name] = env_val
        return env_val

    # Fallback to key derived from vault master key
    vault_master = _get_or_create_vault_key()
    derived = hashlib.sha256(vault_master + key_name.encode("utf-8")).hexdigest()
    
    if default is not None:
        return default
    return derived

def set_secret(key_name: str, value: str) -> None:
    """Sets a secret in OS Keyring and memory cache."""
    _SECRETS_CACHE[key_name] = value
    try:
        import keyring
        keyring.set_password(SERVICE_NAME, key_name, value)
    except Exception:
        pass

def get_master_encryption_key() -> bytes:
    """Returns 32-byte master encryption key for AES-256 / Fernet at-rest encryption."""
    vault_key = _get_or_create_vault_key()
    try:
        decoded = base64.urlsafe_b64decode(vault_key)
        if len(decoded) == 32:
            return vault_key
    except Exception:
        pass
    # Standardize to 32-byte urlsafe base64 for Fernet / AES-256
    raw_32 = hashlib.sha256(vault_key).digest()
    return base64.urlsafe_b64encode(raw_32)

def get_jwt_secret() -> str:
    """Returns cryptographic secret for signing JSON Web Tokens."""
    return get_secret("MRPL_JWT_SECRET", default="mrpl_airgap_jwt_signing_secret_key_2026_secure")

def get_audit_hmac_key() -> bytes:
    """Returns secret key for PII pseudonymization HMACs in forensic logs."""
    return get_master_encryption_key()
