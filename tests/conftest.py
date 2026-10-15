"""Load the pure scraper module without importing Home Assistant."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = ROOT / "custom_components" / "bajagas"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


bajagas_scraper = _load("bajagas_scraper", PACKAGE_DIR / "scraper.py")


@pytest.fixture
def precios_html() -> str:
    return (FIXTURES / "precios.html").read_text(encoding="utf-8")
