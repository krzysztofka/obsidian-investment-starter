"""Platforms package registering all supported platform extensions."""

from .base import BasePlatform, PlatformRegistry
from .common import (
    determine_asset_type,
    load_import_config,
    load_template,
    render_template_body,
    save_or_update_asset,
)
from .degiro import DegiroPlatform, import_degiro
from .exante import ExantePlatform, import_exante, import_exante_api
from .mbank_common import import_mbm
from .mbank_ike import MbankIkePlatform, import_mbank_ike, import_mbm_ike
from .mbank_ikze import MbankIkzePlatform, import_mbank_ikze, import_mbm_ikze
from .pko_bp_bonds import PkoBpBondsPlatform, import_pko_bp_bonds, import_pkobp

__all__ = [
    "BasePlatform",
    "PlatformRegistry",
    "PkoBpBondsPlatform",
    "MbankIkePlatform",
    "MbankIkzePlatform",
    "DegiroPlatform",
    "ExantePlatform",
    "determine_asset_type",
    "load_template",
    "render_template_body",
    "save_or_update_asset",
    "load_import_config",
    "import_pko_bp_bonds",
    "import_pkobp",
    "import_mbank_ike",
    "import_mbm_ike",
    "import_mbank_ikze",
    "import_mbm_ikze",
    "import_mbm",
    "import_degiro",
    "import_exante",
    "import_exante_api",
]
