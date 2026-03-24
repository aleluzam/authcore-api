from sqlalchemy import Column, String, UUID, Boolean
import uuid

from app.database import Base
from app.models.mixins import TimestampMixin


class UserTable(Base, TimestampMixin):
    __tablename__="users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mail = Column(String(255), index=True, unique=True, nullable=False)
    hashed_password = Column(String(220), nullable=False)
    is_verified = Column(Boolean, default=False)