"""Base classes, context, and step registry for modular vault initialization."""

import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class InitContext:
    """Shared execution context passed across vault initialization steps."""

    source_vault: str
    target_dir: str
    interactive: bool = True
    clean: bool | None = None
    force: bool = False
    exante_mode: str | None = None
    degiro_portfolio: str | None = None
    selected_platform_ids: list[str] = field(default_factory=list)
    base_currency: str = "PLN"
    currency_symbol: str = "zł"
    symbol_position: str = "suffix"
    max_single_stock_pct: float = 15.0
    preset_id: str | None = None
    single_step_mode: bool = False


def update_env_variable(env_path: str, key: str, value: str) -> None:
    """Set or update a key=value entry in a .env file preserving comments."""
    content = ""
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            content = f.read()

    pattern = re.compile(rf"(?m)^({re.escape(key)}\s*=\s*).*$")
    if pattern.search(content):
        content = pattern.sub(rf"\g<1>{value}", content)
    else:
        if content and not content.endswith("\n"):
            content += "\n"
        content += f"{key}={value}\n"

    with open(env_path, "w", encoding="utf-8") as f:
        f.write(content)


class BaseInitStep(ABC):
    """Abstract base class representing a discrete onboarding/configuration step."""

    step_id: str = ""
    step_number: int = 0
    title: str = ""
    description: str = ""
    aliases: list[str] = []

    def print_header(self, total_steps: int | None = None, single_step: bool = False) -> None:
        """Print formatted step header."""
        if single_step:
            print(f"\n🔧 Step [{self.step_id}]: {self.title}")
        elif total_steps:
            print(f"\nStep {self.step_number}/{total_steps}: {self.title}...")
        else:
            print(f"\nStep {self.step_number}: {self.title}...")

    @abstractmethod
    def run(self, ctx: InitContext) -> bool:
        """Execute this initialization step. Returns True on success, False on abort/error."""
        raise NotImplementedError


class InitStepRegistry:
    """Registry managing ordered initialization steps and alias resolution."""

    _steps: dict[str, type[BaseInitStep]] = {}
    _alias_map: dict[str, str] = {}

    @classmethod
    def register(cls, step_cls: type[BaseInitStep]) -> type[BaseInitStep]:
        """Decorator to register an initialization step class."""
        if not step_cls.step_id:
            raise ValueError(f"Step class {step_cls.__name__} must define a non-empty 'step_id'.")
        sid = step_cls.step_id.lower().strip()
        cls._steps[sid] = step_cls
        cls._alias_map[sid] = sid
        cls._alias_map[str(step_cls.step_number)] = sid
        for alias in step_cls.aliases:
            cls._alias_map[alias.lower().strip()] = sid
        return step_cls

    @classmethod
    def get(cls, step_identifier: str) -> BaseInitStep | None:
        """Retrieve instantiated step by canonical ID, step number, or alias."""
        key = str(step_identifier).lower().strip()
        canonical_id = cls._alias_map.get(key)
        if not canonical_id:
            # Also try normalizing hyphens/underscores
            norm_key = key.replace("-", "_")
            canonical_id = cls._alias_map.get(norm_key)
        if canonical_id and canonical_id in cls._steps:
            return cls._steps[canonical_id]()
        return None

    @classmethod
    def get_ordered_steps(cls) -> list[BaseInitStep]:
        """Return all registered steps instantiated and ordered by step_number."""
        ordered_classes = sorted(cls._steps.values(), key=lambda s: s.step_number)
        return [s() for s in ordered_classes]
