"""Charging calculations for Smart EV Charging."""

from __future__ import annotations

from .models import ChargingEstimate, ChargingRequest


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
