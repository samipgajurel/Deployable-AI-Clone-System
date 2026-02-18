import os
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGO = "HS256"
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_EXPIRE_MIN = int(os.getenv("JWT_EXPIRE_MIN", "43200"))  # 30 days

def _bcrypt_safe(p: str) -> str:
    p = (p or "")
    b = p.encode("utf-8")[:72]
    return b.decode("utf-8", errors="ignore")

def hash_password(p: str) -> str:
    return pwd_context.hash(_bcrypt_safe(p))

def verify_password(p: str, hashed: str) -> bool:
    return pwd_context.verify(_bcrypt_safe(p), hashed)

def create_token(payload: dict) -> str:
    exp = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MIN)
    to_encode = {**payload, "exp": exp}
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGO)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[ALGO])
    except JWTError:
        return {}
