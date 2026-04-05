from fastapi import HTTPException, status
from sqlalchemy import select
import httpx
import logging
import secrets

from app.dependencies import AsyncSession
from app.models.users import UserTable
from app.core.security import generate_payload, encode_jwt
from app.core.redis import redis_client
from app.settings import settings

logger = logging.getLogger(__name__)


async def get_google_user_info(code: str) -> dict:
    try:
        
        # getting google token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data = {
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": settings.google_redirect_uri,
                    "grant_type": "authorization_code"
                }
            )
            token_data = token_response.json()
            
            if "access_token" not in token_data:
                logger.warning(f"Google token exchange failed: {token_data}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to authenticate with Google"
                )
            
            #getting user google data
            user_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {token_data['access_token']}"} 
            )
            
            user_info = user_response.json()
            if "email" not in user_info:
                logger.warning(f"Google user info missing email: {user_info}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Could not retrieve email from Google"
                )
            
            return user_info
    
    except HTTPException:
        raise
    
    except httpx.HTTPError as e:
        logger.error(f"Google API connection error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to Google"
        )
    
    except Exception as e:
            logger.error(f"Unexpected error getting Google user info: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal Server Error"
            )



async def google_auth(code: str, db: AsyncSession) -> dict:
    try:
        
        user_info = await get_google_user_info(code)
        email = user_info["email"]
        
        result = await db.execute(select(UserTable).filter(UserTable.mail == email))
        user = result.scalar_one_or_none()
        
        if not user:
            user = UserTable(
                mail = email,
                hashed_password = None,
                is_verified = True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        access_token = encode_jwt(generate_payload(user.id))
        refresh_token = secrets.token_urlsafe(32)
        
        await redis_client.setex(f"refresh_token:{refresh_token}", 604800, str(user.id))
        
        return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer"
                }        
    except HTTPException:
            raise
        
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Redis unavailable during Google auth: {str(e)}")            
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable"
        )
        
    except Exception as e:
        logger.error(f"Unexpected error during Google auth: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error"
        )