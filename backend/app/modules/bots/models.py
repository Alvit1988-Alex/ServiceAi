"""Bot model placeholder."""

from sqlalchemy import Column, Integer, String, ForeignKey

from app.database import Base


class Bot(Base):
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"))
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
