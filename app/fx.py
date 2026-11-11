import logging
from decimal import Decimal

import httpx

from app.config import settings
from app.errors import AppError

logger = logging.getLogger("expense_tracker")


async def fetch_rate(base: str, target: str) -> Decimal:
    if base == target:
        return Decimal(1)
    try:
        async with httpx.AsyncClient(
            base_url=settings.fx_base_url, timeout=settings.fx_timeout_seconds
        ) as client:
            response = await client.get("/latest", params={"base": base, "symbols": target})
    except httpx.TimeoutException as exc:
        logger.error("exchange-rate service timed out: %r", exc)
        raise AppError(504, "upstream_timeout", "The exchange-rate service timed out") from exc
    except httpx.RequestError as exc:
        logger.error("exchange-rate service unreachable: %r", exc)
        raise AppError(
            502, "upstream_unavailable", "The exchange-rate service is unreachable"
        ) from exc

    if response.status_code in (404, 422):
        raise AppError(422, "unsupported_currency", f"Cannot convert {base} to {target}")
    if response.status_code != 200:
        logger.error(
            "exchange-rate service returned %s: %s",
            response.status_code,
            response.text[:200],
        )
        raise AppError(502, "upstream_error", "The exchange-rate service returned an error")
    try:
        return Decimal(str(response.json()["rates"][target]))
    except (ValueError, KeyError, TypeError) as exc:
        logger.error("unexpected exchange-rate response: %s", response.text[:200])
        raise AppError(
            502, "upstream_bad_response", "The exchange-rate service sent bad data"
        ) from exc
