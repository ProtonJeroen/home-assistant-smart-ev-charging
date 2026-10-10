"""Price-source helpers for Smart EV Charging."""

from __future__ import annotations

from datetime import datetime
from math import isfinite
from typing import Any

from homeassistant.util import dt as dt_util

from .const import PRICE_KEY_FROM, PRICE_KEY_PRICE, PRICE_KEY_TILL
from .models import PriceSlot


def _parse_datetime(value: Any, timezone) -> datetime | None:
    """Parse a Home Assistant price attribute date/time value."""
    parsed: datetime | None

    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = dt_util.parse_datetime(value)
    else:
        return None

    if parsed is None:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone)

    return parsed


def parse_price_slots(raw_prices: Any, timezone) -> tuple[PriceSlot, ...]:
    """Parse generic Home Assistant price attributes.

    The supported format intentionally matches Frank Energie's prices
    attribute and is generic enough for other providers:

    [
        {"from": <datetime>, "till": <datetime>, "price": <number>},
        ...
    ]
    """
    if not isinstance(raw_prices, list):
        return ()

    slots: list[PriceSlot] = []

    for item in raw_prices:
        if not isinstance(item, dict):
            continue

        start = _parse_datetime(item.get(PRICE_KEY_FROM), timezone)
        end = _parse_datetime(item.get(PRICE_KEY_TILL), timezone)

        try:
            price = float(item.get(PRICE_KEY_PRICE))
        except (TypeError, ValueError):
            continue

        if (
            start is None
            or end is None
            or end <= start
            or not isfinite(price)
        ):
            continue

        slots.append(PriceSlot(start=start, end=end, price=price))

    slots.sort(key=lambda slot: slot.start)
    return tuple(slots)
