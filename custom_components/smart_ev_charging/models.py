"""Data models for Smart EV Charging."""

from __future__ import annotations

from dataclasses import dataclass


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
