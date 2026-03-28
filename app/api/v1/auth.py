from fastapi import APIRouter, Depends

from app.database import get_db, AsyncSession
from app.schemas.users_schemas import UserValidate
from app.services.auth_service import register_new_user

from app.core.mail import send_mail
from app.schemas.mail_schemas import EmailRequest

auth_router = APIRouter(prefix="/v1/auth")


@auth_router.post("/register")
async def register(user_data: UserValidate, db: AsyncSession = Depends(get_db)):
    return await register_new_user(user_data=user_data, db=db)