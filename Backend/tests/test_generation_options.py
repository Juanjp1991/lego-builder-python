"""Unit tests for generation options (model size)."""

import pytest
from pydantic import ValidationError
from models.generation_options import (
    ModelSize,
    MODEL_SIZE_SPECS,
    CustomSizeSettings,
    GenerationOptions,
    get_size_spec,
)


class TestModelSize:
    """Tests for ModelSize enum."""

    def test_all_sizes_defined(self):
        """Test that all expected sizes are defined."""
        sizes = [ModelSize.TINY, ModelSize.SMALL, ModelSize.MEDIUM, ModelSize.LARGE, ModelSize.EPIC, ModelSize.CUSTOM]
        assert len(sizes) == 6

    def test_size_values(self):
        """Test that size values are lowercase strings."""
        assert ModelSize.TINY.value == "tiny"
        assert ModelSize.SMALL.value == "small"
        assert ModelSize.MEDIUM.value == "medium"
        assert ModelSize.LARGE.value == "large"
        assert ModelSize.EPIC.value == "epic"
        assert ModelSize.CUSTOM.value == "custom"


class TestModelSizeSpecs:
    """Tests for MODEL_SIZE_SPECS."""

    def test_all_sizes_have_specs(self):
        """Test that all non-custom sizes have specifications."""
        for size in [ModelSize.TINY, ModelSize.SMALL, ModelSize.MEDIUM, ModelSize.LARGE, ModelSize.EPIC]:
            assert size in MODEL_SIZE_SPECS
            spec = MODEL_SIZE_SPECS[size]
            assert "min_bricks" in spec
            assert "max_bricks" in spec
            assert "min_layers" in spec
            assert "max_layers" in spec

    def test_brick_ranges_are_valid(self):
        """Test that brick ranges make sense."""
        for size, spec in MODEL_SIZE_SPECS.items():
            assert spec["min_bricks"] > 0
            assert spec["max_bricks"] >= spec["min_bricks"]
            assert spec["min_layers"] > 0
            assert spec["max_layers"] >= spec["min_layers"]

    def test_sizes_are_ordered(self):
        """Test that sizes increase in complexity."""
        sizes_ordered = [ModelSize.TINY, ModelSize.SMALL, ModelSize.MEDIUM, ModelSize.LARGE, ModelSize.EPIC]
        for i in range(len(sizes_ordered) - 1):
            current = MODEL_SIZE_SPECS[sizes_ordered[i]]
            next_size = MODEL_SIZE_SPECS[sizes_ordered[i + 1]]
            assert next_size["max_bricks"] >= current["max_bricks"]


class TestCustomSizeSettings:
    """Tests for CustomSizeSettings validation."""

    def test_valid_custom_settings(self):
        """Test that valid custom settings are accepted."""
        settings = CustomSizeSettings(
            min_bricks=50,
            max_bricks=100,
            min_layers=3,
            max_layers=10
        )
        assert settings.min_bricks == 50
        assert settings.max_bricks == 100

    def test_min_bricks_too_low(self):
        """Test that min_bricks < 10 is rejected."""
        with pytest.raises(ValidationError):
            CustomSizeSettings(
                min_bricks=5,  # Too low
                max_bricks=100,
                min_layers=1,
                max_layers=10
            )

    def test_max_bricks_too_high(self):
        """Test that max_bricks > 1000 is rejected."""
        with pytest.raises(ValidationError):
            CustomSizeSettings(
                min_bricks=10,
                max_bricks=1500,  # Too high
                min_layers=1,
                max_layers=10
            )

    def test_min_layers_too_low(self):
        """Test that min_layers < 1 is rejected."""
        with pytest.raises(ValidationError):
            CustomSizeSettings(
                min_bricks=10,
                max_bricks=100,
                min_layers=0,  # Too low
                max_layers=10
            )

    def test_max_layers_too_high(self):
        """Test that max_layers > 50 is rejected."""
        with pytest.raises(ValidationError):
            CustomSizeSettings(
                min_bricks=10,
                max_bricks=100,
                min_layers=1,
                max_layers=60  # Too high
            )

    def test_max_bricks_less_than_min(self):
        """Test that max_bricks < min_bricks is rejected."""
        with pytest.raises(ValidationError):
            CustomSizeSettings(
                min_bricks=100,
                max_bricks=50,  # Less than min
                min_layers=1,
                max_layers=10
            )

    def test_max_layers_less_than_min(self):
        """Test that max_layers < min_layers is rejected."""
        with pytest.raises(ValidationError):
            CustomSizeSettings(
                min_bricks=10,
                max_bricks=100,
                min_layers=10,
                max_layers=5  # Less than min
            )


class TestGenerationOptions:
    """Tests for GenerationOptions."""

    def test_default_options(self):
        """Test default generation options."""
        options = GenerationOptions()
        assert options.model_size == ModelSize.SMALL
        assert options.custom_settings is None
        assert options.complexity == "normal"

    def test_set_model_size(self):
        """Test setting model size."""
        options = GenerationOptions(model_size=ModelSize.LARGE)
        assert options.model_size == ModelSize.LARGE

    def test_custom_requires_settings(self):
        """Test that custom size requires settings."""
        with pytest.raises(ValidationError):
            GenerationOptions(
                model_size=ModelSize.CUSTOM,
                custom_settings=None
            )

    def test_custom_with_settings(self):
        """Test custom size with valid settings."""
        options = GenerationOptions(
            model_size=ModelSize.CUSTOM,
            custom_settings=CustomSizeSettings(
                min_bricks=50,
                max_bricks=150,
                min_layers=5,
                max_layers=15
            )
        )
        assert options.model_size == ModelSize.CUSTOM
        assert options.custom_settings.min_bricks == 50

    def test_get_size_spec_predefined(self):
        """Test getting size spec for predefined sizes."""
        options = GenerationOptions(model_size=ModelSize.MEDIUM)
        spec = options.get_size_spec()
        assert spec["min_bricks"] == 60
        assert spec["max_bricks"] == 120

    def test_get_size_spec_custom(self):
        """Test getting size spec for custom size."""
        options = GenerationOptions(
            model_size=ModelSize.CUSTOM,
            custom_settings=CustomSizeSettings(
                min_bricks=25,
                max_bricks=75,
                min_layers=2,
                max_layers=8
            )
        )
        spec = options.get_size_spec()
        assert spec["min_bricks"] == 25
        assert spec["max_bricks"] == 75
        assert spec["display_name"] == "Custom"


class TestGetSizeSpec:
    """Tests for get_size_spec function."""

    def test_predefined_size(self):
        """Test getting spec for predefined size."""
        spec = get_size_spec(ModelSize.TINY)
        assert spec["min_bricks"] == 15
        assert spec["max_bricks"] == 30

    def test_custom_size_without_settings(self):
        """Test that custom without settings raises error."""
        with pytest.raises(ValueError):
            get_size_spec(ModelSize.CUSTOM)

    def test_custom_size_with_settings(self):
        """Test custom size with settings."""
        settings = CustomSizeSettings(
            min_bricks=100,
            max_bricks=200,
            min_layers=10,
            max_layers=20
        )
        spec = get_size_spec(ModelSize.CUSTOM, settings)
        assert spec["min_bricks"] == 100
        assert spec["max_bricks"] == 200
