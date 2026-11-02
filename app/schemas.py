from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal

CURRENCY_PATTERN = r"^[A-Z]{3}$"


class ExpenseCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    description: str = Field(min_length=1, max_length=200)
    amount_minor: int = Field(gt=0)
    category: str = Field(default="other", min_length=1, max_length=50)
    notes: str | None = Field(default=None, max_length=500)
    currency: str = Field(default="USD", pattern=CURRENCY_PATTERN)


class ExpenseUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    description: str | None = Field(default=None, min_length=1, max_length=200)
    amount_minor: int | None = Field(default=None, gt=0)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    notes: str | None = Field(default=None, max_length=500)
    currency: str | None = Field(default=None, pattern=CURRENCY_PATTERN)


class ExpenseRead(ExpenseCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime

class ConvertedExpense(BaseModel):
    expense_id: int
    original_amount_minor: int
    original_currency: str
    target_currency: str
    rate: Decimal
    converted_amount_minor: int