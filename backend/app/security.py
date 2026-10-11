import os
from datetime import datetime, timedelta, timezone

from jose import jwt
from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()

JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_MINUTES = int(
    os.getenv("JWT_ACCESS_TOKEN_MINUTES", "30")
)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(user_id: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=JWT_ACCESS_TOKEN_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "exp": expires_at,
        "type": "access",
    }

    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)