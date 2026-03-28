from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib import PasswordHash
from jose import jwt, JWTError

password_hash = PasswordHash([Argon2Hasher()])

def hash_password(pw: str):
    return password_hash.hash(pw)

def verify_password(pw: str, hashed_pw: str):
    return password_hash.verify(pw, hashed_pw)