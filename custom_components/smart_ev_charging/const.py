"""Constants for Smart EV Charging."""

from homeassistant.const import Platform

DOMAIN = "smart_ev_charging"
NAME = "Smart EV Charging"

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.DATETIME,
]

CONF_NAME = "name"
CONF_SOC_ENTITY = "soc_entity"
CONF_BATTERY_CAPACITY_KWH = "battery_capacity_kwh"

CONF_TARGET_SOC = "target_soc"
CONF_CHARGE_POWER_KW = "charge_power_kw"
CONF_CHARGE_EFFICIENCY = "charge_efficiency"
CONF_DEPARTURE = "departure"

DEFAULT_NAME = "EV"
DEFAULT_TARGET_SOC = 80.0
DEFAULT_CHARGE_POWER_KW = 6.6
DEFAULT_CHARGE_EFFICIENCY = 92.0
