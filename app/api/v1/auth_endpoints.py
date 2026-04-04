from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.users_schemas import UserValidate
from app.services.auth_service import register_new_user, verify_mail, users_login, generate_access_token, logout


from app.core.mail import send_mail
from app.schemas.mail_schemas import EmailRequest

auth_router = APIRouter(prefix="/v1/auth")


@auth_router.post("/register")
async def register(user_data: UserValidate, db: AsyncSession = Depends(get_db)):
    return await register_new_user(user_data=user_data, db=db)


@auth_router.get("/verify-mail")
async def verify(token: str, db: AsyncSession = Depends(get_db)):
    return await verify_mail(token, db)


@auth_router.post("/login")
async def login(data: UserValidate, db: AsyncSession = Depends(get_db)):
    return await users_login(data, db)    
        
@auth_router.post("/refresh")
async def refresh(refresh_token: str):
    return await generate_access_token(refresh_token)

@auth_router.delete("/logout")
async def logout_user(refresh_token: str):
    return await logout(refresh_token)