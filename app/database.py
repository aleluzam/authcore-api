from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.settings import settings


Base = declarative_base()

engine = create_async_engine(settings.async_database_url)

AsyncSessionLocal = async_sessionmaker(bind=engine)

async def get_db():
   async with AsyncSessionLocal() as db:
        yield db