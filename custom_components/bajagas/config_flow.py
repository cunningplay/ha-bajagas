"""Config and options flows for BajaGas (pick a city, set the poll interval)."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_CITY,
    CONF_SCAN_INTERVAL,
    DEFAULT_CITY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .coordinator import BajaGasConfigEntry, async_fetch_prices
from .scraper import PriceParseError

_LOGGER = logging.getLogger(__name__)


class BajaGasConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up the BajaGas price for one city."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Fetch the city list and present a dropdown (Tijuana suggested)."""
        try:
            prices = await async_fetch_prices(self.hass)
        except (PriceParseError, aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.debug("BajaGas price page check failed: %s", err)
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({}),
                errors={"base": "cannot_connect"},
            )

        cities = sorted(prices, key=str.lower)
        if user_input is not None:
            city = user_input[CONF_CITY]
            await self.async_set_unique_id(city)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"BajaGas {city}", data={CONF_CITY: city}
            )

        default = DEFAULT_CITY if DEFAULT_CITY in cities else cities[0]
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CITY, default=default): SelectSelector(
                        SelectSelectorConfig(
                            options=cities,
                            mode=SelectSelectorMode.DROPDOWN,
                            sort=False,
                        )
                    )
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: BajaGasConfigEntry) -> BajaGasOptionsFlow:
        """Options: polling interval."""
        return BajaGasOptionsFlow()


class BajaGasOptionsFlow(OptionsFlowWithReload):
    """Change how often the price is checked."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Polling interval in hours."""
        if user_input is not None:
            return self.async_create_entry(
                data={CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])}
            )
        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="h",
                        )
                    )
                }
            ),
        )
