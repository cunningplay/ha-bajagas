"""Base entity for the BajaGas integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import BajaGasCoordinator


class BajaGasEntity(CoordinatorEntity[BajaGasCoordinator]):
    """One device per city; stays available while a stored price exists."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: BajaGasCoordinator, key: str) -> None:
        """Attach the entity to the city's device."""
        super().__init__(coordinator)
        self._attr_translation_key = key
        self._attr_unique_id = f"{coordinator.city_slug}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.city_slug)},
            name=f"BajaGas {coordinator.city}",
            manufacturer=MANUFACTURER,
            model="LP price",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def available(self) -> bool:
        """Available whenever there is a price, even if the page is down."""
        return self.coordinator.data is not None and self.coordinator.data.price is not None
