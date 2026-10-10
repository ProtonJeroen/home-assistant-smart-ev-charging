"""Charging calculations for Smart EV Charging."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math

from .models import (
    ChargingEstimate,
    ChargingPlan,
    ChargingRequest,
    PlannedChargeSlot,
    PriceSlot,
)


def calculate_charging_estimate(request: ChargingRequest) -> ChargingEstimate:
    """Calculate energy from the battery, energy from the grid and charge time."""
    if not 0 <= request.current_soc <= 100:
        raise ValueError("current_soc must be between 0 and 100")
    if not 0 <= request.target_soc <= 100:
        raise ValueError("target_soc must be between 0 and 100")
    if request.usable_capacity_kwh <= 0:
        raise ValueError("usable_capacity_kwh must be greater than zero")
    if request.charge_power_kw <= 0:
        raise ValueError("charge_power_kw must be greater than zero")
    if not 0 < request.efficiency <= 1:
        raise ValueError("efficiency must be greater than 0 and at most 1")

    if request.target_soc <= request.current_soc:
        return ChargingEstimate(
            battery_energy_kwh=0.0,
            grid_energy_kwh=0.0,
            duration_minutes=0.0,
        )

    soc_delta = (request.target_soc - request.current_soc) / 100.0
    battery_energy_kwh = request.usable_capacity_kwh * soc_delta
    grid_energy_kwh = battery_energy_kwh / request.efficiency
    duration_minutes = (grid_energy_kwh / request.charge_power_kw) * 60.0

    return ChargingEstimate(
        battery_energy_kwh=battery_energy_kwh,
        grid_energy_kwh=grid_energy_kwh,
        duration_minutes=duration_minutes,
    )


def _price_coverage_complete(
    price_slots: tuple[PriceSlot, ...],
    window_start: datetime,
    window_end: datetime,
) -> bool:
    """Return whether price slots continuously cover the planning window."""
    if window_end <= window_start:
        return True

    tolerance = timedelta(seconds=60)
    cursor = window_start

    for slot in price_slots:
        start = max(slot.start, window_start)
        end = min(slot.end, window_end)

        if end <= cursor or end <= start:
            continue

        if start > cursor + tolerance:
            return False

        cursor = max(cursor, end)
        if cursor >= window_end - tolerance:
            return True

    return cursor >= window_end - tolerance


def calculate_smart_plan(
    price_slots: tuple[PriceSlot, ...],
    window_start: datetime,
    window_end: datetime,
    required_minutes: float,
    charge_power_kw: float,
) -> ChargingPlan:
    """Select the cheapest available price intervals before the deadline.

    Slots do not need to be contiguous. The final selected slot may be used
    only partially, allowing the plan duration to match the calculated charge
    requirement rather than always rounding up to a complete quarter hour.
    """
    if charge_power_kw <= 0:
        raise ValueError("charge_power_kw must be greater than zero")
    if required_minutes < 0:
        raise ValueError("required_minutes must not be negative")

    coverage_complete = _price_coverage_complete(
        price_slots, window_start, window_end
    )

    if required_minutes == 0:
        return ChargingPlan(
            slots=(),
            required_minutes=0.0,
            planned_minutes=0.0,
            estimated_cost=0.0,
            average_price=None,
            coverage_complete=coverage_complete,
        )

    available: list[tuple[datetime, datetime, float]] = []

    for slot in price_slots:
        start = max(slot.start, window_start)
        end = min(slot.end, window_end)
        if end > start:
            available.append((start, end, slot.price))

    available.sort(key=lambda item: (item[2], item[0]))

    remaining_minutes = required_minutes
    selected: list[PlannedChargeSlot] = []

    for start, end, price in available:
        if remaining_minutes <= 0:
            break

        available_minutes = (end - start).total_seconds() / 60.0
        selected_minutes = min(available_minutes, remaining_minutes)
        selected_end = start + timedelta(minutes=selected_minutes)
        energy_kwh = charge_power_kw * selected_minutes / 60.0
        cost = energy_kwh * price

        selected.append(
            PlannedChargeSlot(
                start=start,
                end=selected_end,
                price=price,
                minutes=selected_minutes,
                energy_kwh=energy_kwh,
                cost=cost,
            )
        )
        remaining_minutes -= selected_minutes

    selected.sort(key=lambda slot: slot.start)

    planned_minutes = sum(slot.minutes for slot in selected)
    total_energy_kwh = sum(slot.energy_kwh for slot in selected)
    estimated_cost = sum(slot.cost for slot in selected)
    average_price = (
        estimated_cost / total_energy_kwh if total_energy_kwh > 0 else None
    )

    return ChargingPlan(
        slots=tuple(selected),
        required_minutes=required_minutes,
        planned_minutes=planned_minutes,
        estimated_cost=estimated_cost,
        average_price=average_price,
        coverage_complete=coverage_complete,
    )


def calculate_rolling_plan(
    price_slots: tuple[PriceSlot, ...],
    now: datetime,
    cheap_hours: float,
    required_minutes: float,
    charge_power_kw: float,
) -> ChargingPlan:
    """Choose up to N cheap hours in the next 24 elapsed hours.

    The allowance is a cap per recalculation, not a daily charging quota.
    SOC requirements can shorten it; no deadline fallback extends it.
    UTC arithmetic keeps the horizon and slot durations correct across DST.
    """
    if not math.isfinite(cheap_hours) or not 0.25 <= cheap_hours <= 24:
        raise ValueError("cheap_hours must be between 0.25 and 24")
    if not math.isfinite(required_minutes) or required_minutes < 0:
        raise ValueError("required_minutes must be finite and nonnegative")
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    start = now.astimezone(timezone.utc)
    slots = tuple(
        PriceSlot(
            slot.start.astimezone(timezone.utc),
            slot.end.astimezone(timezone.utc),
            slot.price,
        )
        for slot in price_slots
    )
    return calculate_smart_plan(
        slots, start, start + timedelta(hours=24),
        min(required_minutes, cheap_hours * 60), charge_power_kw,
    )
