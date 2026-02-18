"""
JWT Authentication for SapioCode
Token creation, verification, password hashing, FastAPI dependencies
"""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

try:
    from jose import JWTError, jwt
    JOSE_AVAILABLE = True
except ImportError:
    JOSE_AVAILABLE = False

try:
    from passlib.context import CryptContext
    PASSLIB_AVAILABLE = True
except ImportError:
    PASSLIB_AVAILABLE = False

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "sapiocode-dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

# Password hashing (graceful fallback if passlib not installed)
if PASSLIB_AVAILABLE:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
else:
    pwd_context = None

security = HTTPBearer(auto_error=False)


# ─── Password Hashing ─────────────────────────────────────
def hash_password(password: str) -> str:
    if pwd_context is None:
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if pwd_context is None:
        import hashlib
        return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password
    return pwd_context.verify(plain_password, hashed_password)


# ─── Token Creation ────────────────────────────────────────
def create_access_token(data: Dict[str, Any],
                        expires_delta: Optional[timedelta] = None) -> str:
    if not JOSE_AVAILABLE:
        raise RuntimeError("python-jose not installed. Install it: pip install python-jose[cryptography]")

    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_token_pair(user_id: int, username: str, role: str) -> Dict[str, str]:
    access_token = create_access_token({
        "sub": str(user_id), "username": username,
        "role": role, "type": "access"
    })
    refresh_token = create_access_token(
        {"sub": str(user_id), "username": username,
         "role": role, "type": "refresh"},
        expires_delta=timedelta(days=7)
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


# ─── Token Verification ───────────────────────────────────
def decode_token(token: str) -> Dict[str, Any]:
    if not JOSE_AVAILABLE:
        raise RuntimeError("python-jose not installed")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ─── FastAPI Dependencies ─────────────────────────────────
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Extract and verify current user from JWT Bearer token"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    return {
        "user_id": int(payload["sub"]),
        "username": payload["username"],
        "role": payload["role"]
    }


async def require_teacher(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    if current_user["role"] not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="Teacher access required")
    return current_user


async def require_student(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    if current_user["role"] not in ("student", "admin"):
        raise HTTPException(status_code=403, detail="Student access required")
    return current_user
