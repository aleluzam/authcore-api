from fastapi import status, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib import PasswordHash
from jose import jwt
from jose.exceptions import ExpiredSignatureError
from datetime import datetime, timedelta, timezone
import uuid

from app.settings import settings

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm

password_hash = PasswordHash([Argon2Hasher()])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


# ok
def hash_password(pw: str):
    return password_hash.hash(pw)

# ok
def verify_password(pw: str, hashed_pw: str):
    return password_hash.verify(pw, hashed_pw)

# ok
def encode_jwt(payload: dict):
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a dictionary")
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY not configured")
    
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# ok
def decode_jwt(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired, login again",
            headers={"WWW-Authenticate": "Bearer"}
        )

# ok
def generate_payload(user_id: uuid.UUID) -> dict:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=15),
        "jti": str(uuid.uuid4())
    }
    return payload