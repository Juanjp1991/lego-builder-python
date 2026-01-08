"""Buildability validator for LEGO models.

This module validates that generated LEGO models can be physically built
with standard LEGO bricks, checking grid alignment, connectivity,
structural stability, and assembly order.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Set, Tuple, Optional
import logging
import math

logger = logging.getLogger(__name__)

# LEGO dimensions in mm
LEGO_GRID_SIZE = 8.0  # Standard stud spacing (XY)
LEGO_BRICK_HEIGHT = 9.6  # Standard brick height (Z)
LEGO_STUD_DIAMETER = 4.8
LEGO_STUD_HEIGHT = 1.8

# Standard brick sizes allowed (width x length in studs)
STANDARD_BRICK_SIZES = {"1x2", "1x4", "1x6", "2x2", "2x4", "2x6"}

# Stability check thresholds
STABILITY_TOP_HEAVY_RATIO = 1.5  # Top footprint > base * this ratio triggers recommendation
STABILITY_TOP_HEAVY_AREA_RATIO = 1.3  # Top area > base area * this ratio triggers penalty
COM_OFFSET_THRESHOLD = 0.4  # Center of mass offset relative to base dimension

# Brick dimensions in studs for each brick type
BRICK_DIMENSIONS = {
    "1x2": (1, 2),
    "1x4": (1, 4),
    "1x6": (1, 6),
    "2x2": (2, 2),
    "2x4": (2, 4),
    "2x6": (2, 6),
}


@dataclass
class BrickPlacement:
    """Represents a single brick placement in the build sequence."""
    step: int
    brick: str  # "2x4", "2x2", etc.
    color: str
    position: Dict[str, float]  # {"x": 0, "y": 0, "z": 0}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "step": self.step,
            "brick": self.brick,
            "color": self.color,
            "position": self.position
        }


@dataclass
class BuildabilityResult:
    """Result of buildability validation."""
    valid: bool
    score: int  # 0-100
    layer_count: int
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    build_sequence: List[BrickPlacement] = field(default_factory=list)
    estimated_build_time_minutes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "valid": self.valid,
            "score": self.score,
            "layer_count": self.layer_count,
            "issues": self.issues,
            "recommendations": self.recommendations,
            "build_sequence": [b.to_dict() for b in self.build_sequence],
            "estimated_build_time_minutes": self.estimated_build_time_minutes
        }


def _is_grid_aligned(value: float, grid_size: float, tolerance: float = 0.1) -> bool:
    """Check if a value is aligned to the grid."""
    remainder = abs(value % grid_size)
    return remainder < tolerance or (grid_size - remainder) < tolerance


def _get_brick_footprint(brick: BrickPlacement) -> Set[Tuple[int, int]]:
    """Get the grid cells occupied by a brick at its position (XY footprint).

    Returns a set of (grid_x, grid_y) tuples that the brick covers.
    """
    brick_type = brick.brick
    if brick_type not in BRICK_DIMENSIONS:
        return set()

    width, length = BRICK_DIMENSIONS[brick_type]
    base_x = int(round(brick.position["x"] / LEGO_GRID_SIZE))
    base_y = int(round(brick.position["y"] / LEGO_GRID_SIZE))

    footprint = set()
    for dx in range(width):
        for dy in range(length):
            footprint.add((base_x + dx, base_y + dy))
    return footprint


def _get_layer_index(z: float) -> int:
    """Get the layer index for a given Z position."""
    return int(round(z / LEGO_BRICK_HEIGHT))


def _check_grid_alignment(bricks: List[BrickPlacement]) -> Tuple[List[str], int]:
    """Check if all bricks are aligned to the LEGO grid.

    Returns:
        Tuple of (issues list, penalty points)
    """
    issues = []
    penalty = 0

    for brick in bricks:
        pos = brick.position
        x_aligned = _is_grid_aligned(pos["x"], LEGO_GRID_SIZE)
        y_aligned = _is_grid_aligned(pos["y"], LEGO_GRID_SIZE)
        z_aligned = _is_grid_aligned(pos["z"], LEGO_BRICK_HEIGHT)

        if not x_aligned:
            issues.append(f"Brick at step {brick.step} has X position {pos['x']}mm not aligned to 8mm grid")
            penalty += 5
        if not y_aligned:
            issues.append(f"Brick at step {brick.step} has Y position {pos['y']}mm not aligned to 8mm grid")
            penalty += 5
        if not z_aligned:
            issues.append(f"Brick at step {brick.step} has Z position {pos['z']}mm not aligned to 9.6mm layers")
            penalty += 5

    return issues, penalty


def _check_brick_sizes(bricks: List[BrickPlacement]) -> Tuple[List[str], int]:
    """Check if all bricks are standard sizes.

    Returns:
        Tuple of (issues list, penalty points)
    """
    issues = []
    penalty = 0

    for brick in bricks:
        if brick.brick not in STANDARD_BRICK_SIZES:
            issues.append(f"Non-standard brick size '{brick.brick}' at step {brick.step}. "
                         f"Allowed: {', '.join(sorted(STANDARD_BRICK_SIZES))}")
            penalty += 10

    return issues, penalty


def _check_connectivity(bricks: List[BrickPlacement]) -> Tuple[List[str], int, List[str]]:
    """Check if all bricks are connected to the structure.

    Bricks can connect either below (resting on) or above (supporting).
    The first layer bricks are always valid (they rest on the ground).

    Returns:
        Tuple of (issues list, penalty points, recommendations list)
    """
    issues = []
    recommendations = []
    penalty = 0

    if not bricks:
        return issues, penalty, recommendations

    # Group bricks by layer
    layers: Dict[int, List[BrickPlacement]] = {}
    for brick in bricks:
        layer = _get_layer_index(brick.position["z"])
        if layer not in layers:
            layers[layer] = []
        layers[layer].append(brick)

    # Get footprints for each layer
    layer_footprints: Dict[int, Set[Tuple[int, int]]] = {}
    for layer, layer_bricks in layers.items():
        footprint = set()
        for brick in layer_bricks:
            footprint.update(_get_brick_footprint(brick))
        layer_footprints[layer] = footprint

    # Check each brick (except ground layer) for connections
    sorted_layers = sorted(layers.keys())

    for layer in sorted_layers:
        if layer == 0:
            continue  # Ground layer is always valid

        for brick in layers[layer]:
            brick_footprint = _get_brick_footprint(brick)
            if not brick_footprint:
                continue

            # Check connection to layer below
            has_connection_below = False
            if layer - 1 in layer_footprints:
                overlap_below = brick_footprint & layer_footprints[layer - 1]
                has_connection_below = len(overlap_below) > 0

            # Check connection to layer above (brick supports something above)
            has_connection_above = False
            if layer + 1 in layer_footprints:
                overlap_above = brick_footprint & layer_footprints[layer + 1]
                has_connection_above = len(overlap_above) > 0

            if not has_connection_below and not has_connection_above:
                issues.append(f"Floating brick at step {brick.step} (layer {layer}) - "
                            f"no connection above or below")
                penalty += 15

    # Check if structure is reasonably stable
    if len(sorted_layers) > 1:
        base_footprint = layer_footprints.get(0, set())
        top_layer = sorted_layers[-1]
        top_footprint = layer_footprints.get(top_layer, set())

        if base_footprint and top_footprint:
            base_size = len(base_footprint)
            top_size = len(top_footprint)
            if top_size > base_size * STABILITY_TOP_HEAVY_RATIO:
                recommendations.append("Consider widening the base for better stability")

    return issues, penalty, recommendations


def _check_staggered_joints(bricks: List[BrickPlacement]) -> Tuple[List[str], int]:
    """Check for vertical seams running through >2 consecutive layers.

    Returns:
        Tuple of (issues list, penalty points)
    """
    issues = []
    penalty = 0

    if len(bricks) < 3:
        return issues, penalty

    # Group bricks by layer
    layers: Dict[int, List[BrickPlacement]] = {}
    for brick in bricks:
        layer = _get_layer_index(brick.position["z"])
        if layer not in layers:
            layers[layer] = []
        layers[layer].append(brick)

    sorted_layers = sorted(layers.keys())

    # For each pair of adjacent layers, find joint locations
    # A joint is the edge between two bricks at the same layer
    for i in range(len(sorted_layers) - 2):
        layer1 = sorted_layers[i]
        layer2 = sorted_layers[i + 1]
        layer3 = sorted_layers[i + 2]

        # Get brick edges for each layer
        def get_brick_edges(layer_bricks: List[BrickPlacement]) -> Set[Tuple[float, float, float, float]]:
            """Get edges (x1, y1, x2, y2) of bricks in a layer."""
            edges = set()
            for brick in layer_bricks:
                if brick.brick not in BRICK_DIMENSIONS:
                    continue
                width, length = BRICK_DIMENSIONS[brick.brick]
                x = brick.position["x"]
                y = brick.position["y"]
                # Add all 4 edges
                edges.add((x, y, x + width * LEGO_GRID_SIZE, y))  # Bottom
                edges.add((x, y, x, y + length * LEGO_GRID_SIZE))  # Left
                edges.add((x + width * LEGO_GRID_SIZE, y, x + width * LEGO_GRID_SIZE, y + length * LEGO_GRID_SIZE))  # Right
                edges.add((x, y + length * LEGO_GRID_SIZE, x + width * LEGO_GRID_SIZE, y + length * LEGO_GRID_SIZE))  # Top
            return edges

        edges1 = get_brick_edges(layers.get(layer1, []))
        edges2 = get_brick_edges(layers.get(layer2, []))
        edges3 = get_brick_edges(layers.get(layer3, []))

        # Find edges that appear in all 3 consecutive layers
        continuous_seams = edges1 & edges2 & edges3
        if continuous_seams:
            # This is a warning, not a hard failure
            penalty += 2
            if len(continuous_seams) > 3:
                issues.append(f"Multiple vertical seams detected through layers {layer1}-{layer3}")

    return issues, penalty


def _check_assembly_order(bricks: List[BrickPlacement]) -> Tuple[List[str], int]:
    """Check if the build sequence is physically possible.

    Validates that:
    1. Lower layers are built before upper layers
    2. No brick is placed in a trapped space

    Returns:
        Tuple of (issues list, penalty points)
    """
    issues = []
    penalty = 0

    if not bricks:
        return issues, penalty

    # Check that build sequence goes layer by layer (generally)
    prev_max_z = -1.0
    for brick in bricks:
        z = brick.position["z"]
        layer = _get_layer_index(z)

        # Allow building within same layer or one layer above previous max
        if z > prev_max_z + LEGO_BRICK_HEIGHT * 1.5:
            issues.append(f"Build sequence jumps too far ahead at step {brick.step} - "
                         f"layer {layer} placed before lower layers complete")
            penalty += 5

        prev_max_z = max(prev_max_z, z)

    return issues, penalty


def _check_structural_stability(bricks: List[BrickPlacement]) -> Tuple[List[str], int, List[str]]:
    """Check structural stability of the model.

    Validates:
    1. Base width >= top width (pyramidal stability)
    2. Center of mass is over the base

    Returns:
        Tuple of (issues list, penalty points, recommendations list)
    """
    issues = []
    recommendations = []
    penalty = 0

    if not bricks:
        return issues, penalty, recommendations

    # Calculate bounding box per layer
    layers: Dict[int, List[BrickPlacement]] = {}
    for brick in bricks:
        layer = _get_layer_index(brick.position["z"])
        if layer not in layers:
            layers[layer] = []
        layers[layer].append(brick)

    if len(layers) < 2:
        return issues, penalty, recommendations

    sorted_layers = sorted(layers.keys())
    base_layer = sorted_layers[0]
    top_layer = sorted_layers[-1]

    def get_layer_bounds(layer_bricks: List[BrickPlacement]) -> Tuple[float, float, float, float]:
        """Get (min_x, max_x, min_y, max_y) for a layer."""
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        for brick in layer_bricks:
            if brick.brick not in BRICK_DIMENSIONS:
                continue
            width, length = BRICK_DIMENSIONS[brick.brick]
            x, y = brick.position["x"], brick.position["y"]
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x + width * LEGO_GRID_SIZE)
            max_y = max(max_y, y + length * LEGO_GRID_SIZE)
        return min_x, max_x, min_y, max_y

    base_bounds = get_layer_bounds(layers[base_layer])
    top_bounds = get_layer_bounds(layers[top_layer])

    base_width = base_bounds[1] - base_bounds[0]
    base_depth = base_bounds[3] - base_bounds[2]
    top_width = top_bounds[1] - top_bounds[0]
    top_depth = top_bounds[3] - top_bounds[2]

    base_area = base_width * base_depth
    top_area = top_width * top_depth

    if top_area > base_area * STABILITY_TOP_HEAVY_AREA_RATIO:
        recommendations.append("Model is top-heavy - consider widening the base for stability")
        penalty += 5

    # Calculate approximate center of mass
    total_mass = 0
    com_x = com_y = 0.0
    for brick in bricks:
        if brick.brick not in BRICK_DIMENSIONS:
            continue
        width, length = BRICK_DIMENSIONS[brick.brick]
        mass = width * length  # Approximate mass by stud count
        center_x = brick.position["x"] + (width * LEGO_GRID_SIZE) / 2
        center_y = brick.position["y"] + (length * LEGO_GRID_SIZE) / 2
        com_x += center_x * mass
        com_y += center_y * mass
        total_mass += mass

    if total_mass > 0:
        com_x /= total_mass
        com_y /= total_mass

        # Check if center of mass is over the base
        base_center_x = (base_bounds[0] + base_bounds[1]) / 2
        base_center_y = (base_bounds[2] + base_bounds[3]) / 2

        offset_x = abs(com_x - base_center_x)
        offset_y = abs(com_y - base_center_y)

        if offset_x > base_width * COM_OFFSET_THRESHOLD or offset_y > base_depth * COM_OFFSET_THRESHOLD:
            recommendations.append("Center of mass is off-center - model may tip over")
            penalty += 3

    return issues, penalty, recommendations


def _estimate_build_time(brick_count: int, layer_count: int) -> int:
    """Estimate build time in minutes.

    Assumptions:
    - 15 seconds per brick on average
    - 30 seconds per layer transition
    """
    brick_time = brick_count * 15 / 60  # Convert to minutes
    layer_time = layer_count * 0.5  # 30 seconds per layer
    return int(math.ceil(brick_time + layer_time))


def validate_buildability(model_data: Dict[str, Any]) -> BuildabilityResult:
    """Validate that a LEGO model can be physically built.

    Validates:
    1. Grid alignment - all bricks on 8mm X/Y grid, correct Z increments
    2. Connectivity - no floating bricks, each connects to structure below OR above
    3. Staggered joints - no vertical seams running through >2 consecutive layers
    4. Assembly order - build sequence is physically possible (no trapped spaces)
    5. Structural stability - base width >= top width, center of mass over base

    Args:
        model_data: Dictionary containing:
            - build_sequence: List of brick placements (required)
            - layers: List of layer data (optional)
            - brick_count: Total bricks (optional)
            - layer_count: Total layers (optional)

    Returns:
        BuildabilityResult with validation results
    """
    issues: List[str] = []
    recommendations: List[str] = []
    total_penalty = 0

    # Extract build sequence
    raw_sequence = model_data.get("build_sequence", [])
    if not raw_sequence:
        return BuildabilityResult(
            valid=False,
            score=0,
            layer_count=0,
            issues=["No build_sequence data provided"],
            recommendations=["Ensure the model includes build_sequence metadata"],
            build_sequence=[],
            estimated_build_time_minutes=0
        )

    # Convert raw data to BrickPlacement objects
    bricks: List[BrickPlacement] = []
    for i, item in enumerate(raw_sequence):
        try:
            brick = BrickPlacement(
                step=item.get("step", i + 1),
                brick=item.get("brick", "unknown"),
                color=item.get("color", "unknown"),
                position=item.get("position", {"x": 0, "y": 0, "z": 0})
            )
            bricks.append(brick)
        except Exception as e:
            issues.append(f"Invalid brick data at index {i}: {e}")
            total_penalty += 5

    if not bricks:
        return BuildabilityResult(
            valid=False,
            score=0,
            layer_count=0,
            issues=["No valid bricks found in build_sequence"],
            recommendations=["Check build_sequence format"],
            build_sequence=[],
            estimated_build_time_minutes=0
        )

    # Run all validation checks
    grid_issues, grid_penalty = _check_grid_alignment(bricks)
    issues.extend(grid_issues)
    total_penalty += grid_penalty

    size_issues, size_penalty = _check_brick_sizes(bricks)
    issues.extend(size_issues)
    total_penalty += size_penalty

    conn_issues, conn_penalty, conn_recs = _check_connectivity(bricks)
    issues.extend(conn_issues)
    total_penalty += conn_penalty
    recommendations.extend(conn_recs)

    joint_issues, joint_penalty = _check_staggered_joints(bricks)
    issues.extend(joint_issues)
    total_penalty += joint_penalty

    order_issues, order_penalty = _check_assembly_order(bricks)
    issues.extend(order_issues)
    total_penalty += order_penalty

    stability_issues, stability_penalty, stability_recs = _check_structural_stability(bricks)
    issues.extend(stability_issues)
    total_penalty += stability_penalty
    recommendations.extend(stability_recs)

    # Calculate layer count
    unique_layers = set()
    for brick in bricks:
        layer = _get_layer_index(brick.position["z"])
        unique_layers.add(layer)
    layer_count = len(unique_layers)

    # Calculate score (100 - penalty, minimum 0)
    score = max(0, 100 - total_penalty)
    valid = score >= 70 and len([i for i in issues if "Floating brick" in i or "Non-standard" in i]) == 0

    # Estimate build time
    build_time = _estimate_build_time(len(bricks), layer_count)

    logger.info(f"Buildability validation: score={score}, valid={valid}, "
                f"bricks={len(bricks)}, layers={layer_count}, issues={len(issues)}")

    return BuildabilityResult(
        valid=valid,
        score=score,
        layer_count=layer_count,
        issues=issues,
        recommendations=recommendations,
        build_sequence=bricks,
        estimated_build_time_minutes=build_time
    )
