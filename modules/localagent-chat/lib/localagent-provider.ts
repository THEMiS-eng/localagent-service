/**
 * LocalAgent LLM Provider
 * Connects chat components to LocalAgent backend
 *
 * Features:
 * - Multi-provider support (MLX, Ollama, Claude, OpenAI)
 * - Automatic fallback chain
 * - THEMIS skill injection
 * - 100% offline capable (with local providers)
 */

import { useState, useCallback } from 'react';

const LOCALAGENT_URL = typeof window !== 'undefined'
  ? (window as any).__LOCALAGENT_URL__ || 'http://localhost:9998'
  : process.env.LOCALAGENT_URL || 'http://localhost:9998';

// ============================================================
// TYPES
// ============================================================

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  createdAt: Date;
  provider?: string;
  skill_injected?: boolean;
}

export interface CompleteRequest {
  prompt: string;
  system?: string;
  context?: string;
  skill_name?: string;
  provider?: string;
  fallback?: boolean;
}

export interface CompleteResponse {
  success: boolean;
  response: string;
  provider: string;
  usage?: Record<string, unknown>;
  skill_injected?: boolean;
  error?: string;
}

export interface ProviderInfo {
  name: string;
  available: boolean;
  priority: number;
}

export interface ProviderStatus {
  providers: Record<string, boolean>;
  available: string[];
  active: string | null;
}

export interface LLMStatus {
  llm: ProviderStatus;
  skills: {
    available: string[];
    active: string[];
  };
}

// ============================================================
// API FUNCTIONS
// ============================================================

/**
 * Send completion request to LocalAgent
 */
export async function complete(request: CompleteRequest): Promise<CompleteResponse> {
  try {
    const response = await fetch(`${LOCALAGENT_URL}/api/llm/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: request.prompt,
        system: request.system || '',
        context: request.context || '',
        skill_name: request.skill_name,
        provider: request.provider,
        fallback: request.fallback ?? true,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      return {
        success: false,
        response: '',
        provider: 'error',
        error: error.detail || `HTTP ${response.status}`,
      };
    }

    return response.json();
  } catch (err) {
    return {
      success: false,
      response: '',
      provider: 'error',
      error: err instanceof Error ? err.message : 'Network error',
    };
  }
}

/**
 * Get available LLM providers
 */
export async function getProviders(): Promise<ProviderStatus> {
  try {
    const response = await fetch(`${LOCALAGENT_URL}/api/llm/providers`);
    if (!response.ok) {
      return { providers: {}, available: [], active: null };
    }
    return response.json();
  } catch {
    return { providers: {}, available: [], active: null };
  }
}

/**
 * Set active LLM provider
 */
export async function setProvider(provider: string): Promise<boolean> {
  try {
    const response = await fetch(`${LOCALAGENT_URL}/api/llm/provider`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider }),
    });
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Get full LLM status including skills
 */
export async function getStatus(): Promise<LLMStatus> {
  try {
    const response = await fetch(`${LOCALAGENT_URL}/api/llm/status`);
    if (!response.ok) {
      return {
        llm: { providers: {}, available: [], active: null },
        skills: { available: [], active: [] },
      };
    }
    return response.json();
  } catch {
    return {
      llm: { providers: {}, available: [], active: null },
      skills: { available: [], active: [] },
    };
  }
}

/**
 * Test a specific provider
 */
export async function testProvider(provider: string): Promise<{
  success: boolean;
  response_time_ms: number;
  error?: string;
}> {
  try {
    const response = await fetch(`${LOCALAGENT_URL}/api/llm/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider }),
    });
    return response.json();
  } catch (err) {
    return {
      success: false,
      response_time_ms: 0,
      error: err instanceof Error ? err.message : 'Network error',
    };
  }
}

// ============================================================
// REACT HOOK
// ============================================================

export interface UseLocalAgentChatOptions {
  skill_name?: string;
  provider?: string;
  system?: string;
  onResponse?: (response: CompleteResponse) => void;
  onError?: (error: string) => void;
}

export interface UseLocalAgentChatReturn {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  activeProvider: string | null;
  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
}

/**
 * React hook for LocalAgent chat
 */
export function useLocalAgentChat(
  options: UseLocalAgentChatOptions = {}
): UseLocalAgentChatReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeProvider, setActiveProvider] = useState<string | null>(null);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: content.trim(),
      createdAt: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      const result = await complete({
        prompt: content,
        system: options.system,
        skill_name: options.skill_name,
        provider: options.provider,
        fallback: true,
      });

      if (result.success) {
        const assistantMessage: Message = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: result.response,
          createdAt: new Date(),
          provider: result.provider,
          skill_injected: result.skill_injected,
        };
        setMessages(prev => [...prev, assistantMessage]);
        setActiveProvider(result.provider);
        options.onResponse?.(result);
      } else {
        const errorMsg = result.error || 'Unknown error';
        setError(errorMsg);
        options.onError?.(errorMsg);
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Network error';
      setError(errorMsg);
      options.onError?.(errorMsg);
    } finally {
      setIsLoading(false);
    }
  }, [options]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    activeProvider,
    sendMessage,
    clearMessages,
    setMessages,
  };
}

// ============================================================
// UTILITIES
// ============================================================

/**
 * Generate unique ID
 */
export function generateId(): string {
  return crypto.randomUUID();
}

/**
 * Format provider name for display
 */
export function formatProvider(provider: string): string {
  const names: Record<string, string> = {
    mlx: 'MLX (Local)',
    ollama: 'Ollama (Local)',
    claude: 'Claude',
    openai: 'OpenAI',
  };
  return names[provider] || provider;
}

/**
 * Check if provider is local (offline capable)
 */
export function isLocalProvider(provider: string): boolean {
  return ['mlx', 'ollama'].includes(provider);
}
