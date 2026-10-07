"""Base architecture and registry for platform extensions."""

import os
import re
import sys
from abc import ABC, abstractmethod
from typing import Any

# Ensure scripts directory is on sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_scripts_dir = os.path.dirname(script_dir)
if parent_scripts_dir not in sys.path:
    sys.path.append(parent_scripts_dir)

from model.config import PlatformConfig, load_vault_config


def get_default_base_dir() -> str:
    """Resolve default repository/vault base directory."""
    return os.path.abspath(os.path.join(parent_scripts_dir, "../.."))


class BasePlatform(ABC):
    """Abstract base class representing a broker or account platform extension."""

    id: str = ""
    display_name: str = ""
    raw_folder: str = ""
    default_mode: str = "csv"  # "csv", "xls", "api"
    aliases: list[str] = []

    def __init__(self, base_dir: str | None = None):
        self.base_dir = os.path.abspath(base_dir) if base_dir else get_default_base_dir()

    @property
    def raw_dir(self) -> str:
        """Directory path in 00_Raw for platform export files."""
        return os.path.join(self.base_dir, "00_Raw", self.raw_folder)

    @property
    def vault_assets_dir(self) -> str:
        """Directory path where asset notes are stored."""
        return os.path.join(self.base_dir, "10_Finance", "Assets")

    def get_config(self) -> PlatformConfig:
        """Load platform configuration from config.yaml."""
        vault_cfg = load_vault_config(base_dir=self.base_dir)
        cfg = vault_cfg.platforms.get(self.id)
        if cfg:
            return cfg
        # Fallback to empty default config
        return PlatformConfig(enabled=True, default_mode=self.default_mode)

    def is_enabled(self) -> bool:
        """Check whether platform is enabled in config.yaml."""
        vault_cfg = load_vault_config(base_dir=self.base_dir)
        if self.id in vault_cfg.platforms:
            return vault_cfg.platforms[self.id].enabled
        # If not explicitly mentioned in config, default to True
        return True

    def can_handle_file(self, file_path: str) -> bool:
        """Check if this platform handles the given file path."""
        norm = os.path.normpath(file_path).lower()
        # Direct folder or file keyword match
        if self.raw_folder and self.raw_folder.lower() in norm:
            return True
        if self.id and self.id.lower() in norm:
            return True
        for alias in self.aliases:
            if alias.lower() in norm:
                return True
        return False

    @abstractmethod
    def run_import(
        self,
        file_path: str | None = None,
        use_api: bool | None = None,
        account_id: str | None = None,
        max_workers: int | None = None,
        show_progress: bool = True,
    ) -> int:
        """Run asset import for this platform and return count of imported/updated positions."""
        raise NotImplementedError


