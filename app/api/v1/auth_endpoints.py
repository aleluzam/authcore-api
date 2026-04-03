from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.users_schemas import UserValidate
from app.services.auth_service import register_new_user, verify_mail


from app.core.mail import send_mail
from app.schemas.mail_schemas import EmailRequest

auth_router = APIRouter(prefix="/v1/auth")


@auth_router.post("/register")
async def register(user_data: UserValidate, db: AsyncSession = Depends(get_db)):
    return await register_new_user(user_data=user_data, db=db)

@auth_router.get("/verify-mail")
async def verify(token: str, db: AsyncSession = Depends(get_db)):
    return await verify_mail(token, db)


@auth_router.get("/login")
async def login(db: AsyncSession = Depends(get_db), data: OAuth2PasswordRequestForm = Depends()):
    
        
    