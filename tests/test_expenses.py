import pytest
from sqlalchemy.exc import OperationalError

from app.main import app, get_db


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_then_get_expense(client):
    created = client.post(
        "/expenses",
        json={"description": "Lunch", "amount_minor": 45050, "category": "food"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["id"] == 1
    assert body["currency"] == "USD"
    assert "created_at" in body

    fetched = client.get(f"/expenses/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


def test_get_missing_expense_returns_404(client):
    response = client.get("/expenses/999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize(
    "payload",
    [
        {"description": "", "amount_minor": 100},
        {"description": "   ", "amount_minor": 100},
        {"description": "ok", "amount_minor": 0},
        {"description": "ok", "amount_minor": -5},
        {"description": "ok", "amount_minor": "abc"},
        {"amount_minor": 100},
        {"description": "ok", "amount_minor": 100, "currency": "usd"},
    ],
)
def test_create_rejects_invalid_payload(client, payload):
    response = client.post("/expenses", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert client.get("/expenses").json() == []  # nothing was saved


def test_list_filters_and_paginates(client, create_expense):
    create_expense(description="Lunch", category="food")
    create_expense(description="Bus", category="transport")
    create_expense(description="Dinner", category="food")

    food = client.get("/expenses", params={"category": "food"}).json()
    assert [e["description"] for e in food] == ["Lunch", "Dinner"]

    page = client.get("/expenses", params={"limit": 1, "offset": 1}).json()
    assert [e["description"] for e in page] == ["Bus"]

    assert client.get("/expenses", params={"limit": 0}).status_code == 422


def test_delete_expense(client, create_expense):
    expense = create_expense()
    assert client.delete(f"/expenses/{expense['id']}").status_code == 204
    assert client.get(f"/expenses/{expense['id']}").status_code == 404
    assert client.delete(f"/expenses/{expense['id']}").status_code == 404


def test_patch_expense(client):
    create_payload = {
        "amount_minor": 1500,
        "currency": "USD",
        "description": "Team lunch",
        "category": "Food",
    }
    create_res = client.post("/expenses", json=create_payload)
    assert create_res.status_code == 201
    created = create_res.json()
    expense_id = created["id"]

    patch_res = client.patch(f"/expenses/{expense_id}", json={"amount_minor": 225000})
    assert patch_res.status_code == 200
    updated = patch_res.json()

    assert updated["id"] == expense_id
    assert updated["amount_minor"] == 225000
    assert updated["currency"] == created["currency"]
    assert updated["description"] == created["description"]
    assert updated["category"] == created["category"]


def test_patch_expense_missing_id_returns_404(client):
    missing_id = 999
    patch_res = client.patch(f"/expenses/{missing_id}", json={"amount_minor": 40000})
    assert patch_res.status_code == 404


def test_patch_expense_null_description_returns_422(client, create_expense):
    expense = create_expense(description="Office Supplies")

    response = client.patch(f"/expenses/{expense['id']}", json={"description": None})
    assert response.status_code == 422


def test_database_down_returns_503(client):
    def broken_db():
        raise OperationalError("SELECT 1", {}, Exception("db down"))

    app.dependency_overrides[get_db] = broken_db
    try:
        response = client.get("/expenses")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "database_unavailable"
    assert "db down" not in response.text
