"""Account domain models (placeholders)."""

from sqlalchemy import Column, Integer, String

from app.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
