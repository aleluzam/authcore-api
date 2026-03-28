from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import text
import logging

from app.database import AsyncSession, get_db
from app.api.v1.auth import auth_router
from app.logger import setup_logger

setup_logger()
logger = logging.getLogger("app")

app = FastAPI()
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