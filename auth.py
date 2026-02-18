import os
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import jwt, JWTError
from passlib.context import CryptContext

JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME_SUPER_SECRET")
JWT_ALG = "HS256"
JWT_EXPIRE_MIN = int(os.getenv("JWT_EXPIRE_MIN", "10080"))  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(p: str) -> str:
    return pwd_context.hash(p)

def verify_password(p: str, hashed: str) -> bool:
    return pwd_context.verify(p, hashed)

def create_token(payload: Dict) -> str:
    exp = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MIN)
    payload = {**payload, "exp": exp}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def decode_token(token: str) -> Optional[Dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError:
        return None
