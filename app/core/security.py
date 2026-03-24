from pwdlib import PasswordHash

password_hask = PasswordHash()

def hash_password(pw):
    return password_hask.hash(pw)

def verify_password(pw, hashed_pw):
    return password_hask.verify(pw, hashed_pw)