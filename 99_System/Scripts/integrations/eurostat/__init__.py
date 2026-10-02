"""Eurostat integration package.

Provides automated fetching of official European macroeconomic indicators,
including sovereign 10-year benchmark yields (Maastricht criterion) and
harmonized consumer price inflation (HICP).
"""

from .macro_supplier import EurostatMacroSupplier

__all__ = ["EurostatMacroSupplier"]
