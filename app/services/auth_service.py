from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from redis.exceptions import ConnectionError, TimeoutError
from uuid import UUID
import logging
import secrets
import json

from app.core.redis import redis_client
from app.settings import settings
from app.schemas.users_schemas import UserValidate
from app.schemas.mail_schemas import EmailRequest
from app.models.users import UserTable, RoleTable
from app.core.security import hash_password, generate_payload, encode_jwt, verify_password
from app.core.mail import send_mail

logger = logging.getLogger(__name__)

# register
async def register_new_user(user_data: UserValidate, db: AsyncSession):
    try:
        result = await db.execute(select(UserTable).where(UserTable.mail == user_data.mail))
        check_mail = result.scalar_one_or_none()
        if check_mail:
            logger.warning(f"Duplicate registration attempt for mail: {user_data.mail}")
            return {"message": "If this mail is not registered, you will receive a verification link"}

        # Buscar el rol por defecto
        role_result = await db.execute(select(RoleTable).where(RoleTable.rolename == "user"))
        default_role = role_result.scalar_one_or_none()
        if default_role is None:
            logger.error("Default role 'user' not found in database")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal Server Error"
            )

        hashed_pw = hash_password(user_data.password)

        db_user = UserTable(
            mail = user_data.mail,
            hashed_password = hashed_pw,
            role_id = default_role.id
        )
        db.add(db_user)
        await db.flush()
        await db.refresh(db_user)

        # for redis
        token = secrets.token_urlsafe(32)
        await redis_client.setex(f"verify-mail:{token}", 3600, str(db_user.id))

        link = f"{settings.base_url}/v1/auth/verify-mail?token={token}"
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

# mail_verification
async def verify_mail(token: str, db: AsyncSession):
    try:
        storaged_data = await redis_client.get(f"verify-mail:{token}")
        if not storaged_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        try:
            user_uuid = UUID(storaged_data)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        result = await db.execute(select(UserTable).filter(UserTable.id == user_uuid))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        if user.is_verified == True:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already verified"
            )

        user.is_verified = True
        db.add(user)
        await db.commit()

        await redis_client.delete(f"verify-mail:{token}")

        return {
            "status": "ok",
            "message": "User succesfully verified"
        }

    except HTTPException:
        raise

    except (ConnectionError, TimeoutError) as e:
        await db.rollback()
        logger.error(f"Redis unavailable: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable"
        )

    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error during verification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error"
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error during verification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error"
        )

# login
async def users_login(user_data: UserValidate, db: AsyncSession) -> dict:
    try:
        user_data_dict = await validate_user_data(user_data, db)
        if not user_data_dict:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"}
            )

        payload = generate_payload(user_data_dict["user_id"], user_data_dict["role"])
        access_token = encode_jwt(payload)

        refresh_token = secrets.token_urlsafe(32)

        # Store user_id and role in Redis as JSON
        refresh_data = json.dumps({
            "user_id": str(user_data_dict["user_id"]),
            "role": user_data_dict["role"]
        })
        await redis_client.setex(f"refresh_token:{refresh_token}", 604800, refresh_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer"
        }

    except HTTPException as e:
        logger.error(f"Login error: {str(e)}")
        raise

    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Redis unavailable: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable"
        )

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create access token",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def validate_user_data(user_data: UserValidate, db: AsyncSession) -> dict | None:
    result = await db.execute(select(UserTable).filter(UserTable.mail == user_data.mail))
    user_in_db = result.scalar_one_or_none()

    if not user_in_db:
        logger.warning("Failed login attempt")
        return None

    if not user_in_db.is_verified:
        logger.info("Login attempt for unverified account")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified"
        )

    if not verify_password(user_data.password, user_in_db.hashed_password):
        logger.warning("Failed login attempt")
        return None

    return {
        "user_id": user_in_db.id,
        "role": user_in_db.role.rolename,
        "is_verified": user_in_db.is_verified
    }


async def generate_access_token(refresh_token: str) -> dict:
    try:

        stored_data = await redis_client.get(f"refresh_token:{refresh_token}")
        if not stored_data:
            in_blacklist = await redis_client.get(f"blacklist:{refresh_token}")
            if in_blacklist:
                await redis_client.delete(f"refresh_token:{refresh_token}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token reuse detected"
                )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        # Parse JSON stored in Redis
        try:
            refresh_data = json.loads(stored_data)
            user_id = refresh_data["user_id"]
            user_role = refresh_data["role"]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Invalid refresh token data format: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

        new_access_token = encode_jwt(generate_payload(UUID(user_id), user_role))
        new_refresh_token = secrets.token_urlsafe(32)

        await redis_client.setex(f"blacklist:{refresh_token}", 604800, user_id)
        await redis_client.delete(f"refresh_token:{refresh_token}")

        # Store new refresh token with user_id and role
        new_refresh_data = json.dumps({
            "user_id": user_id,
            "role": user_role
        })
        await redis_client.setex(f"refresh_token:{new_refresh_token}", 604800, new_refresh_data)

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "Bearer"
                }

    except HTTPException as e:
        logger.error(f"Error: {str(e)}")
        raise

    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Redis unavailable: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable"
        )

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create access token",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def logout(refresh_token: str):
    try:
        token_in_redis = await redis_client.get(f"refresh_token:{refresh_token}")
        if not token_in_redis:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token dont exist")

        await redis_client.delete(f"refresh_token:{refresh_token}")

        return {
            "message": "Logout successfully"
        }

    except HTTPException:
        raise

    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Redis unavailable: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable"
        )

    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error"
        )
