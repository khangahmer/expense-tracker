import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

RATES_URL = f"{settings.fx_base_url}/latest"


def upstream_ok(rate):
    return httpx.Response(
        200,
        json={"amount": 1.0, "base": "USD", "date": "2026-10-30", "rates": {"EUR": rate}},
    )


def test_convert_applies_rate_and_rounds_half_up(client, create_expense, respx_mock):
    expense = create_expense(amount_minor=1005, currency="USD")
    respx_mock.get(RATES_URL, params={"base": "USD", "symbols": "EUR"}).mock(
        return_value=upstream_ok(0.5)
    )

    response = client.get(f"/expenses/{expense['id']}/converted", params={"to": "EUR"})

    assert response.status_code == 200
    body = response.json()
    assert body["rate"] == "0.5"
    assert body["converted_amount_minor"] == 503  # 502.5 rounds UP to 503


def test_convert_same_currency_makes_no_external_call(client, create_expense, respx_mock):
    expense = create_expense(currency="USD")

    response = client.get(f"/expenses/{expense['id']}/converted", params={"to": "USD"})

    assert response.status_code == 200
    assert response.json()["rate"] == "1"
    assert len(respx_mock.calls) == 0


@pytest.mark.parametrize(
    ("upstream", "expected_status", "expected_code"),
    [
        (httpx.Response(404, json={"message": "not found"}), 422, "unsupported_currency"),
        (httpx.Response(500, text="boom"), 502, "upstream_error"),
        (httpx.Response(200, json={"unexpected": True}), 502, "upstream_bad_response"),
        (httpx.ConnectTimeout("too slow"), 504, "upstream_timeout"),
        (httpx.ConnectError("refused"), 502, "upstream_unavailable"),
    ],
)
def test_convert_maps_upstream_failures(
    client, create_expense, respx_mock, upstream, expected_status, expected_code
):
    expense = create_expense(currency="USD")
    route = respx_mock.get(RATES_URL)
    if isinstance(upstream, Exception):
        route.mock(side_effect=upstream)
    else:
        route.mock(return_value=upstream)

    response = client.get(f"/expenses/{expense['id']}/converted", params={"to": "EUR"})

    assert response.status_code == expected_status
    assert response.json()["error"]["code"] == expected_code


def test_unexpected_error_returns_generic_500(create_expense, monkeypatch):
    expense = create_expense(currency="USD")

    async def explode(base, target):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr("app.main.fetch_rate", explode)
    # Behave like a real server: respond with 500 instead of re-raising into the test.
    quiet_client = TestClient(app, raise_server_exceptions=False)

    response = quiet_client.get(f"/expenses/{expense['id']}/converted", params={"to": "EUR"})

    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "internal_error"
    assert "error_id" in error["details"]
    assert "secret internal detail" not in response.text
