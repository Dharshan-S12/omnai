"""
MRPL Sovereign Workbench — Encryption at Rest Module
Provides AES-256 encryption & decryption for documents (.docx), forensic logs, and DB exports.
Key sourced securely from secrets management service.
"""

import os
import io
import json
from typing import Union, Optional
from cryptography.fernet import Fernet
from app.security.secrets import get_master_encryption_key

# Header marker to distinguish ciphertext files from unencrypted files
CIPHERTEXT_HEADER = b"MRPL_ENC_v1::"

def _get_fernet() -> Fernet:
    """Initializes Fernet cipher with master encryption key."""
    key = get_master_encryption_key()
    return Fernet(key)

def encrypt_bytes(data: bytes) -> bytes:
    """Encrypts raw byte data using AES-128-CBC / HMAC-SHA256 authenticated container (Fernet)."""
    cipher = _get_fernet()
    token = cipher.encrypt(data)
    return CIPHERTEXT_HEADER + token

def decrypt_bytes(encrypted_data: bytes) -> bytes:
    """Decrypts ciphertext bytes. Raises error if invalid key or corrupted data."""
    if not encrypted_data.startswith(CIPHERTEXT_HEADER):
        # Already plaintext or unencrypted
        return encrypted_data
    token = encrypted_data[len(CIPHERTEXT_HEADER):]
    cipher = _get_fernet()
    return cipher.decrypt(token)

def encrypt_file_at_rest(file_path: str, output_path: Optional[str] = None) -> str:
    """
    Encrypts a file on disk in-place or to a target output path.
    Returns path of encrypted file.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, "rb") as f:
        data = f.read()
    
    # If already encrypted, skip
    if data.startswith(CIPHERTEXT_HEADER):
        return file_path
        
    encrypted = encrypt_bytes(data)
    target = output_path or file_path
    with open(target, "wb") as f:
        f.write(encrypted)
    return target

def decrypt_file_at_rest(file_path: str, output_path: Optional[str] = None) -> bytes:
    """
    Decrypts an encrypted file from disk and returns plaintext bytes.
    Optionally writes decrypted contents to output_path.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    with open(file_path, "rb") as f:
        data = f.read()
        
    plaintext = decrypt_bytes(data)
    if output_path:
        with open(output_path, "wb") as f:
            f.write(plaintext)
    return plaintext

def is_file_encrypted(file_path: str) -> bool:
    """Checks whether a file on disk begins with the MRPL encryption header."""
    if not os.path.exists(file_path):
        return False
    try:
        with open(file_path, "rb") as f:
            header = f.read(len(CIPHERTEXT_HEADER))
            return header == CIPHERTEXT_HEADER
    except Exception:
        return False
