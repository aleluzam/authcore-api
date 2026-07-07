from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose.exceptions import JWTError
from uuid import UUID
import logging

from app.database import AsyncSessionLocal
from app.models.users import UserTable
from app.core.security import oauth2_scheme, decode_jwt

logger = logging.getLogger(__name__)

# sesions
async def get_db():
   async with AsyncSessionLocal() as db:
        yield db


# main security function
async def validate_user(db: AsyncSession, token: str = Depends(oauth2_scheme)) -> UserTable:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credencials cant be validated",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        payload = decode_jwt(token)
        user_id_raw = payload.get("sub")
        if not user_id_raw:
            raise credentials_exception
        user_id = UUID(user_id_raw)

    except (JWTError, ValueError, AttributeError):
        raise credentials_exception
    result = await db.execute(select(UserTable).filter(UserTable.id == user_id))
    user_existed = result.scalar_one_or_none()

    if not user_existed:
        raise credentials_exception
    return user_existed


# role decorator
def require_role(allowed_role: str):
    async def role_checker(token: str = Depends(oauth2_scheme)) -> dict:
        payload = decode_jwt(token)
        user_role = payload.get("role", "user")

        if user_role != allowed_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this resource"
            )

        return payload
    return role_checker
