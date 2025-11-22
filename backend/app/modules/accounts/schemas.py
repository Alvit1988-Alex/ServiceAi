"""Pydantic schemas for accounts."""

from pydantic import BaseModel


class AccountOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
