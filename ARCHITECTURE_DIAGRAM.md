# Model Configuration Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     USER INTERACTION LAYER                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Web UI (UploadPage.tsx)          Testing Lab (TestingPage.tsx)   │
│  ┌────────────────────┐           ┌─────────────────────┐         │
│  │ Model Dropdown     │           │ Model Selector      │         │
│  │ ├─ Anthropic       │           │ ├─ Claude Sonnet    │         │
│  │ │  ├─ Opus 4.5    │           │ ├─ Claude Opus      │         │
│  │ │  └─ Sonnet 4.5  │           │ └─ GPT-5.2          │         │
│  │ └─ OpenAI          │           └─────────────────────┘         │
│  │    ├─ GPT-5.2      │                                           │
│  │    ├─ GPT-4o       │                                           │
│  │    └─ ...          │                                           │
│  └────────────────────┘                                           │
│           │                                  │                     │
└───────────┼──────────────────────────────────┼─────────────────────┘
            │                                  │
            ▼                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CONFIGURATION LAYER                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Frontend Config                    Backend Config                 │
│  ┌─────────────────────┐           ┌──────────────────────┐        │
│  │ modelConfig.ts      │◄─mirrors──┤ model_config.py      │        │
│  │                     │           │                      │        │
│  │ - getAllModels()    │           │ - MODEL_REGISTRY     │        │
│  │ - getDefaultModel() │           │ - ModelDefinition    │        │
│  │ - getGroupedModels()│           │ - get_model_by_id()  │        │
│  └─────────────────────┘           │ - validate_model()   │        │
│           │                        └──────────────────────┘        │
│           │                                  │                     │
│           └──────────────┬───────────────────┘                     │
│                          │                                         │
└──────────────────────────┼─────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      EXECUTION LAYER                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  spreader.py                                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ create_llm(model_name)                                      │   │
│  │ ├─ Detect provider from model_config                       │   │
│  │ ├─ Validate model capabilities                             │   │
│  │ └─ Return ChatAnthropic or ChatOpenAI                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│           │                                                         │
│           ├─────────────────┬───────────────────┐                  │
│           ▼                 ▼                   ▼                  │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐     │
│  │ ChatAnthropic   │ │ ChatOpenAI      │ │ Validation      │     │
│  │ (Claude models) │ │ (GPT models)    │ │ & Tracing       │     │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘     │
│           │                 │                   │                  │
└───────────┼─────────────────┼───────────────────┼──────────────────┘
            │                 │                   │
            ▼                 ▼                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       PROVIDER LAYER                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐              ┌──────────────────┐            │
│  │ Anthropic API    │              │ OpenAI API       │            │
│  │ ├─ Claude Opus   │              │ ├─ GPT-5.2       │            │
│  │ └─ Claude Sonnet │              │ ├─ GPT-4o        │            │
│  └──────────────────┘              │ └─ O1/O3         │            │
│                                    └──────────────────┘            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Model Selection (User → Config)

```
User selects model
    ↓
Frontend reads modelConfig.ts
    ↓
Sends model ID to backend API
    ↓
Backend validates with model_config.py
    ↓
Returns validation result
```

### 2. Document Processing (Config → Execution)

```
API receives upload + model_id
    ↓
spreader.py::create_llm(model_id)
    ↓
model_config.get_model_by_id(model_id)
    ↓
Detect provider (Anthropic or OpenAI)
    ↓
Instantiate appropriate ChatModel
    ↓
Process document with selected model
    ↓
Return structured results
```

### 3. Adding New Models (Config Only)

```
Developer adds to model_config.py:
    ModelDefinition(
        id="new-model",
        provider=...,
        capabilities=[...],
        ...
    )
    ↓
Update frontend/src/modelConfig.ts (mirror)
    ↓
✅ Model appears everywhere:
    - Web UI dropdown
    - Testing lab selector
    - CLI validation
    - API documentation
```

## File Relationships

```
model_config.py (SINGLE SOURCE OF TRUTH)
    │
    ├──► spreader.py
    │    └─ create_llm()
    │    └─ validate_model_for_spreading()
    │
    ├──► backend/testing/test_runner.py
    │    └─ AVAILABLE_MODELS = export_for_api()
    │    └─ get_available_models()
    │
    ├──► backend/api.py (indirect via test_runner)
    │    └─ /api/testing/status endpoint
    │
    └──► frontend/src/modelConfig.ts (mirrors)
         └─ getAllModels()
         └─ getGroupedModels()
         │
         └──► frontend/src/components/UploadPage.tsx
         │    └─ Model dropdown
         │
         └──► frontend/src/components/testing/TestingPage.tsx
              └─ Model selector
```

## Configuration Sources Priority

```
1. CLI/API Override (Highest Priority)
   ├─ python main.py --model claude-sonnet-4-20250514
   └─ API: { modelOverride: "claude-sonnet-4-20250514" }

2. LangSmith Hub (Production Recommended)
   └─ Configured in LangSmith UI
      Changes take effect immediately

3. Environment Variables (.env)
   ├─ ANTHROPIC_MODEL=claude-sonnet-4-20250514
   └─ OPENAI_MODEL=gpt-5.2

4. Code Default (Last Resort)
   └─ model_config.py::DEFAULT_MODEL_ID
      Currently: claude-sonnet-4-20250514
```

## Benefits of This Architecture

### 1. Single Source of Truth
- ✅ All models defined in `model_config.py`
- ✅ No duplication across files
- ✅ Consistent definitions everywhere

### 2. Easy Maintenance
- ✅ Add model in ONE place
- ✅ Automatic propagation to all systems
- ✅ Type-safe validation

### 3. Scalability
- ✅ Support multiple providers
- ✅ Add new capabilities easily
- ✅ Extensible metadata structure

### 4. Developer Experience
- ✅ Clear separation of concerns
- ✅ Self-documenting code
- ✅ Easy to test new models

### 5. User Experience
- ✅ Grouped by provider in UI
- ✅ Clear model descriptions
- ✅ Visual badges (Default, Premium)
- ✅ Cost tier indicators

## Example: Adding a New Model

```python
# 1. Backend: Add to model_config.py
MODEL_REGISTRY.append(
    ModelDefinition(
        id="gpt-5.3",
        name="GPT-5.3",
        provider=ModelProvider.OPENAI,
        capabilities=[VISION, REASONING, STRUCTURED_OUTPUT],
        cost_tier="high"
    )
)

# 2. Frontend: Mirror in modelConfig.ts
MODEL_REGISTRY.push({
  id: 'gpt-5.3',
  name: 'GPT-5.3',
  provider: 'openai',
  capabilities: ['vision', 'reasoning', 'structured_output'],
  costTier: 'high'
});

# 3. Done! Model now appears:
✅ Web UI dropdown
✅ Testing lab selector
✅ CLI validation
✅ API responses
```

## Security & Best Practices

### API Keys
- ✅ Never hardcoded
- ✅ Stored in `.env` (gitignored)
- ✅ Separate keys for each provider

### Model Validation
- ✅ Capability checking (vision, structured output)
- ✅ Provider detection
- ✅ Graceful fallbacks

### Error Handling
- ✅ Clear error messages
- ✅ Model-specific troubleshooting
- ✅ LangSmith tracing for debugging

## Performance Considerations

### Model Selection
- Fast O(n) lookup with list comprehension
- Cached in memory after first load
- No external API calls for model list

### Provider Detection
- Pattern matching on model name
- Fallback to registry lookup
- < 1ms overhead per request

### Frontend Bundle Size
- Model config: ~5KB
- No impact on initial load
- Tree-shakable exports
