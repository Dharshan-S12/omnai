"""
MRPL Sovereign Workbench — Authentication Router
Exposes /auth/login and /auth/me for air-gapped JWT token issuance and user identity verification.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.auth.jwt_auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    User
)

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str
    full_name: str
    employee_id: str
    expires_in_hours: int = 24

@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """
    Authenticates user credentials against local on-prem directory and issues signed JWT.
    """
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )
    
    token = create_access_token(user)
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        username=user.username,
        role=user.role,
        full_name=user.full_name,
        employee_id=user.employee_id
    )

@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    """Returns currently authenticated user information decoded from verified JWT."""
    return current_user
