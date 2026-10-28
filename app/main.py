import logging
from collections.abc import Iterator

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Expense
from app.schemas import ExpenseCreate, ExpenseRead, ExpenseUpdate

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("expense_tracker")

app = FastAPI(title="Expense Tracker")


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_or_404(db: Session, expense_id: int) -> Expense:
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(status_code=404, detail=f"Expense {expense_id} not found")
    return expense


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/expenses", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
def create_expense(payload: ExpenseCreate, db: Session = Depends(get_db)) -> Expense:
    expense = Expense(**payload.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    logger.info("created expense id=%s", expense.id)
    return expense


@app.get("/expenses", response_model=list[ExpenseRead])
def list_expenses(
    category: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[Expense]:
    stmt = select(Expense).order_by(Expense.id)
    if category is not None:
        stmt = stmt.where(Expense.category == category)
    stmt = stmt.limit(limit).offset(offset)
    return list(db.scalars(stmt))


@app.get("/expenses/{expense_id}", response_model=ExpenseRead)
def get_expense(expense_id: int, db: Session = Depends(get_db)) -> Expense:
    return get_or_404(db, expense_id)


@app.patch("/expenses/{expense_id}", response_model=ExpenseRead)
def update_expense(
    expense_id: int, payload: ExpenseUpdate, db: Session = Depends(get_db)
) -> Expense:
    expense = get_or_404(db, expense_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if value is None and field != "notes":
            raise HTTPException(status_code=422, detail=f"{field} cannot be null")
        setattr(expense, field, value)
    db.commit()
    db.refresh(expense)
    return expense


@app.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: int, db: Session = Depends(get_db)) -> None:
    expense = get_or_404(db, expense_id)
    db.delete(expense)
    db.commit()
    logger.info("deleted expense id=%s", expense_id)