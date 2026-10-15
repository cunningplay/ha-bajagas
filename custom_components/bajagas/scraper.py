"""Parse BajaGas per-liter LP prices from the precios page.

Pure module: standard library only, no Home Assistant imports, so it can be
unit-tested on its own. The page at https://bajagas.com/precios has FIVE
``<table class="customers2">`` tables: the first is the per-liter price
(Tijuana ~$10.96/L), the rest are fixed cylinder/tank sizes ($191, $574,
$861, $42 ranges). Only the FIRST table is parsed, keyed by city name so a
reordering of the rows does not matter.
"""

from __future__ import annotations

from html.parser import HTMLParser

# The per-liter table is all small values (~$10-13); the cylinder/tank tables
# are in the hundreds. A row at or above this never belongs to the liter table,
# so it guards against silently reading the wrong table.
MAX_PRICE_PER_LITER = 50.0


class PriceParseError(Exception):
    """The page has no usable per-liter price table."""


class _FirstTableParser(HTMLParser):
    """Collect the cells of the first ``<table class="customers2">``."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_table = False  # inside the chosen table
        self._done = False  # the first customers2 table has been read
        self._nested = 0  # depth of nested tables inside the chosen one
        self._in_cell = False
        self._cell = ""
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._done:
            return
        if tag == "table":
            if not self._in_table:
                classes = (dict(attrs).get("class") or "").split()
                if "customers2" in classes:
                    self._in_table = True
            else:
                self._nested += 1
        elif self._in_table:
            if tag == "tr":
                self.rows.append([])
            elif tag == "td":
                self._in_cell = True
                self._cell = ""

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell += data

    def handle_endtag(self, tag: str) -> None:
        if self._done or not self._in_table:
            return
        if tag == "td" and self._in_cell:
            self._in_cell = False
            if self.rows:
                self.rows[-1].append(self._cell.strip())
        elif tag == "table":
            if self._nested:
                self._nested -= 1
            else:
                self._in_table = False
                self._done = True


def _price(text: str) -> float | None:
    """A price cell (``$10.96 ``) as a float, or None when it is not a number."""
    cleaned = text.replace("$", "").replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_prices(html: str) -> dict[str, float]:
    """Per-liter LP price by city from the BajaGas precios page.

    Returns ``{city: price_float}`` built only from the first ``customers2``
    table. A row with a missing city or an unreadable price is skipped. A page
    with no usable rows, or whose first table looks like a cylinder table
    (any value >= MAX_PRICE_PER_LITER), raises ``PriceParseError``.
    """
    parser = _FirstTableParser()
    parser.feed(html)
    prices: dict[str, float] = {}
    for row in parser.rows:
        if len(row) < 2:
            continue
        city = row[0].strip()
        price = _price(row[1])
        if not city or price is None:
            continue
        prices[city] = price
    if not prices:
        raise PriceParseError("no per-liter price rows found")
    if any(price >= MAX_PRICE_PER_LITER for price in prices.values()):
        raise PriceParseError(
            "the first customers2 table does not look like per-liter prices"
        )
    return prices