class PlatformRegistry:
    """Registry managing available and enabled platform extensions."""

    _platforms: dict[str, type[BasePlatform]] = {}
    _alias_map: dict[str, str] = {}

    @classmethod
    def register(cls, platform_cls: type[BasePlatform]) -> type[BasePlatform]:
        """Register a platform extension class."""
        if not platform_cls.id:
            raise ValueError(f"Platform class {platform_cls.__name__} must define a non-empty 'id'.")
        pid = platform_cls.id.lower().strip()
        cls._platforms[pid] = platform_cls
        cls._alias_map[pid] = pid
        for alias in platform_cls.aliases:
            cls._alias_map[alias.lower().strip()] = pid
        return platform_cls

    @classmethod
    def get(cls, platform_id: str, base_dir: str | None = None) -> BasePlatform | None:
        """Retrieve instantiated platform by ID or alias."""
        key = platform_id.lower().strip()
        canonical_id = cls._alias_map.get(key, key)
        platform_cls = cls._platforms.get(canonical_id)
        if platform_cls:
            return platform_cls(base_dir=base_dir)
        return None

    @classmethod
    def get_all(cls, base_dir: str | None = None) -> dict[str, BasePlatform]:
        """Return all registered platforms keyed by canonical ID."""
        return {pid: platform_cls(base_dir=base_dir) for pid, platform_cls in cls._platforms.items()}

    @classmethod
    def get_enabled(cls, base_dir: str | None = None) -> dict[str, BasePlatform]:
        """Return dictionary of only platforms that are enabled in config.yaml."""
        all_platforms = cls.get_all(base_dir=base_dir)
        return {pid: p for pid, p in all_platforms.items() if p.is_enabled()}

    @classmethod
    def detect_platform_from_path(cls, file_path: str, base_dir: str | None = None) -> BasePlatform:
        """Detect which platform can handle the provided file path."""
        norm_path = os.path.normpath(file_path).lower()
        all_platforms = cls.get_all(base_dir=base_dir)

        # 1. Exact match by raw_folder in path
        for p in all_platforms.values():
            if p.raw_folder and p.raw_folder.lower() in norm_path:
                return p

        # 2. Match by can_handle_file
        for p in all_platforms.values():
            if p.can_handle_file(file_path):
                return p

        supported = ", ".join(p.display_name for p in all_platforms.values())
        raise ValueError(
            f"Could not recognize supported platform from file path '{file_path}'. Supported platforms are: {supported}"
        )

    @classmethod
    def list_platforms(cls, base_dir: str | None = None) -> list[dict[str, Any]]:
        """Return metadata list of all registered platforms and their enabled status."""
        items = []
        for pid, p in cls.get_all(base_dir=base_dir).items():
            cfg = p.get_config()
            items.append(
                {
                    "id": p.id,
                    "display_name": p.display_name,
                    "raw_folder": p.raw_folder,
                    "enabled": p.is_enabled(),
                    "default_mode": getattr(cfg, "default_mode", p.default_mode),
                    "default_portfolio": getattr(cfg, "default_portfolio", None),
                }
            )
        return items

    @classmethod
    def set_platform_enabled(cls, platform_id: str, enabled: bool, base_dir: str | None = None) -> bool:
        """Enable or disable a platform in config.yaml."""
        base = base_dir or get_default_base_dir()
        canonical_id = cls._alias_map.get(platform_id.lower().strip(), platform_id.lower().strip())
        if canonical_id not in cls._platforms:
            raise ValueError(f"Unknown platform ID: '{platform_id}'")

        candidate_paths = [
            os.path.join(base, "99_System", "config.yaml"),
            os.path.join(base, "config.yaml"),
        ]
        val_str = "true" if enabled else "false"
        updated = False

        for target_path in candidate_paths:
            if not os.path.exists(target_path):
                continue
            with open(target_path, encoding="utf-8") as f:
                content = f.read()

            lines = content.splitlines(keepends=True)
            in_platforms = False
            in_target_platform = False
            found_enabled = False
            found_platform = False
            new_lines = []

            for line in lines:
                stripped = line.strip()
                if line.startswith("platforms:"):
                    in_platforms = True
                    new_lines.append(line)
                    continue

                if in_platforms:
                    # Leaving platforms section
                    if stripped and not line.startswith(" ") and not line.startswith("\t"):
                        if in_target_platform and not found_enabled:
                            new_lines.append(f"    enabled: {val_str}\n")
                            found_enabled = True
                        if not found_platform:
                            new_lines.append(f"  {canonical_id}:\n    enabled: {val_str}\n\n")
                            found_platform = True
                            found_enabled = True
                        in_platforms = False
                        in_target_platform = False
                        new_lines.append(line)
                        continue

                    if re.match(r"^ {2}[a-zA-Z0-9_-]+:", line):
                        if in_target_platform and not found_enabled:
                            new_lines.append(f"    enabled: {val_str}\n")
                            found_enabled = True
                        if line.startswith(f"  {canonical_id}:"):
                            in_target_platform = True
                            found_platform = True
                        else:
                            in_target_platform = False
                        new_lines.append(line)
                        continue

                    if in_target_platform and re.match(r"^ {4}enabled:", line):
                        new_lines.append(f"    enabled: {val_str}\n")
                        found_enabled = True
                        continue

                new_lines.append(line)

            if in_platforms and not found_platform:
                new_lines.append(f"  {canonical_id}:\n    enabled: {val_str}\n")
            elif in_target_platform and not found_enabled:
                new_lines.append(f"    enabled: {val_str}\n")

            new_content = "".join(new_lines)
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            updated = True

        load_vault_config(base_dir=base, force_refresh=True)
        return updated
