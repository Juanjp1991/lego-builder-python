"""Generation options for LEGO model generation.

This module defines model size tiers and custom settings validation
for controlling the complexity and size of generated LEGO models.
"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, field_validator, model_validator


class ModelSize(str, Enum):
    """Model size tiers for LEGO generation.

    Each tier defines brick count and layer count ranges:
    - TINY: Quick builds for simple models
    - SMALL: Standard builds (default)
    - MEDIUM: Detailed models
    - LARGE: Grand showcase pieces
    - EPIC: Highly detailed masterpieces
    - CUSTOM: User-defined ranges
    """
    TINY = "tiny"       # 15-30 bricks, 1-8 layers
    SMALL = "small"     # 30-60 bricks, 2-10 layers (default)
    MEDIUM = "medium"   # 60-120 bricks, 4-13 layers
    LARGE = "large"     # 120-200 bricks, 6-17 layers
    EPIC = "epic"       # 200-350 bricks, 10-23 layers
    CUSTOM = "custom"   # User-defined


MODEL_SIZE_SPECS: Dict[ModelSize, Dict[str, int]] = {
    ModelSize.TINY: {
        "min_bricks": 15,
        "max_bricks": 30,
        "min_layers": 1,
        "max_layers": 8,
        "display_name": "Quick Build"
    },
    ModelSize.SMALL: {
        "min_bricks": 30,
        "max_bricks": 60,
        "min_layers": 2,
        "max_layers": 10,
        "display_name": "Standard"
    },
    ModelSize.MEDIUM: {
        "min_bricks": 60,
        "max_bricks": 120,
        "min_layers": 4,
        "max_layers": 13,
        "display_name": "Detailed"
    },
    ModelSize.LARGE: {
        "min_bricks": 120,
        "max_bricks": 200,
        "min_layers": 6,
        "max_layers": 17,
        "display_name": "Grand"
    },
    ModelSize.EPIC: {
        "min_bricks": 200,
        "max_bricks": 350,
        "min_layers": 10,
        "max_layers": 23,
        "display_name": "Epic"
    },
}


class CustomSizeSettings(BaseModel):
    """Custom size settings for user-defined model complexity.

    Attributes:
        min_bricks: Minimum number of bricks (>= 10)
        max_bricks: Maximum number of bricks (<= 1000)
        min_layers: Minimum number of layers (>= 1)
        max_layers: Maximum number of layers (<= 50)
    """
    min_bricks: int
    max_bricks: int
    min_layers: int
    max_layers: int

    @field_validator('min_bricks')
    @classmethod
    def validate_min_bricks(cls, v: int) -> int:
        if v < 10:
            raise ValueError('min_bricks must be >= 10')
        return v

    @field_validator('max_bricks')
    @classmethod
    def validate_max_bricks(cls, v: int) -> int:
        if v > 1000:
            raise ValueError('max_bricks must be <= 1000')
        return v

    @field_validator('min_layers')
    @classmethod
    def validate_min_layers(cls, v: int) -> int:
        if v < 1:
            raise ValueError('min_layers must be >= 1')
        return v

    @field_validator('max_layers')
    @classmethod
    def validate_max_layers(cls, v: int) -> int:
        if v > 50:
            raise ValueError('max_layers must be <= 50')
        return v

    @model_validator(mode='after')
    def validate_ranges(self) -> 'CustomSizeSettings':
        if self.max_bricks < self.min_bricks:
            raise ValueError('max_bricks must be >= min_bricks')
        if self.max_layers < self.min_layers:
            raise ValueError('max_layers must be >= min_layers')
        return self


class GenerationOptions(BaseModel):
    """Options for controlling LEGO model generation.

    Attributes:
        model_size: The size tier for the model (default: SMALL)
        custom_settings: Custom brick/layer ranges (required if model_size is CUSTOM)
        complexity: Legacy complexity setting from Story 2.5 ('simple' | 'normal')
    """
    model_size: ModelSize = ModelSize.SMALL
    custom_settings: Optional[CustomSizeSettings] = None
    complexity: str = "normal"  # 'simple' | 'normal' from Story 2.5

    @model_validator(mode='after')
    def validate_custom_requires_settings(self) -> 'GenerationOptions':
        if self.model_size == ModelSize.CUSTOM and self.custom_settings is None:
            raise ValueError('custom_settings is required when model_size is CUSTOM')
        return self

    def get_size_spec(self) -> Dict[str, Any]:
        """Get the size specification for this generation options.

        Returns:
            Dictionary with min_bricks, max_bricks, min_layers, max_layers
        """
        if self.model_size == ModelSize.CUSTOM and self.custom_settings:
            return {
                "min_bricks": self.custom_settings.min_bricks,
                "max_bricks": self.custom_settings.max_bricks,
                "min_layers": self.custom_settings.min_layers,
                "max_layers": self.custom_settings.max_layers,
                "display_name": "Custom"
            }
        return MODEL_SIZE_SPECS.get(self.model_size, MODEL_SIZE_SPECS[ModelSize.SMALL])


def get_size_spec(model_size: ModelSize, custom_settings: Optional[CustomSizeSettings] = None) -> Dict[str, Any]:
    """Get the size specification for a given model size.

    Args:
        model_size: The model size tier
        custom_settings: Custom settings (required if model_size is CUSTOM)

    Returns:
        Dictionary with min_bricks, max_bricks, min_layers, max_layers, display_name

    Raises:
        ValueError: If model_size is CUSTOM but custom_settings is None
    """
    if model_size == ModelSize.CUSTOM:
        if custom_settings is None:
            raise ValueError('custom_settings is required when model_size is CUSTOM')
        return {
            "min_bricks": custom_settings.min_bricks,
            "max_bricks": custom_settings.max_bricks,
            "min_layers": custom_settings.min_layers,
            "max_layers": custom_settings.max_layers,
            "display_name": "Custom"
        }
    return MODEL_SIZE_SPECS.get(model_size, MODEL_SIZE_SPECS[ModelSize.SMALL])
