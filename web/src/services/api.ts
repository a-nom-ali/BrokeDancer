/**
 * API Service
 *
 * Handles HTTP requests to the backend REST API
 */

import type {
  Bot,
  StrategyInstance,
  GlobalPortfolio,
  ActivityItem,
  ExecutionRecord,
  WorkflowDefinition,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

/**
 * Generic fetch wrapper with error handling
 */
async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: response.statusText }));
      throw new Error(error.message || `HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API request failed:', url, error);
    throw error;
  }
}

/**
 * Global Portfolio API
 */
export const portfolioAPI = {
  /**
   * Get global portfolio metrics
   */
  async getGlobalPortfolio(): Promise<GlobalPortfolio> {
    return fetchAPI<GlobalPortfolio>('/portfolio');
  },

  /**
   * Get PnL history
   */
  async getPnLHistory(days: number = 30): Promise<GlobalPortfolio['pnlHistory']> {
    return fetchAPI(`/portfolio/pnl?days=${days}`);
  },
};

/**
 * Bot API
 */
export const botAPI = {
  /**
   * Get all bots
   */
  async getAllBots(): Promise<Bot[]> {
    return fetchAPI<Bot[]>('/bots');
  },

  /**
   * Get bot by ID
   */
  async getBot(botId: string): Promise<Bot> {
    return fetchAPI<Bot>(`/bots/${botId}`);
  },

  /**
   * Create a new bot
   */
  async createBot(botData: Partial<Bot>): Promise<Bot> {
    return fetchAPI<Bot>('/bots', {
      method: 'POST',
      body: JSON.stringify(botData),
    });
  },

  /**
   * Update bot
   */
  async updateBot(botId: string, updates: Partial<Bot>): Promise<Bot> {
    return fetchAPI<Bot>(`/bots/${botId}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  },

  /**
   * Delete bot
   */
  async deleteBot(botId: string): Promise<void> {
    return fetchAPI<void>(`/bots/${botId}`, {
      method: 'DELETE',
    });
  },

  /**
   * Start bot
   */
  async startBot(botId: string): Promise<Bot> {
    return fetchAPI<Bot>(`/bots/${botId}/start`, {
      method: 'POST',
    });
  },

  /**
   * Pause bot
   */
  async pauseBot(botId: string): Promise<Bot> {
    return fetchAPI<Bot>(`/bots/${botId}/pause`, {
      method: 'POST',
    });
  },

  /**
   * Stop bot
   */
  async stopBot(botId: string): Promise<Bot> {
    return fetchAPI<Bot>(`/bots/${botId}/stop`, {
      method: 'POST',
    });
  },
};

/**
 * Strategy API
 */
export const strategyAPI = {
  /**
   * Get all strategies for a bot
   */
  async getBotStrategies(botId: string): Promise<StrategyInstance[]> {
    return fetchAPI<StrategyInstance[]>(`/bots/${botId}/strategies`);
  },

  /**
   * Get strategy by ID
   */
  async getStrategy(strategyId: string): Promise<StrategyInstance> {
    return fetchAPI<StrategyInstance>(`/strategies/${strategyId}`);
  },

  /**
   * Create a new strategy
   */
  async createStrategy(botId: string, strategyData: Partial<StrategyInstance>): Promise<StrategyInstance> {
    return fetchAPI<StrategyInstance>(`/bots/${botId}/strategies`, {
      method: 'POST',
      body: JSON.stringify(strategyData),
    });
  },

  /**
   * Update strategy
   */
  async updateStrategy(strategyId: string, updates: Partial<StrategyInstance>): Promise<StrategyInstance> {
    return fetchAPI<StrategyInstance>(`/strategies/${strategyId}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  },

  /**
   * Delete strategy
   */
  async deleteStrategy(strategyId: string): Promise<void> {
    return fetchAPI<void>(`/strategies/${strategyId}`, {
      method: 'DELETE',
    });
  },

  /**
   * Start strategy
   */
  async startStrategy(strategyId: string): Promise<StrategyInstance> {
    return fetchAPI<StrategyInstance>(`/strategies/${strategyId}/start`, {
      method: 'POST',
    });
  },

  /**
   * Pause strategy
   */
  async pauseStrategy(strategyId: string): Promise<StrategyInstance> {
    return fetchAPI<StrategyInstance>(`/strategies/${strategyId}/pause`, {
      method: 'POST',
    });
  },

  /**
   * Get strategy execution history
   */
  async getExecutionHistory(strategyId: string, limit: number = 100): Promise<ExecutionRecord[]> {
    return fetchAPI<ExecutionRecord[]>(`/strategies/${strategyId}/executions?limit=${limit}`);
  },
};

/**
 * Workflow API
 */
export const workflowAPI = {
  /**
   * Get workflow definition
   */
  async getWorkflow(strategyId: string): Promise<WorkflowDefinition> {
    return fetchAPI<WorkflowDefinition>(`/strategies/${strategyId}/workflow`);
  },

  /**
   * Update workflow definition
   */
  async updateWorkflow(strategyId: string, workflow: WorkflowDefinition): Promise<WorkflowDefinition> {
    return fetchAPI<WorkflowDefinition>(`/strategies/${strategyId}/workflow`, {
      method: 'PUT',
      body: JSON.stringify(workflow),
    });
  },

  /**
   * Update node property
   */
  async updateNodeProperty(strategyId: string, nodeId: string, property: string, value: unknown): Promise<void> {
    return fetchAPI<void>(`/strategies/${strategyId}/workflow/nodes/${nodeId}`, {
      method: 'PATCH',
      body: JSON.stringify({ property, value }),
    });
  },

  /**
   * Save runtime value as default
   */
  async saveRuntimeValue(strategyId: string, nodeId: string, field: string, value: unknown): Promise<void> {
    return fetchAPI<void>(`/strategies/${strategyId}/workflow/nodes/${nodeId}/save-runtime`, {
      method: 'POST',
      body: JSON.stringify({ field, value }),
    });
  },
};

/**
 * Activity API
 */
export const activityAPI = {
  /**
   * Get recent activity
   */
  async getRecentActivity(limit: number = 50): Promise<ActivityItem[]> {
    return fetchAPI<ActivityItem[]>(`/activity?limit=${limit}`);
  },

  /**
   * Get activity for a specific bot
   */
  async getBotActivity(botId: string, limit: number = 50): Promise<ActivityItem[]> {
    return fetchAPI<ActivityItem[]>(`/bots/${botId}/activity?limit=${limit}`);
  },
};

/**
 * Export all API services
 */
export const api = {
  portfolio: portfolioAPI,
  bots: botAPI,
  strategies: strategyAPI,
  workflows: workflowAPI,
  activity: activityAPI,
};

export default api;
