"""Coordinator: scrapes the BajaGas price page daily, keeps a local Store, charts via statistics."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
import logging
from typing import Any

import aiohttp

from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util, slugify

from .const import (
    CONF_CITY,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    HISTORY_CAP,
    PRICES_URL,
    RECENT_HISTORY,
    STORAGE_VERSION,
    UNIT_PRICE,
)
from .scraper import PriceParseError, parse_prices

_LOGGER = logging.getLogger(__name__)

FETCH_TIMEOUT = 30  # seconds

type BajaGasConfigEntry = ConfigEntry[BajaGasCoordinator]


async def async_fetch_prices(hass: HomeAssistant, url: str = PRICES_URL) -> dict[str, float]:
    """Fetch the BajaGas precios page and parse the per-liter prices by city."""
    session = async_get_clientsession(hass)
    async with session.get(
        url, timeout=aiohttp.ClientTimeout(total=FETCH_TIMEOUT)
    ) as response:
        response.raise_for_status()
        html = await response.text()
    return parse_prices(html)


@dataclass
class BajaGasData:
    """Everything the entities read."""

    city: str
    price: float | None = None
    all_prices: dict[str, float] = field(default_factory=dict)
    updated: datetime | None = None
    previous: float | None = None
    change: float | None = None
    history: list[dict[str, Any]] = field(default_factory=list)


class BajaGasCoordinator(DataUpdateCoordinator[BajaGasData]):
    """Scrapes the selected city's LP price; serves stored data when the page is down."""

    config_entry: BajaGasConfigEntry

    def __init__(self, hass: HomeAssistant, entry: BajaGasConfigEntry) -> None:
        """Set up the coordinator for one city."""
        hours = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        self.city: str = entry.data[CONF_CITY]
        self.city_slug: str = slugify(self.city)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {self.city}",
            update_interval=timedelta(hours=hours),
        )
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self._price: float | None = None
        self._all_prices: dict[str, float] = {}
        self._previous: float | None = None
        self._updated: datetime | None = None
        self._history: list[dict[str, Any]] = []
        self._last_stat_date: str | None = None

    async def async_load_store(self) -> bool:
        """Load stored prices and publish them at once. True if a price was stored."""
        stored = await self._store.async_load()
        if not stored or stored.get("price") is None:
            return False
        self._price = stored.get("price")
        self._all_prices = {
            str(k): float(v) for k, v in (stored.get("all_prices") or {}).items()
        }
        self._previous = stored.get("previous")
        self._updated = _parse_dt(stored.get("updated"))
        self._history = list(stored.get("history") or [])
        self._last_stat_date = stored.get("last_stat_date")
        self.async_set_updated_data(self._snapshot())
        return True

    def _snapshot(self) -> BajaGasData:
        change = (
            round(self._price - self._previous, 4)
            if self._price is not None and self._previous is not None
            else None
        )
        return BajaGasData(
            city=self.city,
            price=self._price,
            all_prices=dict(self._all_prices),
            updated=self._updated,
            previous=self._previous,
            change=change,
            history=list(self._history[-RECENT_HISTORY:]),
        )

    async def _async_save(self) -> None:
        await self._store.async_save(
            {
                "city": self.city,
                "price": self._price,
                "all_prices": self._all_prices,
                "previous": self._previous,
                "updated": self._updated.isoformat() if self._updated else None,
                "history": self._history,
                "last_stat_date": self._last_stat_date,
            }
        )

    async def _async_update_data(self) -> BajaGasData:
        try:
            prices = await async_fetch_prices(self.hass)
        except PriceParseError as err:
            raise UpdateFailed(f"BajaGas price page unreadable: {err}") from err
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise UpdateFailed(f"BajaGas price page unavailable: {err}") from err

        now = dt_util.now()
        self._all_prices = prices
        self._updated = now
        if self.city in prices:
            new_price = prices[self.city]
            if self._price is None or new_price != self._price:
                self._previous = self._price
                self._price = new_price
                self._history.append({"date": now.date().isoformat(), "price": new_price})
                if len(self._history) > HISTORY_CAP:
                    self._history = self._history[-HISTORY_CAP:]
        else:
            _LOGGER.warning(
                "City %s missing from this BajaGas poll; keeping the last price", self.city
            )
        await self._async_save()
        self._async_import_statistics(now)
        return self._snapshot()

    def _async_import_statistics(self, now: datetime) -> None:
        """Write one daily mean point per recorded price into long-term statistics."""
        if not self._history:
            return
        today = now.date().isoformat()
        if self._last_stat_date == today:
            return  # already imported today
        tz = dt_util.get_default_time_zone()
        points: list[StatisticData] = []
        for entry in self._history:
            try:
                day = datetime.fromisoformat(str(entry["date"])).date()
                price = float(entry["price"])
            except (KeyError, TypeError, ValueError):
                continue
            start = datetime.combine(day, time(0), tzinfo=tz)
            points.append(StatisticData(start=start, mean=price, min=price, max=price))
        if not points:
            return
        async_add_external_statistics(
            self.hass,
            StatisticMetaData(
                mean_type=StatisticMeanType.ARITHMETIC,
                has_sum=False,
                name=f"BajaGas {self.city} LP price",
                source=DOMAIN,
                statistic_id=f"{DOMAIN}:{self.city_slug}_price",
                unit_class=None,
                unit_of_measurement=UNIT_PRICE,
            ),
            points,
        )
        self._last_stat_date = today


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None
