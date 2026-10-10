"""Data models for Smart EV Charging."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ChargingRequest:
    """Input required for a basic charging estimate."""

    current_soc: float
    target_soc: float
    usable_capacity_kwh: float
    charge_power_kw: float
    efficiency: float


@dataclass(frozen=True, slots=True)
class ChargingEstimate:
    """Calculated energy and time required for charging."""

    battery_energy_kwh: float
    grid_energy_kwh: float
    duration_minutes: float


@dataclass(frozen=True, slots=True)
class PriceSlot:
    """One energy-price interval."""

    start: datetime
    end: datetime
    price: float


@dataclass(frozen=True, slots=True)
class PlannedChargeSlot:
    """A selected part of a price slot used by the charging plan."""

    start: datetime
    end: datetime
    price: float
    minutes: float
    energy_kwh: float
    cost: float


@dataclass(frozen=True, slots=True)
class ChargingPlan:
    """Price-optimized charge plan."""

    slots: tuple[PlannedChargeSlot, ...]
    required_minutes: float
    planned_minutes: float
    estimated_cost: float
    average_price: float | None
    coverage_complete: bool
