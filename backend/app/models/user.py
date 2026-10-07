import enum

from sqlalchemy import Column, DateTime, Enum, Integer, String, func

from app.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"              # Event Administrator
    OPERATOR = "OPERATOR"        # Control Room Operator
    MAINTENANCE = "MAINTENANCE"  # Maintenance staff


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    status = Column(Enum(UserStatus), nullable=False, server_default="ACTIVE")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)