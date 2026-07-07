from sqlalchemy import Column, String, UUID, Boolean, ForeignKey
from sqlalchemy.orm import relationship
import uuid

from app.database import Base
from app.models.mixins import TimestampMixin

class UserTable(Base, TimestampMixin):
    __tablename__="users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mail = Column(String(255), index=True, unique=True, nullable=False)
    hashed_password = Column(String(220), nullable=True)
    is_verified = Column(Boolean, default=False)

    role_id = Column(UUID(as_uuid=True), ForeignKey("role.id"), nullable = False)
    role = relationship("RoleTable", back_populates="users", lazy="joined")

class RoleTable(Base, TimestampMixin):
	__tablename__="role"

	id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	rolename = Column(String(15), nullable=False, default="user")
	users = relationship("UserTable", back_populates="role", lazy="select")
