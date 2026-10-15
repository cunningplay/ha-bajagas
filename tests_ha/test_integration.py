"""Home Assistant integration tests: config flow, polling, Store restore, statistics."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bajagas.const import DOMAIN
from custom_components.bajagas.scraper import PriceParseError, parse_prices

HTML = (
    Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "precios.html"
).read_text(encoding="utf-8")
PRICES = parse_prices(HTML)
CITY = "Tijuana"
STAT_ID = "bajagas:tijuana_price"

FETCH_CO = "custom_components.bajagas.coordinator.async_fetch_prices"
FETCH_CF = "custom_components.bajagas.config_flow.async_fetch_prices"


def entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN, data={"city": CITY}, unique_id=CITY, title=f"BajaGas {CITY}"
    )


def entity_ids(hass: HomeAssistant, e: MockConfigEntry) -> dict[str, str]:
    reg = er.async_get(hass)
    return {
        x.translation_key: x.entity_id
        for x in er.async_entries_for_config_entry(reg, e.entry_id)
    }


async def get_stats(hass: HomeAssistant) -> dict:
    from homeassistant.components.recorder import get_instance
    from homeassistant.components.recorder.statistics import statistics_during_period

    await hass.async_block_till_done()
    await get_instance(hass).async_block_till_done()
    return await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        None,
        {STAT_ID},
        "day",
        None,
        {"mean"},
    )


async def test_config_flow_city_dropdown(hass: HomeAssistant) -> None:
    with patch(FETCH_CF, return_value=PRICES), patch(FETCH_CO, return_value=PRICES):
        r = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        assert r["type"] is FlowResultType.FORM
        # the city dropdown offers all 17 cities and suggests Tijuana
        key = next(k for k in r["data_schema"].schema if str(k) == "city")
        selector = r["data_schema"].schema[key]
        options = selector.config["options"]
        assert len(options) == 17 and CITY in options
        assert key.default() == CITY

        r2 = await hass.config_entries.flow.async_configure(
            r["flow_id"], {"city": CITY}
        )
        await hass.async_block_till_done()
    assert r2["type"] is FlowResultType.CREATE_ENTRY
    assert r2["data"] == {"city": CITY}
    assert r2["result"].unique_id == CITY


async def test_config_flow_cannot_connect(hass: HomeAssistant) -> None:
    with patch(FETCH_CF, side_effect=PriceParseError("garbage")):
        r = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert r["type"] is FlowResultType.FORM
    assert r["errors"] == {"base": "cannot_connect"}


async def test_poll_sets_price_and_statistic(
    hass: HomeAssistant, freezer, hass_storage
) -> None:
    freezer.move_to("2026-10-14 12:00:00")
    e = entry()
    e.add_to_hass(hass)
    with patch(FETCH_CO, return_value=PRICES):
        assert await hass.config_entries.async_setup(e.entry_id)
        await hass.async_block_till_done()
    assert e.state is ConfigEntryState.LOADED

    ids = entity_ids(hass, e)
    st = hass.states.get(ids["price"])
    assert st.state == "10.96"
    assert st.attributes["unit_of_measurement"] == "MXN/L"
    assert st.attributes["state_class"] == "measurement"
    assert st.attributes["all_prices"]["Tijuana"] == 10.96
    assert st.attributes["history"][-1]["price"] == 10.96

    # the stored history grew and the price is persisted
    stored = hass_storage[f"{DOMAIN}.{e.entry_id}"]["data"]
    assert stored["price"] == 10.96
    assert stored["history"][-1] == {"date": "2026-10-14", "price": 10.96}

    # a bajagas:tijuana_price statistic row was written at the current price
    stats = await get_stats(hass)
    rows = stats[STAT_ID]
    assert rows and rows[0]["mean"] == 10.96


async def test_restore_last_value_on_fetch_failure(
    hass: HomeAssistant, freezer, hass_storage
) -> None:
    freezer.move_to("2026-10-14 12:00:00")
    e = entry()
    e.add_to_hass(hass)
    hass_storage[f"{DOMAIN}.{e.entry_id}"] = {
        "version": 1,
        "minor_version": 1,
        "key": f"{DOMAIN}.{e.entry_id}",
        "data": {
            "city": CITY,
            "price": 11.5,
            "all_prices": {CITY: 11.5, "Ensenada": 10.77},
            "previous": 11.0,
            "updated": "2026-10-13T12:00:00+00:00",
            "history": [{"date": "2026-10-13", "price": 11.5}],
            "last_stat_date": "2026-10-13",
        },
    }
    with patch(FETCH_CO, side_effect=PriceParseError("page down")):
        assert await hass.config_entries.async_setup(e.entry_id)
        await hass.async_block_till_done()
    # entry stays loaded on the stored value even though the first scrape failed
    assert e.state is ConfigEntryState.LOADED
    assert not e.runtime_data.last_update_success
    st = hass.states.get(entity_ids(hass, e)["price"])
    assert st.state == "11.5"
    assert st.attributes["previous"] == 11.0
    assert st.attributes["change"] == 0.5


async def test_missing_city_keeps_last_value(
    hass: HomeAssistant, freezer, caplog
) -> None:
    freezer.move_to("2026-10-14 12:00:00")
    e = entry()
    e.add_to_hass(hass)
    with patch(FETCH_CO, return_value=PRICES):
        assert await hass.config_entries.async_setup(e.entry_id)
        await hass.async_block_till_done()
    # next poll: the selected city is gone from the page
    without_city = {k: v for k, v in PRICES.items() if k != CITY}
    with patch(FETCH_CO, return_value=without_city):
        await e.runtime_data.async_refresh()
        await hass.async_block_till_done()
    st = hass.states.get(entity_ids(hass, e)["price"])
    assert st.state == "10.96"  # last known value kept
    assert "missing from this BajaGas poll" in caplog.text


async def test_options_interval(hass: HomeAssistant) -> None:
    from datetime import timedelta

    e = entry()
    e.add_to_hass(hass)
    with patch(FETCH_CO, return_value=PRICES):
        assert await hass.config_entries.async_setup(e.entry_id)
        await hass.async_block_till_done()
        r = await hass.config_entries.options.async_init(e.entry_id)
        r = await hass.config_entries.options.async_configure(
            r["flow_id"], {"scan_interval": 12}
        )
        await hass.async_block_till_done()
    assert e.options == {"scan_interval": 12}
    assert e.runtime_data.update_interval == timedelta(hours=12)


async def test_remove_entry_deletes_store(
    hass: HomeAssistant, hass_storage
) -> None:
    e = entry()
    e.add_to_hass(hass)
    with patch(FETCH_CO, return_value=PRICES):
        assert await hass.config_entries.async_setup(e.entry_id)
        await hass.async_block_till_done()
    assert f"{DOMAIN}.{e.entry_id}" in hass_storage
    await hass.config_entries.async_remove(e.entry_id)
    await hass.async_block_till_done()
    assert f"{DOMAIN}.{e.entry_id}" not in hass_storage
