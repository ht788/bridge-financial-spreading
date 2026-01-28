# Model Configuration Guide

## Overview

The Bridge Financial Spreader supports multiple AI models from both OpenAI and Anthropic. All available models are defined in a **centralized configuration** to ensure consistency between the regular app and testing lab.

## Latest Models Available

### ✨ Anthropic Claude 4.5 Series (Recommended)

- **Claude Sonnet 4.5** (`claude-sonnet-4-20250514`) - **DEFAULT**
  - Best balance of speed, accuracy, and cost
  - Excellent vision capabilities for financial documents
  - Recommended for general-purpose financial spreading

- **Claude Opus 4.5** (`claude-opus-4-5`) - **PREMIUM**
  - Most capable Claude model
  - Superior reasoning and analysis
  - Use for complex financial documents requiring highest accuracy

### OpenAI Models

#### GPT-5 Series (Reasoning Focused)
- **GPT-5.2** (`gpt-5.2`) - Latest with enhanced reasoning
- **GPT-5** (`gpt-5`) - Strong reasoning capabilities

#### GPT-4o Series (Vision Focused)
- **GPT-4o** (`gpt-4o`) - Fast, reliable vision extraction
- **GPT-4o Mini** (`gpt-4o-mini`) - Cost-efficient for simple documents

#### O-Series (Reasoning Specialized)
- **O1** (`o1`) - Reasoning-first for complex problems
- **O1 Mini** (`o1-mini`) - Efficient reasoning
- **O3 Mini** (`o3-mini`) - Latest mini reasoning model

## Architecture

### Centralized Configuration

All models are defined in **ONE place** to prevent configuration drift:

```
Backend:  model_config.py       (Python - Single source of truth)
Frontend: modelConfig.ts        (TypeScript - Mirrors backend)
```

This ensures:
- ✅ No need to update models in multiple files
- ✅ Consistency between regular app and testing lab
- ✅ Easy to add new models (just update model_config.py)
- ✅ Type safety with Pydantic validation

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `langchain-anthropic>=0.3.0` - For Claude models
- `langchain-openai>=0.2.0` - For GPT models
- `anthropic>=0.40.0` - Anthropic SDK
- `openai>=1.50.0` - OpenAI SDK

### 2. Configure API Keys

Copy `env.example` to `.env` and add your API keys:

```bash
# For Claude models (Recommended)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# For GPT models
OPENAI_API_KEY=sk-your-key-here

# LangSmith for observability (optional but recommended)
LANGSMITH_API_KEY=lsv2_pt_your-key-here
LANGSMITH_PROJECT=financial-spreader-v1
```

### 3. Choose Default Model

Set your preferred model in `.env`:

```bash
# Option 1: Use Claude Sonnet (recommended)
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# Option 2: Use GPT-5.2
OPENAI_MODEL=gpt-5.2
```

## Usage

### Regular App (Web UI)

1. Upload your financial statement PDF
2. Click "Advanced Options"
3. Select model from dropdown (organized by provider)
4. Process the document

The dropdown groups models by provider:
```
Anthropic (Claude)
  └─ Claude Opus 4.5 [Premium]
  └─ Claude Sonnet 4.5 [Default]

OpenAI
  └─ GPT-5.2
  └─ GPT-5
  └─ GPT-4o
  └─ GPT-4o Mini
  └─ O1
  └─ O1 Mini
  └─ O3 Mini
```

### Testing Lab

1. Navigate to Testing tab
2. Select company and model
3. Run test
4. Compare results across models

### Command Line

```bash
# Use default model
python main.py example.pdf income

# Override model
python main.py example.pdf income --model claude-opus-4-5
python main.py example.pdf income --model gpt-5.2
```

## Model Selection Priority

Models are selected in this order:

1. **CLI/API Override** (highest priority)
   ```python
   spread_financials(file, doc_type, model_override="claude-sonnet-4-20250514")
   ```

2. **LangSmith Hub Configuration** (recommended for production)
   - Configure in LangSmith UI
   - Changes take effect immediately without code deploy

3. **Environment Variables** (`.env` file)
   ```bash
   ANTHROPIC_MODEL=claude-sonnet-4-20250514
   # or
   OPENAI_MODEL=gpt-5.2
   ```

