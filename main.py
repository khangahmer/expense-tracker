from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel,Field

app = FastAPI(title="Expense Tracker")

class ExpenseCreate(BaseModel):
    description: str = Field(min_length=1, max_length=200)
    amount_minor: int= Field(gt=0)

class Expense(ExpenseCreate):
    id: int

#temporary storage 
expenses: dict[int, Expense] = {}
next_id=1

@app.get("/health")
def health() -> dict[str, str]:
    return {"status":"ok"}

@app.post("/expenses", response_model=Expense, status_code=status.HTTP_201_CREATED)
def create_expense(payload:ExpenseCreate) -> Expense:
    global next_id
    expense = Expense(id = next_id, **payload.model_dump())
    expenses[next_id] = expense
    next_id +=1
    return expense

@app.get("/expenses", response_model=list[Expense])
def list_expenses() -> list[Expense]:
    return list(expenses.values())

@app.get("/expenses/{expense_id}", response_model= Expense)
def get_expense(expense_id: int) -> Expense:
    expense = expenses.get(expense_id)
    if expense is None:
        raise HTTPException(status_code = 404, detail=f"Expense {expense_id} not found!")
    return expense

@app.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: int)->None:
    if expense_id not in expenses:
        raise HTTPException(status_code= 404, detail=f"Expense {expense_id} not found!")
    del expenses[expense_id]


