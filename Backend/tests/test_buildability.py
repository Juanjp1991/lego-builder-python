"""Unit tests for the buildability validator."""

import pytest
from validation.buildability import (
    validate_buildability,
    BuildabilityResult,
    BrickPlacement,
    STANDARD_BRICK_SIZES,
    LEGO_GRID_SIZE,
    LEGO_BRICK_HEIGHT,
    _is_grid_aligned,
    _get_brick_footprint,
    _get_layer_index,
)


class TestGridAlignment:
    """Tests for grid alignment validation."""

    def test_is_grid_aligned_exact(self):
        """Test that exact grid positions are aligned."""
        assert _is_grid_aligned(0.0, LEGO_GRID_SIZE)
        assert _is_grid_aligned(8.0, LEGO_GRID_SIZE)
        assert _is_grid_aligned(16.0, LEGO_GRID_SIZE)

    def test_is_grid_aligned_within_tolerance(self):
        """Test that positions within tolerance are aligned."""
        assert _is_grid_aligned(8.05, LEGO_GRID_SIZE)
        assert _is_grid_aligned(7.95, LEGO_GRID_SIZE)

    def test_is_grid_aligned_misaligned(self):
        """Test that misaligned positions are detected."""
        assert not _is_grid_aligned(4.0, LEGO_GRID_SIZE)
        assert not _is_grid_aligned(8.5, LEGO_GRID_SIZE)

    def test_grid_aligned_bricks_pass(self):
        """Test that grid-aligned bricks pass validation."""
        model_data = {
            "build_sequence": [
                {"step": 1, "brick": "2x4", "color": "red", "position": {"x": 0, "y": 0, "z": 0}},
                {"step": 2, "brick": "2x4", "color": "red", "position": {"x": 8, "y": 0, "z": 0}},
            ]
        }
        result = validate_buildability(model_data)
        assert "not aligned" not in " ".join(result.issues).lower()

    def test_misaligned_bricks_fail(self):
        """Test that misaligned bricks are caught."""
        model_data = {
            "build_sequence": [
                {"step": 1, "brick": "2x4", "color": "red", "position": {"x": 5, "y": 0, "z": 0}},
            ]
        }
        result = validate_buildability(model_data)
        assert any("not aligned" in issue for issue in result.issues)


class TestBrickSizes:
    """Tests for brick size validation."""

    def test_standard_sizes_pass(self):
        """Test that standard brick sizes pass validation."""
        model_data = {
            "build_sequence": [
                {"step": 1, "brick": "2x4", "color": "red", "position": {"x": 0, "y": 0, "z": 0}},
                {"step": 2, "brick": "2x2", "color": "blue", "position": {"x": 16, "y": 0, "z": 0}},
                {"step": 3, "brick": "1x4", "color": "white", "position": {"x": 0, "y": 8, "z": 0}},
            ]
        }
        result = validate_buildability(model_data)
        assert not any("Non-standard" in issue for issue in result.issues)

    def test_nonstandard_sizes_fail(self):
        """Test that non-standard brick sizes are caught."""
        model_data = {
            "build_sequence": [
                {"step": 1, "brick": "3x3", "color": "red", "position": {"x": 0, "y": 0, "z": 0}},
            ]
        }
        result = validate_buildability(model_data)
        assert any("Non-standard" in issue for issue in result.issues)


