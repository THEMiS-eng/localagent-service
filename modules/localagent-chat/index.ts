/**
 * LocalAgent Chat Module
 *
 * Minimal chat components connected to LocalAgent LLM backend
 */

// Provider & Hook
export {
  // API functions
  complete,
  getProviders,
  setProvider,
  getStatus,
  testProvider,
  // React hook
  useLocalAgentChat,
  // Utilities
  generateId,
  formatProvider,
  isLocalProvider,
  // Types
  type Message,
  type CompleteRequest,
  type CompleteResponse,
  type ProviderStatus,
  type LLMStatus,
  type UseLocalAgentChatOptions,
  type UseLocalAgentChatReturn,
} from './lib/localagent-provider';

// Components
export { SimpleChat, type SimpleChatProps } from './components/SimpleChat';
