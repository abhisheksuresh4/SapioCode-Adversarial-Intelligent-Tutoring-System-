"""
Authentication API Routes
Endpoints: POST /register, POST /login, GET /profile, POST /refresh
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel

from app.auth.jwt_handler import (
    hash_password, verify_password, create_token_pair,
    get_current_user, decode_token, create_access_token
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ─── Request / Response Models ─────────────────────────────
class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    full_name: Optional[str] = None
    role: str = "student"


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class ProfileResponse(BaseModel):
    user_id: int
    email: str
    username: str
    role: str
    full_name: Optional[str]
    created_at: str


# ─── Register ─────────────────────────────────────────────
@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(request: RegisterRequest):
    """Register a new student or teacher account"""
    # Try PostgreSQL first, fallback to in-memory
    try:
        from sqlalchemy import select
        from app.db.postgres import get_db, User

        # Get async DB session
        db_gen = get_db()
        db = await db_gen.__anext__()
        try:
            # Check existing
            existing = await db.execute(
                select(User).where(
                    (User.username == request.username) | (User.email == request.email)
                )
            )
            if existing.scalar_one_or_none():
                raise HTTPException(409, "Username or email already registered")

            if request.role not in ("student", "teacher"):
                raise HTTPException(400, "Role must be 'student' or 'teacher'")

            user = User(
                email=request.email,
                username=request.username,
                password_hash=hash_password(request.password),
                role=request.role,
                full_name=request.full_name,
                created_at=datetime.utcnow()
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

            tokens = create_token_pair(user.id, user.username, user.role)
            return TokenResponse(
                **tokens,
                user={
                    "user_id": user.id, "username": user.username,
                    "email": user.email, "role": user.role,
                    "full_name": user.full_name
                }
            )
        finally:
            await db.close()

    except (ImportError, RuntimeError):
        # No PostgreSQL — use in-memory registration for dev
        return _register_in_memory(request)


def _register_in_memory(request: RegisterRequest) -> TokenResponse:
    """Fallback registration when PostgreSQL is unavailable"""
    if request.username in _memory_users:
        raise HTTPException(409, "Username already registered")

    user_id = len(_memory_users) + 1
    _memory_users[request.username] = {
        "id": user_id,
        "email": request.email,
        "username": request.username,
        "password_hash": hash_password(request.password),
        "role": request.role,
        "full_name": request.full_name,
        "created_at": datetime.utcnow().isoformat()
    }

    tokens = create_token_pair(user_id, request.username, request.role)
    return TokenResponse(
        **tokens,
        user={
            "user_id": user_id, "username": request.username,
            "email": request.email, "role": request.role,
            "full_name": request.full_name
        }
    )


# In-memory user store (fallback when no PostgreSQL)
_memory_users: dict = {}


# ─── Login ─────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate and get JWT tokens"""
    try:
        from sqlalchemy import select
        from app.db.postgres import get_db, User

        db_gen = get_db()
        db = await db_gen.__anext__()
        try:
            result = await db.execute(
                select(User).where(
                    (User.username == request.username) | (User.email == request.username)
                )
            )
            user = result.scalar_one_or_none()

            if not user or not verify_password(request.password, user.password_hash):
                raise HTTPException(401, "Invalid credentials")
            if not user.is_active:
                raise HTTPException(403, "Account is deactivated")

            user.last_login = datetime.utcnow()
            await db.commit()

            tokens = create_token_pair(user.id, user.username, user.role)
            return TokenResponse(
                **tokens,
                user={
                    "user_id": user.id, "username": user.username,
                    "email": user.email, "role": user.role,
                    "full_name": user.full_name
                }
            )
        finally:
            await db.close()

    except (ImportError, RuntimeError):
        return _login_in_memory(request)


def _login_in_memory(request: LoginRequest) -> TokenResponse:
    """Fallback login when PostgreSQL is unavailable"""
    user_data = _memory_users.get(request.username)
    if not user_data or not verify_password(request.password, user_data["password_hash"]):
        raise HTTPException(401, "Invalid credentials")

    tokens = create_token_pair(user_data["id"], user_data["username"], user_data["role"])
    return TokenResponse(
        **tokens,
        user={
            "user_id": user_data["id"], "username": user_data["username"],
            "email": user_data["email"], "role": user_data["role"],
            "full_name": user_data["full_name"]
        }
    )


# ─── Profile ──────────────────────────────────────────────
@router.get("/profile", response_model=ProfileResponse)
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Get current user's profile"""
    try:
        from sqlalchemy import select
        from app.db.postgres import get_db, User

        db_gen = get_db()
        db = await db_gen.__anext__()
        try:
            result = await db.execute(
                select(User).where(User.id == current_user["user_id"])
            )
            user = result.scalar_one_or_none()
            if not user:
                raise HTTPException(404, "User not found")
            return ProfileResponse(
                user_id=user.id, email=user.email, username=user.username,
                role=user.role, full_name=user.full_name,
                created_at=user.created_at.isoformat()
            )
        finally:
            await db.close()

    except (ImportError, RuntimeError):
        # Fallback
        for uname, data in _memory_users.items():
            if data["id"] == current_user["user_id"]:
                return ProfileResponse(
                    user_id=data["id"], email=data["email"],
                    username=data["username"], role=data["role"],
                    full_name=data["full_name"], created_at=data["created_at"]
                )
        raise HTTPException(404, "User not found")


# ─── Refresh Token ─────────────────────────────────────────
@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """Get a new access token using a refresh token"""
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token")

    new_access = create_access_token({
        "sub": payload["sub"], "username": payload["username"],
        "role": payload["role"], "type": "access"
    })
    return {"access_token": new_access, "token_type": "bearer"}
