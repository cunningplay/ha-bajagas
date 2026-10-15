"""Tests for the BajaGas price scraper (real precios.html fixture)."""

from __future__ import annotations

import pytest

from conftest import bajagas_scraper

parse_prices = bajagas_scraper.parse_prices
PriceParseError = bajagas_scraper.PriceParseError

# One small per-liter table (two cities), reused in several cases.
LITER_TABLE = """
<table class="customers2"><tbody>
  <tr><td>Tijuana</td><td>$10.96 </td></tr>
  <tr><td>Ensenada</td><td>$10.77 </td></tr>
</tbody></table>
"""


def test_tijuana_price(precios_html: str) -> None:
    prices = parse_prices(precios_html)
    assert prices["Tijuana"] == 10.96


def test_all_17_cities(precios_html: str) -> None:
    prices = parse_prices(precios_html)
    assert len(prices) == 17
    # a spread of the real values, incl. accented city names
    assert prices["Ensenada"] == 10.77
    assert prices["La Paz"] == 12.67
    assert prices["Juárez"] == 10.34
    assert prices["Los Cabos"] == 13.0
    assert prices["Comondú"] == 13.11


def test_picks_first_table_not_cylinders(precios_html: str) -> None:
    """Tijuana must be the per-liter price (10.96), never the 10 Kg table (202.90)."""
    prices = parse_prices(precios_html)
    assert prices["Tijuana"] == 10.96
    # every per-liter value stays small; no cylinder price leaks in
    assert all(value < 50 for value in prices.values())
    assert max(prices.values()) < 14


def test_row_reorder_robust() -> None:
    reordered = """
    <table class="customers2"><tbody>
      <tr><td>Ensenada</td><td>$10.77 </td></tr>
      <tr><td>Tijuana</td><td>$10.96 </td></tr>
    </tbody></table>
    """
    assert parse_prices(reordered) == {"Ensenada": 10.77, "Tijuana": 10.96}


def test_only_first_table_is_read() -> None:
    """A later customers2 table (cylinder prices) is ignored entirely."""
    html = (
        LITER_TABLE
        + '<table class="customers2"><tr><td>Tijuana</td><td>$202.90 </td></tr></table>'
    )
    prices = parse_prices(html)
    assert prices == {"Tijuana": 10.96, "Ensenada": 10.77}


def test_missing_city_omitted() -> None:
    """A row with an unreadable price is skipped; others are kept."""
    html = """
    <table class="customers2"><tbody>
      <tr><td>Tijuana</td><td>$10.96 </td></tr>
      <tr><td>Rosarito</td><td> </td></tr>
      <tr><td></td><td>$9.99 </td></tr>
    </tbody></table>
    """
    prices = parse_prices(html)
    assert prices == {"Tijuana": 10.96}
    assert "Rosarito" not in prices


def test_garbage_page_raises() -> None:
    with pytest.raises(PriceParseError):
        parse_prices("<html><body><p>no prices here</p></body></html>")


def test_empty_page_raises() -> None:
    with pytest.raises(PriceParseError):
        parse_prices("")


def test_cylinder_only_page_raises() -> None:
    """If the first table somehow held cylinder prices, the guard rejects it."""
    html = '<table class="customers2"><tr><td>Tijuana</td><td>$202.90 </td></tr></table>'
    with pytest.raises(PriceParseError):
        parse_prices(html)
