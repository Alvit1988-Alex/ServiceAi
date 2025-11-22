"""Bot schemas."""

from pydantic import BaseModel


class BotCreateIn(BaseModel):
    name: str
    description: str | None = None


class BotOut(BaseModel):
    id: int
    name: str
    description: str | None = None

    class Config:
        from_attributes = True
