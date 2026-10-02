"""Vault Patch & Update System.

Provides automated sequential version patching from the upstream template starter
into downstream user vaults while strictly preserving personal investment data.
"""

from .patch_engine import PatchEngine, get_vault_version, run_patch

__all__ = ["PatchEngine", "get_vault_version", "run_patch"]
