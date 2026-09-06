"""
MRPL Sovereign Workbench — Air-Gapped Real Authentication & JWT Subsystem
Implements bcrypt-hashed local credential directory and signed JWT access tokens.
Enforces cryptographic subject binding for all supervisory actions and audit trails.
"""

import os
import jwt
import bcrypt
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from fastapi import Header, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.security.secrets import get_jwt_secret

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

security_scheme = HTTPBearer(auto_error=False)

class User(BaseModel):
    user_id: str
    username: str
    role: str
    full_name: str
    employee_id: str
    is_active: bool = True

class TokenData(BaseModel):
    username: str
    role: str
    user_id: str
    exp: datetime

# Local On-Prem Air-Gapped Credential Store (bcrypt hashed)
# Seeded with standard MRPL roles
_USERS_DB = {
    "supervisor": {
        "user_id": "usr-sup-0012",
        "username": "supervisor",
        "role": "supervisor",
        "full_name": "Rajesh Kumar (Lead Supervisor)",
        "employee_id": "MRPL-EMP-0012",
        # bcrypt hash for 'mrpl_sup_2026!'
        "password_hash": bcrypt.hashpw(b"mrpl_sup_2026!", bcrypt.gensalt()).decode("utf-8"),
        "is_active": True
    },
    "operator": {
        "user_id": "usr-op-1044",
        "username": "operator",
        "role": "operator",
        "full_name": "Anil Verma (Field Operator)",
        "employee_id": "MRPL-EMP-1044",
        # bcrypt hash for 'mrpl_op_2026!'
        "password_hash": bcrypt.hashpw(b"mrpl_op_2026!", bcrypt.gensalt()).decode("utf-8"),
        "is_active": True
    },
    "admin": {
        "user_id": "usr-adm-0001",
        "username": "admin",
        "role": "admin",
        "full_name": "MRPL Sovereign System Administrator",
        "employee_id": "MRPL-EMP-0001",
        # bcrypt hash for 'mrpl_admin_2026!'
        "password_hash": bcrypt.hashpw(b"mrpl_admin_2026!", bcrypt.gensalt()).decode("utf-8"),
        "is_active": True
    }
}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against stored bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticates username and password against local on-prem directory."""
    user_record = _USERS_DB.get(username.lower().strip())
    if not user_record:
        return None
    if not verify_password(password, user_record["password_hash"]):
        return None
    return User(
        user_id=user_record["user_id"],
        username=user_record["username"],
        role=user_record["role"],
        full_name=user_record["full_name"],
        employee_id=user_record["employee_id"],
        is_active=user_record["is_active"]
    )

def create_access_token(user: User, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a cryptographically signed JWT token bound to user identity."""
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=JWT_EXPIRATION_HOURS))
    payload = {
        "sub": user.username,
        "user_id": user.user_id,
        "role": user.role,
        "full_name": user.full_name,
        "employee_id": user.employee_id,
        "iat": datetime.now(timezone.utc),
        "exp": expire
    }
    secret = get_jwt_secret()
    token = jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)
    return token

def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodes and verifies a JWT token's signature and expiration.
    Raises HTTPException on invalid or expired token.
    """
    secret = get_jwt_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Authentication token has expired. Please log in again.")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid authentication token: {str(e)}")

async def get_current_user(
    auth_header: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="X-Auth-Token")
) -> User:
    """
    FastAPI dependency that extracts and validates the JWT from Authorization header or X-Auth-Token.
    Strictly forbids forged or missing tokens.
    """
    token = None
    if auth_header and auth_header.credentials:
        token = auth_header.credentials
    elif authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
    elif x_auth_token:
        token = x_auth_token.strip()

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Missing Bearer JWT token."
        )

    payload = decode_access_token(token)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Token missing subject claim.")

    user_record = _USERS_DB.get(username)
    if not user_record:
        # User defined directly in verified token payload
        return User(
            user_id=payload.get("user_id", f"usr-{username}"),
            username=username,
            role=payload.get("role", "operator"),
            full_name=payload.get("full_name", username),
            employee_id=payload.get("employee_id", "MRPL-EXT")
        )

    return User(
        user_id=user_record["user_id"],
        username=user_record["username"],
        role=user_record["role"],
        full_name=user_record["full_name"],
        employee_id=user_record["employee_id"],
        is_active=user_record["is_active"]
    )

def require_roles(allowed_roles: List[str]):
    """Role-Based Access Control gate using verified JWT token identity."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.lower() not in [r.lower() for r in allowed_roles]:
            raise HTTPException(
                status_code=403,
                detail=f"Access Denied: Authenticated role '{current_user.role}' is not authorized. Required: {allowed_roles}"
            )
        return current_user
    return role_checker
