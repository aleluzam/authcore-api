from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base

from app.settings import settings


Base = declarative_base()

engine = create_engine(settings.database_url)

def get_db():
    
    with Session(bind=engine) as session:
        try:
            yield session
        finally:
            session.close()
    