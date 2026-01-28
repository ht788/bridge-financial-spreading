/**
 * Central Model Configuration for Frontend
 * 
 * This file is the frontend equivalent of backend/model_config.py
 * It defines all available models in one place to ensure consistency.
 * 
 * IMPORTANT: When adding new models, update BOTH this file and backend/model_config.py
 * (or better yet, generate this file from the backend config via API)
 */

export type ModelProvider = 'openai' | 'anthropic';

export type ModelCapability = 'vision' | 'reasoning' | 'structured_output';

export interface ModelDefinition {
  id: string;
  name: string;
  provider: ModelProvider;
  description: string;
  capabilities: ModelCapability[];
  isDefault: boolean;
  supportsReasoningEffort: boolean;
  supportsExtendedThinking: boolean;
  recommendedUse?: string;
  costTier: 'low' | 'medium' | 'high' | 'premium';
}

/**
 * MODEL REGISTRY - Single source of truth for all available models
 * 
 * This should be kept in sync with backend/model_config.py
 */
export const MODEL_REGISTRY: ModelDefinition[] = [
  // =========================================================================
  // ANTHROPIC MODELS (Latest - Claude 4.5 Series)
  // =========================================================================
  {
    id: 'claude-opus-4-5',
    name: 'Claude Opus 4.5',
    provider: 'anthropic',
    description: 'Most capable Claude model with superior reasoning and analysis',
    capabilities: ['vision', 'reasoning', 'structured_output'],
    isDefault: true, // Set as default for highest accuracy
    supportsReasoningEffort: false, // Anthropic doesn't use reasoning_effort
    supportsExtendedThinking: true,  // Supports extended thinking
    recommendedUse: 'Complex financial documents requiring highest accuracy',
    costTier: 'premium'
  },
  {
    id: 'claude-sonnet-4-5',
    name: 'Claude Sonnet 4.5',
    provider: 'anthropic',
    description: 'Balanced performance and speed with excellent vision capabilities',
    capabilities: ['vision', 'reasoning', 'structured_output'],
    isDefault: false,
    supportsReasoningEffort: false, // Anthropic doesn't use reasoning_effort
    supportsExtendedThinking: true,  // Supports extended thinking
    recommendedUse: 'General purpose financial spreading with excellent quality',
    costTier: 'medium'
  }
];

/**
 * Helper functions
 */

export function getAllModels(): ModelDefinition[] {
  return MODEL_REGISTRY;
}

export function getModelById(modelId: string): ModelDefinition | undefined {
  return MODEL_REGISTRY.find(m => m.id === modelId);
}

export function getDefaultModel(): ModelDefinition {
  const defaultModel = MODEL_REGISTRY.find(m => m.isDefault);
  return defaultModel || MODEL_REGISTRY[0];
}

export function getModelsByProvider(provider: ModelProvider): ModelDefinition[] {
  return MODEL_REGISTRY.filter(m => m.provider === provider);
}

export function getVisionModels(): ModelDefinition[] {
  return MODEL_REGISTRY.filter(m => m.capabilities.includes('vision'));
}

export function getModelDisplayInfo(modelId: string): { 
  name: string; 
  badge?: string;
  description: string;
} {
  const model = getModelById(modelId);
  if (!model) {
    return { name: modelId, description: 'Unknown model' };
  }

  let badge: string | undefined;
  if (model.isDefault) {
    badge = 'Default';
  } else if (model.costTier === 'premium') {
    badge = 'Premium';
  } else if (model.costTier === 'low') {
    badge = 'Fast';
  }

  return {
    name: model.name,
    badge,
    description: model.description
  };
}

/**
 * Group models by provider for UI display
 */
export function getGroupedModels(): Array<{
  provider: ModelProvider;
  providerName: string;
  models: ModelDefinition[];
}> {
  return [
    {
      provider: 'anthropic',
      providerName: 'Anthropic (Claude)',
      models: getModelsByProvider('anthropic')
    },
    {
      provider: 'openai',
      providerName: 'OpenAI',
      models: getModelsByProvider('openai')
    }
  ];
}

/**
 * Cost tier colors for UI
 */
export function getCostTierColor(tier: string): string {
  switch (tier) {
    case 'low':
      return 'text-green-600';
    case 'medium':
      return 'text-blue-600';
    case 'high':
      return 'text-orange-600';
    case 'premium':
      return 'text-purple-600';
    default:
      return 'text-gray-600';
  }
}
