"""Dialog schemas placeholder."""

from enum import Enum
from pydantic import BaseModel


class DialogStatus(str, Enum):
    AUTO = "auto"
    WAIT_OPERATOR = "wait_operator"
    WAIT_USER = "wait_user"


class DialogOut(BaseModel):
    id: int
    status: DialogStatus

    class Config:
        from_attributes = True