class TestConnectivity:
    """Tests for brick connectivity validation."""

    def test_ground_layer_always_valid(self):
        """Test that bricks on the ground layer are valid."""
        model_data = {
            "build_sequence": [
                {"step": 1, "brick": "2x4", "color": "red", "position": {"x": 0, "y": 0, "z": 0}},
            ]
        }
        result = validate_buildability(model_data)
        assert not any("Floating" in issue for issue in result.issues)

    def test_connected_brick_above_passes(self):
        """Test that a brick resting on another brick passes."""
        model_data = {
            "build_sequence": [
                {"step": 1, "brick": "2x4", "color": "red", "position": {"x": 0, "y": 0, "z": 0}},
                {"step": 2, "brick": "2x4", "color": "blue", "position": {"x": 0, "y": 0, "z": 9.6}},
            ]
        }
        result = validate_buildability(model_data)
        assert not any("Floating" in issue for issue in result.issues)

    def test_truly_floating_brick_fails(self):
        """Test that a truly floating brick (no connection above OR below) fails."""
        model_data = {
            "build_sequence": [
                {"step": 1, "brick": "2x4", "color": "red", "position": {"x": 0, "y": 0, "z": 0}},
                {"step": 2, "brick": "2x4", "color": "blue", "position": {"x": 100, "y": 100, "z": 9.6}},
            ]
        }
        result = validate_buildability(model_data)
        assert any("Floating" in issue for issue in result.issues)

    def test_brick_supported_from_above_passes(self):
        """Test that a brick supported by interlocking with brick above is valid.

        This tests the edge case where a brick might seem floating but is actually
        supported by interlocking with a brick above it (cantilever scenario).
        """
        # Create a scenario where layer 1 brick is only connected to layer 2 above it
        model_data = {
            "build_sequence": [
                # Ground layer
                {"step": 1, "brick": "2x4", "color": "red", "position": {"x": 0, "y": 0, "z": 0}},
                # Layer 1 - partially overlapping with ground but also overlapping with layer 2
                {"step": 2, "brick": "2x4", "color": "blue", "position": {"x": 0, "y": 0, "z": 9.6}},
                # Layer 2 - overlapping with layer 1
                {"step": 3, "brick": "2x4", "color": "green", "position": {"x": 0, "y": 0, "z": 19.2}},
            ]
        }
        result = validate_buildability(model_data)
        # All bricks should be connected - no floating
        assert not any("Floating" in issue for issue in result.issues)


class TestStaggeredJoints:
    """Tests for staggered joints validation."""

    def test_staggered_joints_pass(self):
        """Test that properly staggered joints pass."""
        model_data = {
            "build_sequence": [
                # Layer 0
                {"step": 1, "brick": "2x4", "color": "red", "position": {"x": 0, "y": 0, "z": 0}},
                {"step": 2, "brick": "2x4", "color": "red", "position": {"x": 32, "y": 0, "z": 0}},
                # Layer 1 - offset
                {"step": 3, "brick": "2x4", "color": "blue", "position": {"x": 16, "y": 0, "z": 9.6}},
                # Layer 2 - offset from layer 1
                {"step": 4, "brick": "2x4", "color": "green", "position": {"x": 0, "y": 0, "z": 19.2}},
            ]
        }
        result = validate_buildability(model_data)
        # Staggered joints should not cause major issues
        assert result.score >= 70


class TestAssemblyOrder:
    """Tests for assembly order validation."""

    def test_bottom_to_top_passes(self):
        """Test that building from bottom to top passes."""
        model_data = {
            "build_sequence": [
                {"step": 1, "brick": "2x4", "color": "red", "position": {"x": 0, "y": 0, "z": 0}},
                {"step": 2, "brick": "2x4", "color": "blue", "position": {"x": 0, "y": 0, "z": 9.6}},
                {"step": 3, "brick": "2x4", "color": "green", "position": {"x": 0, "y": 0, "z": 19.2}},
            ]
        }
        result = validate_buildability(model_data)
        assert not any("jumps too far" in issue for issue in result.issues)

    def test_jumping_layers_fails(self):
        """Test that jumping multiple layers ahead fails."""
        model_data = {
            "build_sequence": [
                {"step": 1, "brick": "2x4", "color": "red", "position": {"x": 0, "y": 0, "z": 0}},
                {"step": 2, "brick": "2x4", "color": "blue", "position": {"x": 0, "y": 0, "z": 38.4}},  # Skip to layer 4
            ]
        }
        result = validate_buildability(model_data)
        assert any("jumps too far" in issue for issue in result.issues)


class TestStructuralStability:
    """Tests for structural stability validation."""

    def test_stable_pyramid_passes(self):
        """Test that a pyramid-shaped structure passes stability."""
        model_data = {
            "build_sequence": [
                # Wide base
                {"step": 1, "brick": "2x4", "color": "red", "position": {"x": 0, "y": 0, "z": 0}},
                {"step": 2, "brick": "2x4", "color": "red", "position": {"x": 32, "y": 0, "z": 0}},
                # Narrower top
                {"step": 3, "brick": "2x4", "color": "blue", "position": {"x": 16, "y": 0, "z": 9.6}},
            ]
        }
        result = validate_buildability(model_data)
        assert not any("top-heavy" in rec.lower() for rec in result.recommendations)


