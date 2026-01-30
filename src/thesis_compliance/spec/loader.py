"""YAML style specification loader."""

from pathlib import Path
from typing import Any

import yaml

from thesis_compliance.spec.rules import (
    BibliographyRule,
    CaptionRule,
    FontRule,
    HeadingRule,
    MarginRule,
    PageNumberRule,
    SpacingRule,
    StyleSpec,
    TitlePageRule,
)


class SpecLoader:
    """Load style specifications from YAML files."""

    # Directory containing built-in specs
    BUILTIN_DIR = Path(__file__).parent / "builtin"

    @classmethod
    def list_builtin_specs(cls) -> list[str]:
        """List available built-in specifications.

        Returns:
            List of spec names (without .yaml extension).
        """
        if not cls.BUILTIN_DIR.exists():
            return []
        return [p.stem for p in cls.BUILTIN_DIR.glob("*.yaml")]

    @classmethod
    def _validate_path(cls, path: Path) -> None:
        """Validate path to prevent path traversal attacks.

        Args:
            path: Path to validate.

        Raises:
            ValueError: If path contains traversal sequences or is invalid.
        """
        # Check for path traversal attempts
        if ".." in str(path):
            raise ValueError(f"Invalid spec path: path traversal not allowed: {path}")

        # Resolve and verify the path exists
        try:
            resolved = path.resolve()
            if not resolved.exists():
                raise ValueError(f"Invalid spec path: {path}")
        except (OSError, RuntimeError) as e:
            raise ValueError(f"Invalid spec path: {path}: {e}") from e

    @classmethod
    def load(cls, name_or_path: str) -> StyleSpec:
        """Load a style specification.

        Args:
            name_or_path: Either a built-in spec name (e.g., "rackham")
                         or a path to a custom YAML file.

        Returns:
            Loaded StyleSpec.

        Raises:
            FileNotFoundError: If spec file doesn't exist.
            ValueError: If spec file is invalid or contains path traversal.
        """
        # Check if it's a path
        path = Path(name_or_path)
        if path.suffix == ".yaml" or path.suffix == ".yml":
            cls._validate_path(path)
            if not path.exists():
                raise FileNotFoundError(f"Spec file not found: {path}")
            return cls._load_from_file(path)

        # Try as built-in spec name
        builtin_path = cls.BUILTIN_DIR / f"{name_or_path}.yaml"
        if builtin_path.exists():
            return cls._load_from_file(builtin_path)

        # Try with .yaml extension added
        yaml_path = path.with_suffix(".yaml")
        if yaml_path.exists():
            cls._validate_path(yaml_path)
            return cls._load_from_file(yaml_path)

        raise FileNotFoundError(
            f"Spec not found: '{name_or_path}'. "
            f"Available built-in specs: {', '.join(cls.list_builtin_specs())}"
        )

    @classmethod
    def _load_from_file(cls, path: Path) -> StyleSpec:
        """Load spec from a YAML file.

        Args:
            path: Path to YAML file.

        Returns:
            Loaded StyleSpec.

        Raises:
            ValueError: If file is invalid.
        """
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {path}: {e}") from e

        if not isinstance(data, dict):
            raise ValueError(f"Spec file must contain a YAML object: {path}")

        return cls._parse_spec(data, path.stem)

    @classmethod
    def _parse_spec(cls, data: dict[str, Any], default_name: str) -> StyleSpec:
        """Parse spec data into a StyleSpec object.

        Args:
            data: Parsed YAML data.
            default_name: Default name if not specified in data.

        Returns:
            StyleSpec object.
        """
        # Parse margins
        margins_data = data.get("margins", {})
        margins = MarginRule(
            left=margins_data.get("left", 1.5),
            right=margins_data.get("right", 1.0),
            top=margins_data.get("top", 1.0),
            bottom=margins_data.get("bottom", 1.0),
            tolerance=margins_data.get("tolerance", 0.05),
        )

        # Parse additional margin rules
        additional_margins: list[MarginRule] = []
        for rule_data in data.get("additional_margins", []):
            additional_margins.append(
                MarginRule(
                    left=rule_data.get("left", margins.left),
                    right=rule_data.get("right", margins.right),
                    top=rule_data.get("top", margins.top),
                    bottom=rule_data.get("bottom", margins.bottom),
                    tolerance=rule_data.get("tolerance", margins.tolerance),
                    applies_to=rule_data.get("applies_to", "all"),
                )
            )

        # Parse fonts
        fonts_data = data.get("fonts", {})
        fonts = FontRule(
            allowed_fonts=fonts_data.get(
                "allowed_fonts", ["Times", "Times New Roman", "Arial", "Helvetica"]
            ),
            body_size=fonts_data.get("body_size", 12.0),
            size_tolerance=fonts_data.get("size_tolerance", 0.5),
            min_size=fonts_data.get("min_size", 10.0),
        )

        # Parse spacing
        spacing_data = data.get("spacing", {})
        spacing = SpacingRule(
            required_ratio=spacing_data.get("required_ratio", 2.0),
            tolerance=spacing_data.get("tolerance", 0.2),
            applies_to=spacing_data.get("applies_to", "body"),
        )

        # Parse page numbers
        page_numbers_data = data.get("page_numbers", {})
        front_matter = page_numbers_data.get("front_matter", {})
        body = page_numbers_data.get("body", {})
        page_numbers = PageNumberRule(
            front_matter_style=front_matter.get("style", "roman"),
            front_matter_position=front_matter.get("position", "bottom"),
            front_matter_alignment=front_matter.get("alignment", "center"),
            body_style=body.get("style", "arabic"),
            body_position=body.get("position", "bottom"),
            body_alignment=body.get("alignment", "center"),
            body_starts_at=body.get("starts_at", 1),
        )

        # Parse title page
        title_page_data = data.get("title_page", {})
        title_page = TitlePageRule(
            top_margin=title_page_data.get("top_margin", 2.0),
            margin_tolerance=title_page_data.get("margin_tolerance", 0.1),
            has_page_number=title_page_data.get("has_page_number", False),
        )

        # Parse headings (optional)
        headings: HeadingRule | None = None
        if "headings" in data:
            hd = data["headings"]
            headings = HeadingRule(
                chapter_font_size=hd.get("chapter_font_size", 14.0),
                chapter_bold=hd.get("chapter_bold", True),
                chapter_all_caps=hd.get("chapter_all_caps", True),
                section_font_size=hd.get("section_font_size", 12.0),
                section_bold=hd.get("section_bold", True),
                subsection_font_size=hd.get("subsection_font_size", 12.0),
                subsection_bold=hd.get("subsection_bold", False),
                subsection_italic=hd.get("subsection_italic", True),
                space_before_chapter=hd.get("space_before_chapter", 2.0),
                space_before_section=hd.get("space_before_section", 24.0),
                space_before_subsection=hd.get("space_before_subsection", 12.0),
                size_tolerance=hd.get("size_tolerance", 0.5),
            )

        # Parse captions (optional)
        captions: CaptionRule | None = None
        if "captions" in data:
            cd = data["captions"]
            captions = CaptionRule(
                font_size=cd.get("font_size", 10.0),
                size_tolerance=cd.get("size_tolerance", 0.5),
                figure_position=cd.get("figure_position", "below"),
                table_position=cd.get("table_position", "above"),
                figure_label=cd.get("figure_label", "Figure"),
                table_label=cd.get("table_label", "Table"),
                numbering=cd.get("numbering", "continuous"),
            )

        # Parse bibliography (optional)
        bibliography: BibliographyRule | None = None
        if "bibliography" in data:
            bd = data["bibliography"]
            bibliography = BibliographyRule(
                hanging_indent=bd.get("hanging_indent", 0.5),
                indent_tolerance=bd.get("indent_tolerance", 0.1),
                entry_spacing=bd.get("entry_spacing", 1.0),
                between_entries=bd.get("between_entries", 2.0),
                spacing_tolerance=bd.get("spacing_tolerance", 0.2),
                font_size=bd.get("font_size", 12.0),
                size_tolerance=bd.get("size_tolerance", 0.5),
            )

        return StyleSpec(
            name=data.get("name", default_name),
            university=data.get("university", "Unknown University"),
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            url=data.get("url", ""),
            margins=margins,
            fonts=fonts,
            spacing=spacing,
            page_numbers=page_numbers,
            title_page=title_page,
            headings=headings,
            captions=captions,
            bibliography=bibliography,
            additional_margins=additional_margins,
        )

    @classmethod
    def get_default_spec(cls) -> StyleSpec:
        """Get the default (Rackham) specification.

        Returns:
            Default StyleSpec.
        """
        try:
            return cls.load("rackham")
        except FileNotFoundError:
            # Return a basic default if rackham.yaml is missing
            return StyleSpec(
                name="default",
                university="Generic",
                description="Default thesis formatting requirements",
            )
