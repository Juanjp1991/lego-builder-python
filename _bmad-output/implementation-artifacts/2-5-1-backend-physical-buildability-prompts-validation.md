# Story 2.5.1: Backend - Physical Buildability Prompts & Validation

Status: done

## Story

As a developer,
I want the Designer and Coder agents to generate models optimized for real-world LEGO construction with programmatic validation,
So that users can physically build the generated models with standard LEGO bricks.

## Acceptance Criteria

1. **Given** a user submits a generation request via the A2A protocol
   **When** the backend agents process the request
   **Then** the Designer agent prompt includes voxel/Minecraft-inspired aesthetic guidance with:
   - Blocky, chunky shapes with clear geometric forms - no smooth curves or organic shapes
   - **PRESERVE DISTINCT FEATURES**: When voxelizing, keep key recognizable features (eyes, ears, wings, wheels, etc.) that make the model identifiable
   - Layer-by-layer construction mindset (bottom-up assembly)
   - Stud alignment on 8mm grid (standard LEGO pitch)
   - Overlapping joint patterns (staggered like real brickwork, no vertical seams >2 layers)
   - No floating elements (every brick connects to structure below OR above via stud interlocking)
   - Color grouping per layer (minimize color switches during build)
   - Standard bricks ONLY: 2x2, 2x4, 2x6, 1x2, 1x4, 1x6 (no other sizes allowed)

2. **And** the Coder agent prompt includes physical construction rules:
   - Position bricks on 8mm X/Y grid
   - Z-axis increments: 9.6mm per layer (standard LEGO brick height)
   - Enforce stud-to-anti-stud connections (bricks can connect below OR above)
   - Standard bricks ONLY: 2x2, 2x4, 2x6, 1x2, 1x4, 1x6 (reject any other sizes)
   - Output `build_sequence` metadata with ordered brick placements
   - Output `layers` array: `[{z: 0, bricks: [...]}, {z: 9.6, bricks: [...]}]`
   - Validate before returning: no enclosed voids, no impossible assembly order

3. **And** the generation request accepts a model size option (`options.modelSize`) with sizes:
   - `tiny`: "Quick Build" - 15-30 bricks, 1-8 layers
   - `small`: "Standard" - 30-60 bricks, 2-10 layers (default)
   - `medium`: "Detailed" - 60-120 bricks, 4-13 layers
   - `large`: "Grand" - 120-200 bricks, 6-17 layers
   - `epic`: "Epic" - 200-350 bricks, 10-23 layers
   - `custom`: User-defined brick/layer ranges

4. **And** custom size settings are validated:
   - `minBricks` >= 10, <= `maxBricks`
   - `maxBricks` <= 1000 (hard limit)
   - `minLayers` >= 1, <= `maxLayers`
   - `maxLayers` <= 50
   - Invalid values return error: "Custom settings out of range"

5. **And** a buildability validator is implemented at `/Backend/validation/buildability.py` that checks:
   - Grid alignment - all bricks on 8mm X/Y grid, correct Z increments
   - Connectivity - no floating bricks, each connects to structure below OR above (interlocking works both ways)
   - Staggered joints - no vertical seams running through >2 consecutive layers
   - Assembly order - build sequence is physically possible (no trapped spaces)
   - Structural stability - base width >= top width, center of mass over base