class TestBuildTime:
    """Tests for build time estimation."""

    def test_build_time_calculation(self):
        """Test that build time is calculated reasonably."""
        model_data = {
            "build_sequence": [
                {"step": 1, "brick": "2x4", "color": "red", "position": {"x": 0, "y": 0, "z": 0}},
                {"step": 2, "brick": "2x4", "color": "blue", "position": {"x": 0, "y": 0, "z": 9.6}},
                {"step": 3, "brick": "2x4", "color": "green", "position": {"x": 0, "y": 0, "z": 19.2}},
                {"step": 4, "brick": "2x4", "color": "yellow", "position": {"x": 0, "y": 0, "z": 28.8}},
            ]
        }
        result = validate_buildability(model_data)
        # 4 bricks at 15s each = 1 min, 4 layers at 30s each = 2 min -> ~3 min
        assert result.estimated_build_time_minutes >= 2
        assert result.estimated_build_time_minutes <= 5


class TestScoreCalculation:
    """Tests for overall score calculation."""

    def test_perfect_model_high_score(self):
        """Test that a valid model gets a high score."""
        model_data = {
            "build_sequence": [
                {"step": 1, "brick": "2x4", "color": "red", "position": {"x": 0, "y": 0, "z": 0}},
                {"step": 2, "brick": "2x4", "color": "red", "position": {"x": 16, "y": 0, "z": 0}},
                {"step": 3, "brick": "2x4", "color": "blue", "position": {"x": 8, "y": 0, "z": 9.6}},
            ]
        }
        result = validate_buildability(model_data)
        assert result.score >= 80
        assert result.valid

    def test_invalid_model_low_score(self):
        """Test that an invalid model gets a low score."""
        model_data = {
            "build_sequence": [
                {"step": 1, "brick": "3x3", "color": "red", "position": {"x": 5, "y": 5, "z": 5}},
            ]
        }
        result = validate_buildability(model_data)
        assert result.score < 70
        assert not result.valid


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_build_sequence(self):
        """Test handling of empty build sequence."""
        model_data = {"build_sequence": []}
        result = validate_buildability(model_data)
        assert not result.valid
        assert result.score == 0

    def test_missing_build_sequence(self):
        """Test handling of missing build sequence."""
        model_data = {}
        result = validate_buildability(model_data)
        assert not result.valid
        assert "No build_sequence" in result.issues[0]

    def test_invalid_brick_data(self):
        """Test handling of malformed brick data."""
        model_data = {
            "build_sequence": [
                {"step": 1},  # Missing required fields
            ]
        }
        result = validate_buildability(model_data)
        # Should still produce a result, possibly with issues
        assert isinstance(result, BuildabilityResult)


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_layer_index(self):
        """Test layer index calculation."""
        assert _get_layer_index(0) == 0
        assert _get_layer_index(9.6) == 1
        assert _get_layer_index(19.2) == 2
        assert _get_layer_index(9.5) == 1  # Within rounding

    def test_get_brick_footprint(self):
        """Test brick footprint calculation."""
        brick = BrickPlacement(
            step=1,
            brick="2x4",
            color="red",
            position={"x": 0, "y": 0, "z": 0}
        )
        footprint = _get_brick_footprint(brick)
        # 2x4 brick should cover 8 grid cells
        assert len(footprint) == 8
        assert (0, 0) in footprint
        assert (1, 0) in footprint
        assert (0, 3) in footprint
        assert (1, 3) in footprint


class TestResultSerialization:
    """Tests for result serialization."""

    def test_result_to_dict(self):
        """Test that BuildabilityResult can be serialized to dict."""
        model_data = {
            "build_sequence": [
                {"step": 1, "brick": "2x4", "color": "red", "position": {"x": 0, "y": 0, "z": 0}},
            ]
        }
        result = validate_buildability(model_data)
        result_dict = result.to_dict()

        assert "valid" in result_dict
        assert "score" in result_dict
        assert "layer_count" in result_dict
        assert "issues" in result_dict
        assert "build_sequence" in result_dict
        assert isinstance(result_dict["build_sequence"], list)
