"""Tests for style specification loading."""

import pytest
import tempfile
from pathlib import Path

from thesis_compliance.spec import SpecLoader, StyleSpec
from thesis_compliance.spec.rules import MarginRule


class TestSpecLoader:
    """Tests for SpecLoader."""

    def test_list_builtin_specs(self):
        specs = SpecLoader.list_builtin_specs()
        assert "rackham" in specs
        assert "unc" in specs
        assert "rice" in specs

    def test_load_builtin_rackham(self):
        spec = SpecLoader.load("rackham")
        assert spec.name == "rackham"
        assert spec.university == "University of Michigan"
        assert spec.margins.left == 1.5
        assert spec.margins.right == 1.0

    def test_load_builtin_unc(self):
        spec = SpecLoader.load("unc")
        assert spec.name == "unc"
        assert "Carolina" in spec.university

    def test_load_not_found(self):
        with pytest.raises(FileNotFoundError):
            SpecLoader.load("nonexistent_university")

    def test_load_custom_yaml(self):
        yaml_content = """
name: custom
university: Custom University
description: Custom spec for testing
margins:
  left: 2.0
  right: 1.5
  top: 1.25
  bottom: 1.25
fonts:
  allowed_fonts:
    - CustomFont
  body_size: 11.0
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()

            spec = SpecLoader.load(f.name)
            assert spec.name == "custom"
            assert spec.university == "Custom University"
            assert spec.margins.left == 2.0
            assert spec.fonts.body_size == 11.0
            assert "CustomFont" in spec.fonts.allowed_fonts

    def test_get_default_spec(self):
        spec = SpecLoader.get_default_spec()
        assert spec.name == "rackham"


class TestStyleSpec:
    """Tests for StyleSpec."""

    def test_rule_count(self):
        spec = SpecLoader.load("rackham")
        count = spec.rule_count
        # Should have multiple rules
        assert count >= 10

    def test_get_margin_rule_for_title_page(self):
        spec = SpecLoader.load("rackham")
        rule = spec.get_margin_rule_for_page("title_page")
        # Title page has 2" top margin
        assert rule.top == 2.0

    def test_get_margin_rule_for_body(self):
        spec = SpecLoader.load("rackham")
        rule = spec.get_margin_rule_for_page("body")
        # Body uses standard margins
        assert rule.left == 1.5
        assert rule.top == 1.0
