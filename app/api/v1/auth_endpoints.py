from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.settings import settings
from app.schemas.users_schemas import UserValidate
from app.services.auth_service import register_new_user, verify_mail, users_login, generate_access_token, logout
from app.services.google_auth_service import google_auth


from app.core.mail import send_mail
from app.schemas.mail_schemas import EmailRequest

auth_router = APIRouter(prefix="/v1/auth")


@auth_router.post("/register", tags=["auth"])
async def register(user_data: UserValidate, db: AsyncSession = Depends(get_db)):
    return await register_new_user(user_data=user_data, db=db)


@auth_router.get("/verify-mail", tags=["mail"])
async def verify(token: str, db: AsyncSession = Depends(get_db)):
    return await verify_mail(token, db)


@auth_router.post("/login", tags=["auth"])
async def login(data: UserValidate, db: AsyncSession = Depends(get_db)):
    return await users_login(data, db)    
        
        
@auth_router.post("/refresh", tags=["auth"])
async def refresh(refresh_token: str):
    return await generate_access_token(refresh_token)


@auth_router.delete("/logout", tags=["auth"])
async def logout_user(refresh_token: str):
    return await logout(refresh_token)


@auth_router.get("/google", tags=["google"])
async def google_login():
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.google_client_id}"
        f"&redirect_uri={settings.google_redirect_uri}"            
        "&response_type=code"
        "&scope=openid email profile"
        )
    return RedirectResponse(google_auth_url)


@auth_router.get("/google/callback", tags=["google"])
async def google_callback(code: str, db: AsyncSession = Depends(get_db)):
    return await google_auth(code, db)
