import enum

from sqlalchemy import (
    Column, DateTime, Enum, ForeignKey, Integer, Numeric, func, text,
)

from app.database import Base


class InSide(str, enum.Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class Tripwire(Base):
    __tablename__ = "tripwires"

    id = Column(Integer, primary_key=True, index=True)
    # unique=True -> one tripwire per camera (SRS 8.1.4)
    camera_id = Column(
        Integer,
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Line endpoints, normalised 0-1 (independent of video resolution)
    x1 = Column(Numeric(6, 5), nullable=False)
    y1 = Column(Numeric(6, 5), nullable=False)
    x2 = Column(Numeric(6, 5), nullable=False)
    y2 = Column(Numeric(6, 5), nullable=False)

    in_side = Column(Enum(InSide), nullable=False)
    cooldown_sec = Column(Integer, nullable=False, server_default=text("3"))

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )