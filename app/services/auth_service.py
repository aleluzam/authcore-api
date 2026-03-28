from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone, timedelta
from redis.exceptions import ConnectionError, TimeoutError
import logging
import secrets

from app.database import get_db, AsyncSession
from app.core.redis import redis_client
from app.settings import settings
from app.schemas.users_schemas import UserValidate
from app.schemas.mail_schemas import EmailRequest
from app.models.users import UserTable
from app.core.security import hash_password
from app.core.mail import send_mail

logger = logging.getLogger(__name__)


async def register_new_user(user_data: UserValidate, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(UserTable).where(UserTable.mail == user_data.mail))
        check_mail = result.scalar_one_or_none()
        if check_mail:
            logger.warning(f"Duplicate registration attempt for mail: {user_data.mail}")
            return {"message": "If this mail is not registered, you will receive a verification link"}
        
        hashed_pw = hash_password(user_data.password)
        
        db_user = UserTable(
            mail = user_data.mail,
            hashed_password = hashed_pw
        )
        db.add(db_user)
        await db.flush()
        await db.refresh(db_user)
        
        token = secrets.token_urlsafe(32)
        
        await redis_client.setex(f"verify-mail:{token}", 3600, str(db_user.id))
        
        link = f"{settings.base_url}/auth/verify-mail?token={token}"
        email_object = EmailRequest(
            to = db_user.mail,
            subject="Verification mail",
            message=f"Your verification link is: {link}"
        )
        send_mail(email_object)
        
        await db.commit()        
                

        return {"message": "If this mail is not registered, you will receive a verification link"}
    
    except SQLAlchemyError as e:
        await db.rollback()
        logger.warning(f"Database error during registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error"
        )
        
    except (ConnectionError, TimeoutError) as e:
        await db.rollback()
        logger.error(f"Redis unavailable: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error"
        )    
    
    except Exception as e:
        await db.rollback()
        logger.warning(f"Unexpected error during registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error"
        )