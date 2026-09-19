from abc import ABC, abstractmethod
from typing import Optional, List, Any
import sys
import os

# Ensure model is importable
current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.dirname(os.path.dirname(current_dir))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

from model.asset import Asset


class BaseAlertRule(ABC):
    """Abstract base class for all portfolio alert rules."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable identifier for the rule."""
        pass

    @property
    @abstractmethod
    def tag(self) -> str:
        """The Obsidian tag to apply when alert condition is met (e.g. '#alert/overvalued')."""
        pass

    @property
    def description(self) -> str:
        """Brief description of the rule criteria."""
        return ""

    @abstractmethod
    def evaluate(self, asset: Asset, context: Any) -> Optional[bool]:
        """Evaluate if the alert condition is triggered.

        Returns:
            True: The alert condition is met (tag should be added).
            False: The alert condition is not met (tag should be removed).
            None: The rule is not applicable to this asset (tag remains unchanged).
        """
        pass

    def apply(self, asset: Asset, context: Any) -> bool:
        """Evaluate rule and update asset tags in-place.

        Returns True if the asset's tags were modified, False otherwise.
        """
        should_alert = self.evaluate(asset, context)
        if should_alert is None:
            return False

        tags = list(asset.tags) if asset.tags else []
        tag_clean = self.tag.lstrip("#")
        has_tag = (self.tag in tags) or (tag_clean in tags)

        if should_alert and not has_tag:
            tags.append(self.tag)
            asset.tags = tags
            return True
        elif not should_alert and has_tag:
            tags = [t for t in tags if t != self.tag and t != tag_clean]
            asset.tags = tags
            return True

        return False
