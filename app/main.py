from fastapi import FastAPI, Depends, HTTPException, status
from contextlib import asynccontextmanager
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.dependencies import get_db, AsyncSessionLocal
from app.settings import settings
from app.api.v1.auth_endpoints import auth_router
from app.logger import setup_logger

setup_logger()
logger = logging.getLogger("app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.secret_key:
        raise RuntimeError("SECRET_KEY not configured, App cant run")
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
            logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise RuntimeError(f"Database unavailable: {str(e)}")
    
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(auth_router)


@app.get("/")
async def route():
    return "Hello"

@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    try:
        query = await db.execute(text("SELECT 1"))
        return {
            "health": "healthy",
            "db": "conected"
        }
        
    except Exception as e:
        logger.error(f"Error trying to connect database, error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database unavailable"
        )