4. **Code Default** (last resort)
   - Defined in `model_config.py`
   - Currently: `claude-sonnet-4-20250514`

## Adding New Models

To add a new model, update **only** `model_config.py`:

```python
MODEL_REGISTRY.append(
    ModelDefinition(
        id="new-model-id",
        name="New Model Name",
        provider=ModelProvider.ANTHROPIC,  # or OPENAI
        description="Model description",
        capabilities=[
            ModelCapability.VISION,
            ModelCapability.REASONING,
            ModelCapability.STRUCTURED_OUTPUT
        ],
        is_default=False,
        supports_reasoning_effort=False,  # True for O-series
        recommended_use="When to use this model",
        cost_tier="medium"  # low, medium, high, premium
    )
)
```

The model will automatically appear in:
- ✅ Web UI dropdown
- ✅ Testing lab model selector
- ✅ API validation
- ✅ CLI help text

## Model Capabilities

All models must have these capabilities for financial spreading:

- **VISION** - Required for processing PDF images
- **STRUCTURED_OUTPUT** - Required for Pydantic schema compliance

Optional capabilities:
- **REASONING** - Enhanced reasoning for complex documents

## Cost Optimization

Models are tagged with cost tiers:

- **Low**: GPT-4o Mini - Quick testing, simple documents
- **Medium**: Claude Sonnet 4.5, GPT-4o, O1 Mini - General use
- **High**: GPT-5.2, O1 - Complex analysis
- **Premium**: Claude Opus 4.5 - Highest accuracy requirements

**Recommendation**: Start with Claude Sonnet 4.5 (medium tier) for the best balance.

## Provider Comparison

| Feature | Anthropic Claude 4.5 | OpenAI GPT-5 |
|---------|---------------------|--------------|
| Vision Quality | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐ Very Good |
| Reasoning | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐⭐ Excellent |
| Speed | ⭐⭐⭐⭐ Fast | ⭐⭐⭐⭐ Fast |
| Cost (Sonnet) | ⭐⭐⭐⭐ Good | ⭐⭐⭐ Moderate |
| Cost (Opus/GPT-5) | ⭐⭐⭐ Moderate | ⭐⭐⭐ Moderate |
| Structured Output | ⭐⭐⭐⭐⭐ Native | ⭐⭐⭐⭐⭐ Native |

**Default Choice**: Claude Sonnet 4.5 offers the best overall balance for financial document processing.

## Troubleshooting

### Model Not Available Error

```
Error: Model 'claude-sonnet-4-20250514' requires ANTHROPIC_API_KEY
```

**Solution**: Add `ANTHROPIC_API_KEY` to your `.env` file.

### Vision Capability Warning

```
Warning: Model 'o1' does not support vision (required for PDF processing)
```

**Solution**: O1 models don't have vision. Use O1 only with text-based extraction or choose a vision-capable model (GPT-4o, GPT-5, Claude).

### Frontend/Backend Model Mismatch

If models appear in the backend but not frontend (or vice versa):

1. Check that `frontend/src/modelConfig.ts` mirrors `backend/model_config.py`
2. Rebuild the frontend: `cd frontend && npm run build`
3. Restart the backend server

## Best Practices

1. **Production**: Use LangSmith Hub to configure models
   - Change models without code deploys
   - A/B test different models
   - Version control prompts and models together

2. **Development**: Use environment variables (`.env`)
   - Quick local testing
   - Switch between providers easily

3. **Testing**: Use CLI overrides
   - Compare model performance
   - Test new models before production

4. **Cost Management**: 
   - Start with Claude Sonnet 4.5 (default)
   - Use Mini models for testing
   - Reserve Opus/GPT-5.2 for complex documents

## Future Enhancements

- [ ] Auto-fetch model list from providers (no manual updates)
- [ ] Model performance metrics in testing lab
- [ ] Cost tracking per model
- [ ] Automatic model fallback on rate limits
- [ ] Model-specific prompt optimization

## Support

For questions or issues:
- Check this guide first
- Review `model_config.py` for available models
- Check LangSmith traces for debugging
- File an issue with model details and error logs
