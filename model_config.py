"""
Central Model Configuration for Financial Spreader

This module defines ALL available models in one place to ensure consistency
between the regular app and testing lab. Adding a new model requires only
updating this file.

Architecture:
- Single source of truth for model definitions
- Supports both OpenAI and Anthropic models
- Backend and frontend share the same configuration
- Easy to extend with new models
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ModelProvider(str, Enum):
    """Model provider enum"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class ModelCapability(str, Enum):
    """Model capabilities"""
    VISION = "vision"  # Supports image inputs
    REASONING = "reasoning"  # Has reasoning/chain-of-thought capabilities
    STRUCTURED_OUTPUT = "structured_output"  # Supports structured output


class ModelDefinition(BaseModel):
    """Complete model definition"""
    id: str = Field(description="Model identifier used in API calls")
    name: str = Field(description="Display name for UI")
    provider: ModelProvider = Field(description="Model provider (openai, anthropic)")
    description: Optional[str] = Field(default=None, description="Model description for UI")
    capabilities: List[ModelCapability] = Field(
        default_factory=list,
        description="List of model capabilities"
    )
    is_default: bool = Field(default=False, description="Whether this is the default model")
    supports_reasoning_effort: bool = Field(
        default=False,
        description="Whether model supports reasoning_effort parameter (OpenAI)"
    )
    supports_extended_thinking: bool = Field(
        default=False,
        description="Whether model supports extended_thinking parameter (Anthropic)"
    )
    recommended_use: Optional[str] = Field(
        default=None,
        description="Recommended use case for this model"
    )
    cost_tier: str = Field(
        default="medium",
        description="Relative cost tier: low, medium, high, premium"
    )
    
    def to_dict(self) -> Dict:
        """Export as dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider.value,
            "description": self.description,
            "capabilities": [c.value for c in self.capabilities],
            "is_default": self.is_default,
            "supports_reasoning_effort": self.supports_reasoning_effort,
            "supports_extended_thinking": self.supports_extended_thinking,
            "recommended_use": self.recommended_use,
            "cost_tier": self.cost_tier
        }
    
    def to_api_model(self) -> Dict:
        """Export as AvailableModel format for testing API"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description or ""
        }


# =============================================================================
# MODEL REGISTRY - SINGLE SOURCE OF TRUTH
# =============================================================================

MODEL_REGISTRY: List[ModelDefinition] = [
    # =========================================================================
    # ANTHROPIC MODELS (Latest - Claude 4.5 Series)
    # =========================================================================
    ModelDefinition(
        id="claude-opus-4-5",
        name="Claude Opus 4.5",
        provider=ModelProvider.ANTHROPIC,
        description="Most capable Claude model with superior reasoning and analysis",
        capabilities=[
            ModelCapability.VISION,
            ModelCapability.REASONING,
            ModelCapability.STRUCTURED_OUTPUT
        ],
        is_default=True,  # Set as default for highest accuracy
        supports_reasoning_effort=False,  # Anthropic doesn't use reasoning_effort
        supports_extended_thinking=True,   # Supports extended thinking
        recommended_use="Complex financial documents requiring highest accuracy",
        cost_tier="premium"
    ),
    
    ModelDefinition(
        id="claude-sonnet-4-5",
        name="Claude Sonnet 4.5",
        provider=ModelProvider.ANTHROPIC,
        description="Balanced performance and speed with excellent vision capabilities",
        capabilities=[
            ModelCapability.VISION,
            ModelCapability.REASONING,
            ModelCapability.STRUCTURED_OUTPUT
        ],
        is_default=False,
        supports_reasoning_effort=False,  # Anthropic doesn't use reasoning_effort
        supports_extended_thinking=True,   # Supports extended thinking
        recommended_use="General purpose financial spreading with excellent quality",
        cost_tier="medium"
    ),
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_all_models() -> List[ModelDefinition]:
    """Get all available models"""
    return MODEL_REGISTRY


def get_model_by_id(model_id: str) -> Optional[ModelDefinition]:
    """Get a specific model by ID"""
    return next((m for m in MODEL_REGISTRY if m.id == model_id), None)


def get_default_model() -> ModelDefinition:
    """Get the default model"""
    default = next((m for m in MODEL_REGISTRY if m.is_default), None)
    if not default:
        # Fallback to first model if no default set
        return MODEL_REGISTRY[0]
    return default


def get_models_by_provider(provider: ModelProvider) -> List[ModelDefinition]:
    """Get all models from a specific provider"""
    return [m for m in MODEL_REGISTRY if m.provider == provider]


def get_models_with_capability(capability: ModelCapability) -> List[ModelDefinition]:
    """Get all models with a specific capability"""
    return [m for m in MODEL_REGISTRY if capability in m.capabilities]


def get_vision_models() -> List[ModelDefinition]:
    """Get all models that support vision (required for PDF processing)"""
    return get_models_with_capability(ModelCapability.VISION)


def export_for_api() -> List[Dict]:
    """Export model list for API responses (testing format)"""
    return [m.to_api_model() for m in MODEL_REGISTRY]


def export_for_frontend() -> List[Dict]:
    """Export model list for frontend consumption (full details)"""
    return [m.to_dict() for m in MODEL_REGISTRY]


# =============================================================================
# VALIDATION
# =============================================================================

def validate_model_for_spreading(model_id: str) -> tuple[bool, Optional[str]]:
    """
    Validate that a model is suitable for financial spreading.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    model = get_model_by_id(model_id)
    
    if not model:
        return False, f"Unknown model: {model_id}"
    
    # Vision capability is required for PDF processing
    if ModelCapability.VISION not in model.capabilities:
        return False, f"Model {model_id} does not support vision (required for PDF processing)"
    
    # Structured output is required
    if ModelCapability.STRUCTURED_OUTPUT not in model.capabilities:
        return False, f"Model {model_id} does not support structured output"
    
    return True, None


# =============================================================================
# MODEL CONFIGURATION EXPORT
# =============================================================================

# Export as simple dict for backward compatibility
AVAILABLE_MODELS_DICT = {
    m.id: {
        "name": m.name,
        "provider": m.provider.value,
        "description": m.description,
        "is_default": m.is_default
    }
    for m in MODEL_REGISTRY
}

# Get default model ID for environment variable fallback
DEFAULT_MODEL_ID = get_default_model().id