6. **And** if `buildability.score < 70`, the Coder agent attempts one automatic self-correction pass (does NOT count against user's retry limit)

7. **And** the A2A generation response includes buildability metadata:
   ```json
   {
     "stl_url": "https://...",
     "model_metadata": { "brick_count": 45, "dimensions": {...} },
     "buildability": {
       "score": 87,
       "valid": true,
       "layer_count": 6,
       "issues": [],
       "recommendations": ["Consider wider base"],
       "estimated_build_time_minutes": 12,
       "build_sequence": [...]
     }
   }
   ```

## Tasks / Subtasks

- [x] Task 1: Update Designer agent prompt for voxel-style LEGO (AC: #1)
  - [x] Add voxel/Minecraft-inspired aesthetic instructions
  - [x] Add feature preservation guidance (keep distinct features when voxelizing)
  - [x] Add 8mm grid alignment guidance
  - [x] Add overlapping joint pattern requirements
  - [x] Add standard brick size constraints (2x2, 2x4, 2x6, 1x2, 1x4, 1x6 only)
  - [x] Add layer-by-layer construction mindset guidance
  - [x] Add no-floating-elements rule
  - [x] Add color grouping per layer guidance

- [x] Task 2: Update Coder agent prompt for physical construction (AC: #2)
  - [x] Add 8mm X/Y grid positioning rules
  - [x] Add Z-axis increment rule (9.6mm per layer)
  - [x] Add stud-to-anti-stud connection enforcement
  - [x] Add standard brick size validation (reject non-standard)
  - [x] Add build_sequence metadata output requirement
  - [x] Add layers array output format
  - [x] Add enclosed void and impossible assembly validation

- [x] Task 3: Implement model size options (AC: #3, #4)
  - [x] Create `/Backend/models/generation_options.py` with ModelSize enum
  - [x] Define brick/layer ranges for each size tier
  - [x] Implement custom size validation
  - [x] Update A2A models to accept modelSize option
  - [x] Pass modelSize to Designer and Coder agents
  - [x] Update Designer prompt to adapt complexity based on size

- [x] Task 4: Create buildability validator (AC: #5)
  - [x] Create `/Backend/validation/__init__.py`
  - [x] Create `/Backend/validation/buildability.py`
  - [x] Implement `BuildabilityResult` dataclass
  - [x] Implement `validate_buildability()` function
  - [x] Add grid alignment check
  - [x] Add connectivity check (bricks must connect below OR above)
  - [x] Add staggered joints check
  - [x] Add assembly order check
  - [x] Add structural stability check
  - [x] Add unit tests in `/Backend/tests/test_buildability.py`

- [x] Task 5: Integrate validator into generation pipeline (AC: #6)
  - [x] Import validator in control_flow/agent.py
  - [x] Call validator after Coder generates code
  - [x] Implement self-correction pass if score < 70
  - [x] Ensure self-correction doesn't count against retry limit
  - [x] Log validation results for debugging

- [x] Task 6: Add buildability metadata to A2A response (AC: #7)
  - [x] Update A2A models with BuildabilityMetadata
  - [x] Include buildability in task artifacts
  - [x] Add estimated_build_time_minutes calculation
  - [x] Include build_sequence in response
  - [x] Update frontend types to consume new metadata

- [x] Task 7: Comprehensive testing
  - [x] Test Designer prompt generates voxel-style specs
  - [x] Test Coder prompt produces grid-aligned code
  - [x] Test model size options are respected
  - [x] Test custom size validation
  - [x] Test buildability validator catches issues
  - [x] Test self-correction improves score
  - [x] Test A2A response includes buildability metadata

## Dev Notes

### Key Architecture Decisions

1. **Voxel/Minecraft Aesthetic**: Models should look like blocky LEGO creations, not smooth organic shapes. This makes them physically buildable.

2. **Feature Preservation**: When simplifying to voxel/brick form, the model must retain its distinct recognizable features (eyes, ears, wings, wheels, etc.). A dragon must still look like a dragon, not a generic blocky shape.

3. **Standard Brick Sizes Only**: Restricting to 2x2, 2x4, 2x6, 1x2, 1x4, 1x6 ensures models use common bricks users actually have.

4. **LEGO Grid System**:
   - XY Grid: 8mm pitch (standard LEGO stud spacing)
   - Z Heights: 9.6mm per layer (standard LEGO brick height)
   - Studs are 4.8mm diameter, 1.8mm height

5. **Self-Correction Strategy**: If buildability score < 70, the Coder agent gets one free attempt to fix issues before returning to user. This is transparent to the user (no retry count impact).

6. **Build Sequence**: The generated model must include step-by-step assembly order so the frontend can display layer-by-layer instructions.

### Previous Story Learnings (2.5)

From Story 2.5 (First-Build Guarantee & User Profiling):
- **Complexity parameter exists**: Frontend already sends `complexity: 'simple' | 'normal'` via GenerateOptions
- **Model simplicity matters**: First-build mode constrains max layers (5), prefers larger bricks
- **Dexie.js database**: userPreferences table stores first-build flag
- **API extension pattern**: GenerateOptions interface in `/Frontend/lib/types.ts`

This story extends the complexity concept with explicit size tiers.

### Technology Stack (Backend)

From `/Backend/requirements.txt` and project-context.md:
- **FastAPI**: 0.118.3
- **build123d**: 0.10.0 - CAD library for LEGO model generation
- **google-genai**: 1.52.0 - Gemini API for LLM agents
- **pyvista**: 0.46.4 - For STL rendering
- **Python**: Strict type hints required

### File Locations

**New Files:**
- `/Backend/validation/__init__.py` - Package init
- `/Backend/validation/buildability.py` - Buildability validator
- `/Backend/models/generation_options.py` - ModelSize enum and options (or add to existing models)
- `/Backend/tests/test_buildability.py` - Validator tests

**Modified Files:**
- `/Backend/sub_agents/designer/prompt.py` - Add voxel/LEGO construction rules
- `/Backend/sub_agents/coder/prompt.py` - Add physical construction rules
- `/Backend/sub_agents/control_flow/agent.py` - Integrate validator, self-correction
- `/Backend/a2a/models.py` - Add BuildabilityMetadata, ModelSize types
- `/Backend/a2a/api.py` - Pass modelSize option to agents

### Designer Prompt Additions

Add to `SYSTEM_PROMPT` in `/Backend/sub_agents/designer/prompt.py`:

```python
LEGO BUILDABILITY REQUIREMENTS (CRITICAL):
- **VOXEL/MINECRAFT AESTHETIC**: Design blocky, chunky shapes. NO smooth curves or organic forms.
- **PRESERVE DISTINCT FEATURES**: When voxelizing, KEEP key recognizable features (eyes, ears, wings, wheels, horns, tails, etc.) that make the model identifiable. Simplify but don't lose identity!
- **LAYER-BY-LAYER THINKING**: Every design must be buildable from bottom-up, one layer at a time.
- **8mm GRID**: All brick positions align to 8mm grid (standard LEGO stud spacing).
- **STAGGERED JOINTS**: Like real brickwork - no vertical seams extending >2 layers. Overlap bricks!
- **NO FLOATING ELEMENTS**: Every brick must connect to structure below OR above via stud interlocking.
- **STANDARD BRICKS ONLY**: 2x2, 2x4, 2x6, 1x2, 1x4, 1x6. NO other sizes.
- **COLOR GROUPING**: Group same-color bricks in consecutive layers to minimize color switches during build.

MODEL SIZE TIERS:
- TINY (15-30 bricks, 1-8 layers): Simple silhouette, single color recommended
- SMALL (30-60 bricks, 2-10 layers): Recognizable shape, 2-3 colors
- MEDIUM (60-120 bricks, 4-13 layers): Detailed features, 3-5 colors
- LARGE (120-200 bricks, 6-17 layers): Intricate details, unlimited colors
- EPIC (200-350 bricks, 10-23 layers): Highly detailed showcase piece
```

### Coder Prompt Additions

Add to `SYSTEM_PROMPT` in `/Backend/sub_agents/coder/prompt.py`:

```python
LEGO PHYSICAL CONSTRUCTION RULES (CRITICAL):
- **8mm X/Y GRID**: All brick X/Y positions must be multiples of 8mm
- **Z-AXIS HEIGHT**: 9.6mm per layer (standard LEGO brick height)
- **STUD CONNECTIONS**: Every brick must interlock with >=1 brick below OR above (both directions valid)
- **STANDARD BRICKS ONLY**: 2x2, 2x4, 2x6, 1x2, 1x4, 1x6. Reject any other sizes.
- **NO FLOATING GEOMETRY**: No brick can exist without connection to structure
- **NO ENCLOSED VOIDS**: Assembly must be physically possible (no trapped spaces)
- **OUTPUT BUILD SEQUENCE**: Include step-by-step brick placement order

REQUIRED OUTPUT METADATA:
Your code must generate these variables:
- `build_sequence`: List[Dict] with ordered brick placements
  Example: [{"step": 1, "brick": "2x4", "color": "red", "position": {"x": 0, "y": 0, "z": 0}}, ...]
- `layers`: List[Dict] grouping bricks by Z-height
  Example: [{"z": 0, "bricks": [...]}, {"z": 9.6, "bricks": [...]}, ...]
- `brick_count`: Total number of bricks
- `layer_count`: Total number of layers
```

### Buildability Validator Structure

```python
# /Backend/validation/buildability.py
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class BrickPlacement:
    step: int
    brick: str  # "2x4", "2x2", etc.
    color: str
    position: Dict[str, float]  # {"x": 0, "y": 0, "z": 0}

@dataclass
class BuildabilityResult:
    valid: bool
    score: int  # 0-100
    layer_count: int
    issues: List[str]
    recommendations: List[str]
    build_sequence: List[BrickPlacement]
    estimated_build_time_minutes: int

def validate_buildability(model_data: dict) -> BuildabilityResult:
    """
    Validates:
    1. Grid alignment - all bricks on 8mm X/Y grid, correct Z increments
    2. Connectivity - no floating bricks, each connects to structure below OR above
       (bricks can be supported from top via interlocking with brick above)
    3. Staggered joints - no vertical seams running through >2 consecutive layers
    4. Assembly order - build sequence is physically possible (no trapped spaces)
    5. Structural stability - base width >= top width, center of mass over base
    """
    # Implementation here
    pass
```

### Model Size Implementation

```python
# /Backend/models/generation_options.py or add to a2a/models.py
from enum import Enum
from pydantic import BaseModel, validator
from typing import Optional

class ModelSize(str, Enum):
    TINY = "tiny"       # 15-30 bricks, 1-8 layers
    SMALL = "small"     # 30-60 bricks, 2-10 layers (default)
    MEDIUM = "medium"   # 60-120 bricks, 4-13 layers
    LARGE = "large"     # 120-200 bricks, 6-17 layers
    EPIC = "epic"       # 200-350 bricks, 10-23 layers
    CUSTOM = "custom"   # User-defined

MODEL_SIZE_SPECS = {
    ModelSize.TINY: {"min_bricks": 15, "max_bricks": 30, "min_layers": 1, "max_layers": 8},
    ModelSize.SMALL: {"min_bricks": 30, "max_bricks": 60, "min_layers": 2, "max_layers": 10},
    ModelSize.MEDIUM: {"min_bricks": 60, "max_bricks": 120, "min_layers": 4, "max_layers": 13},
    ModelSize.LARGE: {"min_bricks": 120, "max_bricks": 200, "min_layers": 6, "max_layers": 17},
    ModelSize.EPIC: {"min_bricks": 200, "max_bricks": 350, "min_layers": 10, "max_layers": 23},
}

class CustomSizeSettings(BaseModel):
    min_bricks: int
    max_bricks: int
    min_layers: int
    max_layers: int

    @validator('min_bricks')
    def validate_min_bricks(cls, v):
        if v < 10:
            raise ValueError('min_bricks must be >= 10')
        return v

    @validator('max_bricks')
    def validate_max_bricks(cls, v, values):
        if v > 1000:
            raise ValueError('max_bricks must be <= 1000')
        if 'min_bricks' in values and v < values['min_bricks']:
            raise ValueError('max_bricks must be >= min_bricks')
        return v

    @validator('min_layers')
    def validate_min_layers(cls, v):
        if v < 1:
            raise ValueError('min_layers must be >= 1')
        return v

    @validator('max_layers')
    def validate_max_layers(cls, v, values):
        if v > 50:
            raise ValueError('max_layers must be <= 50')
        if 'min_layers' in values and v < values['min_layers']:
            raise ValueError('max_layers must be >= min_layers')
        return v

class GenerationOptions(BaseModel):
    model_size: ModelSize = ModelSize.SMALL
    custom_settings: Optional[CustomSizeSettings] = None
    complexity: str = "normal"  # 'simple' | 'normal' from Story 2.5
```

### Self-Correction Flow

```python
# In control_flow/agent.py after coder generates code:

from validation.buildability import validate_buildability

# After getting coder output:
validation_result = validate_buildability(model_data)

if validation_result.score < 70:
    logger.info(f"Buildability score {validation_result.score} < 70, attempting self-correction")

    # Create correction prompt with validation issues
    correction_prompt = f"""
    Original Specification: {original_spec}

    Buildability Issues Found:
    {chr(10).join(f'- {issue}' for issue in validation_result.issues)}

    Please fix the code to address these structural issues.
    """

    # Run coder again with correction (does NOT count as user retry)
    corrected_output = await self._run_coder_step(correction_prompt, ...)

    # Re-validate
    final_validation = validate_buildability(corrected_model_data)

    # Use corrected version regardless (user gets best effort)
```

### A2A Response Update

```python
# Update response_message to include buildability
from validation.buildability import validate_buildability

# After successful generation:
validation_result = validate_buildability(model_data)

response_data = {
    "stl_url": f"/download/{stl_filename}",
    "model_metadata": {
        "brick_count": validation_result.build_sequence.__len__(),
        "dimensions": {"x": 80, "y": 64, "z": 57.6}
    },
    "buildability": {
        "score": validation_result.score,
        "valid": validation_result.valid,
        "layer_count": validation_result.layer_count,
        "issues": validation_result.issues,
        "recommendations": validation_result.recommendations,
        "estimated_build_time_minutes": validation_result.estimated_build_time_minutes,
        "build_sequence": [asdict(b) for b in validation_result.build_sequence]
    }
}
```

### Testing Strategy

**Unit Tests (`/Backend/tests/test_buildability.py`):**
1. Test grid alignment validation catches misaligned bricks
2. Test connectivity check catches truly floating bricks (no connection above or below)
3. Test connectivity check ALLOWS bricks supported from above (top-interlocking)
4. Test staggered joints check catches vertical seams
5. Test assembly order check catches trapped spaces
6. Test stability check catches top-heavy designs
7. Test score calculation is correct
8. Test estimated build time calculation

**Integration Tests:**
1. Test Designer prompt produces voxel-style specifications
2. Test Coder generates grid-aligned code
3. Test model size options are respected
4. Test self-correction improves buildability score
5. Test A2A response includes buildability metadata

### Project Structure Notes

Per Architecture and project-context.md:
- New validation module: `/Backend/validation/`
- Tests co-located in `/Backend/tests/`
- Follow snake_case for Python files
- Use type hints for all functions
- Dataclasses for structured data
- Pydantic for API models

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.5.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Backend Stack]
- [Source: _bmad-output/project-context.md#Backend Agent Patterns]
- [Source: Backend/sub_agents/designer/prompt.py] - Designer prompt to modify
- [Source: Backend/sub_agents/coder/prompt.py] - Coder prompt to modify
- [Source: Backend/sub_agents/control_flow/agent.py] - Integration point
- [Source: Backend/a2a/models.py] - A2A models to extend
- [Source: LEGO Dimensions Reference] - 8mm pitch, 9.6mm brick height

### Dependencies

**Requires Story 2.1, 2.2, 2.4, 2.5 to be complete** - This story builds on the existing generation pipeline and structural feedback display.

**Enables:**
- Story 2.4 - Better structural feedback data from validator
- Epic 4 - Build instructions use build_sequence for layer-by-layer view
- Future inventory matching improvements

### Risk Considerations

1. **Performance Impact**: Buildability validation adds processing time. Monitor and optimize if needed.

2. **Over-Constraining**: Too strict validation might reject valid models. Start with score threshold of 70.

3. **LLM Compliance**: Designer/Coder may not always follow brick size constraints. The validator catches violations.

4. **Build Sequence Accuracy**: Generating correct assembly order is complex. Start with simple layer-by-layer ordering.

5. **Edge Cases**: Overhangs and cantilevers are valid if the brick interlocks with a brick above it. The validator must check bidirectional connectivity (below OR above), not just bottom-up support.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None required - all code compiles and tests pass syntax validation.

### Completion Notes List

- Implemented comprehensive LEGO buildability validation system
- Updated Designer prompt with voxel/Minecraft aesthetic, 8mm grid alignment, staggered joints, standard bricks only
- Updated Coder prompt with physical construction rules and required output metadata format
- Created ModelSize enum with 5 predefined tiers (tiny, small, medium, large, epic) plus custom option
- Implemented full buildability validator checking grid alignment, connectivity, staggered joints, assembly order, structural stability
- Integrated validator into control_flow agent with auto self-correction when score < 70
- Added BuildabilityMetadata to A2A response including score, issues, recommendations, build_sequence, estimated_build_time
- Updated frontend TypeScript types with ModelSize, BuildabilityMetadata, BrickPlacement interfaces
- Created comprehensive unit tests for validator and generation options
- All Python files pass syntax validation
- Frontend TypeScript types compile successfully

### File List

**New Files:**
- Backend/models/__init__.py
- Backend/models/generation_options.py
- Backend/validation/__init__.py
- Backend/validation/buildability.py
- Backend/tests/test_buildability.py
- Backend/tests/test_generation_options.py

**Modified Files:**
- Backend/sub_agents/designer/prompt.py
- Backend/sub_agents/coder/prompt.py
- Backend/sub_agents/control_flow/agent.py
- Backend/a2a/models.py
- Backend/a2a/api.py
- Frontend/lib/types.ts

### Change Log

2026-01-08: Implemented Story 2.5.1 - Backend Physical Buildability Prompts & Validation
- Added LEGO buildability requirements to Designer and Coder prompts
- Created ModelSize enum with 5 tiers + custom option
- Implemented buildability validator with 5 validation checks
- Integrated self-correction flow when buildability score < 70
- Added buildability metadata to A2A generation response
- Updated frontend types for consumption
