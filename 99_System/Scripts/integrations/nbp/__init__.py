"""NBP (Narodowy Bank Polski) integration package.

Provides automated fetching of official exchange rates (Table A fixing),
domestic gold price fixing, and monetary policy base interest rates (RPP decisions).
"""

from .macro_supplier import NBPMacroSupplier

__all__ = ["NBPMacroSupplier"]
