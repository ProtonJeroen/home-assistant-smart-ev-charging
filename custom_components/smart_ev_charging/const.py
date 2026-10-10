"""Constants for Smart EV Charging."""

from homeassistant.const import Platform

DOMAIN = "smart_ev_charging"
NAME = "Smart EV Charging"

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.DATETIME,
]

CONF_NAME = "name"
CONF_SOC_ENTITY = "soc_entity"
CONF_BATTERY_CAPACITY_KWH = "battery_capacity_kwh"
CONF_PRICE_ENTITY = "price_entity"

CONF_TARGET_SOC = "target_soc"
CONF_CHARGE_POWER_KW = "charge_power_kw"
CONF_CHARGE_EFFICIENCY = "charge_efficiency"
CONF_DEPARTURE = "departure"
CONF_SAFETY_MARGIN_MINUTES = "safety_margin_minutes"
CONF_CHARGING_MODE = "charging_mode"

MODE_OFF = "off"
MODE_CHARGE_NOW = "charge_now"
MODE_SMART = "smart"
MODE_READY_BY_DEPARTURE = "ready_by_departure"

CHARGING_MODES = [
    MODE_OFF,
    MODE_CHARGE_NOW,
    MODE_SMART,
    MODE_READY_BY_DEPARTURE,
]

STATUS_OFF = "off"
STATUS_TARGET_REACHED = "target_reached"
STATUS_VEHICLE_DATA_UNAVAILABLE = "vehicle_data_unavailable"
STATUS_DEPARTURE_NOT_SET = "departure_not_set"
STATUS_CHARGE_NOW = "charge_now"
STATUS_PRICE_SOURCE_NOT_CONFIGURED = "price_source_not_configured"
STATUS_WAITING_FOR_PRICE_DATA = "waiting_for_price_data"
STATUS_WAITING_FOR_SMART_SLOT = "waiting_for_smart_slot"
STATUS_SMART_CHARGE_SLOT = "smart_charge_slot"
STATUS_WAITING_FOR_LATEST_START = "waiting_for_latest_start"
STATUS_MUST_CHARGE_DEADLINE = "must_charge_deadline"

CHARGING_STATUSES = [
    STATUS_OFF,
    STATUS_TARGET_REACHED,
    STATUS_VEHICLE_DATA_UNAVAILABLE,
    STATUS_DEPARTURE_NOT_SET,
    STATUS_CHARGE_NOW,
    STATUS_PRICE_SOURCE_NOT_CONFIGURED,
    STATUS_WAITING_FOR_PRICE_DATA,
    STATUS_WAITING_FOR_SMART_SLOT,
    STATUS_SMART_CHARGE_SLOT,
    STATUS_WAITING_FOR_LATEST_START,
    STATUS_MUST_CHARGE_DEADLINE,
]

DEFAULT_NAME = "EV"
DEFAULT_TARGET_SOC = 80.0
DEFAULT_CHARGE_POWER_KW = 6.6
DEFAULT_CHARGE_EFFICIENCY = 92.0
DEFAULT_SAFETY_MARGIN_MINUTES = 20.0
DEFAULT_CHARGING_MODE = MODE_OFF

PRICE_ATTRIBUTE = "prices"
PRICE_KEY_FROM = "from"
PRICE_KEY_TILL = "till"
PRICE_KEY_PRICE = "price"
