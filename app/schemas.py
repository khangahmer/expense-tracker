from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExpenseCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    description: str = Field(min_length=1, max_length=200)
    amount_minor: int = Field(gt=0)
    category: str = Field(default="other", min_length=1, max_length=50)
    notes: str | None = Field(default=None, max_length=500)


class ExpenseUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    description: str | None = Field(default=None, min_length=1, max_length=200)
    amount_minor: int | None = Field(default=None, gt=0)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    notes: str | None = Field(default=None, max_length=500)


class ExpenseRead(ExpenseCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime