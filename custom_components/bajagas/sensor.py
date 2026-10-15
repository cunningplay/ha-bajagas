"""The current BajaGas LP price sensor."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import UNIT_PRICE
from .coordinator import BajaGasConfigEntry, BajaGasCoordinator
from .entity import BajaGasEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BajaGasConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the price sensor."""
    async_add_entities([BajaGasPriceSensor(entry.runtime_data)])


class BajaGasPriceSensor(BajaGasEntity, SensorEntity):
    """The selected city's current per-liter LP price (MXN/L)."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UNIT_PRICE
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: BajaGasCoordinator) -> None:
        """Create the price sensor."""
        super().__init__(coordinator, "price")

    @property
    def native_value(self) -> float | None:
        """Current MXN/L price."""
        data = self.coordinator.data
        return data.price if data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """All cities' prices and the recent history."""
        data = self.coordinator.data
        if data is None:
            return None
        return {
            "all_prices": data.all_prices,
            "updated": data.updated,
            "previous": data.previous,
            "change": data.change,
            "history": data.history,
        }
