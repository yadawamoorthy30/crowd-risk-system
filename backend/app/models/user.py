import enum

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Integer, String, func, text,
)

from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"        # Event Administrator
    operator = "operator"  # Control Room Operator


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Boolean, nullable=False, server_default=text("1"))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)