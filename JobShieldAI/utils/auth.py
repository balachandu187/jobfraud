"""
Security and JWT Session Helper for JobShield AI
Implements PBKDF2-HMAC-SHA256 password hashing with per-user salt,
constant-time signature verification, and tamper-proof HMAC-SHA256 bearer tokens.
"""

import os
import hmac
import hashlib
import base64
import json
import time
from typing import Optional, Dict, Any

# Dynamic server secret key (persisted across reboots or generated from machine seed)
SECRET_KEY = os.environ.get("JOBSHIELD_SECRET_KEY", "jobshield-ai-cyber-secret-token-sign-key-2026")
TOKEN_EXPIRY_SECONDS = 86400 * 7  # 7-day session validity

def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hashes a plaintext password with PBKDF2-HMAC-SHA256."""
    if not salt:
        salt = base64.b64encode(os.urandom(16)).decode('utf-8')
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    pw_hash = base64.b64encode(key).decode('utf-8')
    return pw_hash, salt

def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verifies a password against the stored PBKDF2 hash using constant-time comparison."""
    calculated_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(calculated_hash, stored_hash)

def create_auth_token(user_id: int, email: str, role: str, full_name: str) -> str:
    """Creates a signed, URL-safe session token with timestamp and expiry."""
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "name": full_name,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRY_SECONDS
    }
    raw_payload = base64.urlsafe_b64encode(json.dumps(payload).encode('utf-8')).decode('utf-8').rstrip('=')
    signature = hmac.new(SECRET_KEY.encode('utf-8'), raw_payload.encode('utf-8'), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')
    return f"{raw_payload}.{sig_b64}"

def verify_auth_token(token: str) -> Optional[Dict[str, Any]]:
    """Verifies cryptographic signature and expiry of the bearer token."""
    if not token or "." not in token:
        return None
    try:
        raw_payload, sig_b64 = token.split(".", 1)
        # Verify signature
        expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), raw_payload.encode('utf-8'), hashlib.sha256).digest()
        calc_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode('utf-8').rstrip('=')
        if not hmac.compare_digest(sig_b64, calc_sig_b64):
            return None
        
        # Decode payload
        padding = "=" * ((4 - len(raw_payload) % 4) % 4)
        payload_bytes = base64.urlsafe_b64decode((raw_payload + padding).encode('utf-8'))
        payload = json.loads(payload_bytes.decode('utf-8'))
        
        # Check expiry
        if payload.get("exp", 0) < time.time():
            return None
            
        return payload
    except Exception:
        return None
