"""Style specification loading and models."""

from thesis_compliance.spec.loader import SpecLoader
from thesis_compliance.spec.rules import (
    FontRule,
    MarginRule,
    PageNumberRule,
    SpacingRule,
    StyleSpec,
    TitlePageRule,
)

__all__ = [
    "SpecLoader",
    "StyleSpec",
    "MarginRule",
    "FontRule",
    "SpacingRule",
    "PageNumberRule",
    "TitlePageRule",
]
