"""Constants for the BajaGas LP price integration."""

from __future__ import annotations

DOMAIN = "bajagas"

CONF_CITY = "city"
CONF_SCAN_INTERVAL = "scan_interval"  # hours

PRICES_URL = "https://bajagas.com/precios"

DEFAULT_CITY = "Tijuana"
DEFAULT_SCAN_INTERVAL = 24  # hours (BajaGas publishes a daily price)
MIN_SCAN_INTERVAL = 1
MAX_SCAN_INTERVAL = 168

CURRENCY = "MXN"
UNIT_PRICE = "MXN/L"
MANUFACTURER = "BajaGas"

STORAGE_VERSION = 1
HISTORY_CAP = 400  # stored price-change entries kept
RECENT_HISTORY = 30  # entries exposed in the sensor attribute
