/**
 * SimpleChat - Minimal chat component for LocalAgent
 *
 * Features:
 * - Clean Vercel-inspired design
 * - Provider indicator (MLX/Ollama/Claude)
 * - THEMIS skill support
 * - Responsive layout
 * - Dark mode support
 */

'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  useLocalAgentChat,
  formatProvider,
  isLocalProvider,
  type Message,
  type UseLocalAgentChatOptions,
} from '../lib/localagent-provider';

// ============================================================
// STYLES (Tailwind classes)
// ============================================================

const styles = {
  container: 'flex flex-col h-full bg-white dark:bg-gray-900',
  header: 'flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700',
  headerTitle: 'text-lg font-semibold text-gray-900 dark:text-white',
  headerStatus: 'flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400',
  statusDot: 'w-2 h-2 rounded-full',
  statusDotLocal: 'bg-green-500',
  statusDotCloud: 'bg-blue-500',
  statusDotOffline: 'bg-gray-400',

  messagesContainer: 'flex-1 overflow-y-auto px-4 py-4',
  messagesInner: 'max-w-3xl mx-auto space-y-4',

  messageRow: 'flex w-full',
  messageRowUser: 'justify-end',
  messageRowAssistant: 'justify-start gap-3',

  avatar: 'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm',
  avatarAssistant: 'bg-gray-100 dark:bg-gray-800 ring-1 ring-gray-200 dark:ring-gray-700',

  bubble: 'max-w-[80%] px-4 py-2 rounded-2xl text-sm',
  bubbleUser: 'bg-blue-600 text-white',
  bubbleAssistant: 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white',

  providerTag: 'text-xs text-gray-400 dark:text-gray-500 mt-1',

  inputContainer: 'border-t border-gray-200 dark:border-gray-700 px-4 py-3',
  inputInner: 'max-w-3xl mx-auto',
  inputForm: 'flex items-end gap-2 p-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 focus-within:border-blue-500 dark:focus-within:border-blue-500 transition-colors',
  textarea: 'flex-1 resize-none bg-transparent border-none outline-none text-gray-900 dark:text-white placeholder-gray-400 text-sm min-h-[44px] max-h-[200px] py-2 px-2',
  sendButton: 'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-colors',
  sendButtonEnabled: 'bg-blue-600 text-white hover:bg-blue-700',
  sendButtonDisabled: 'bg-gray-200 dark:bg-gray-700 text-gray-400 cursor-not-allowed',

  thinking: 'flex items-center gap-2 text-gray-500 dark:text-gray-400 text-sm',
  thinkingDots: 'flex gap-1',
  thinkingDot: 'w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce',

  error: 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 px-4 py-2 rounded-lg text-sm',

  greeting: 'text-center py-12',
  greetingIcon: 'text-4xl mb-4',
  greetingTitle: 'text-xl font-semibold text-gray-900 dark:text-white mb-2',
  greetingSubtitle: 'text-gray-500 dark:text-gray-400',
};

// ============================================================
// ICONS
// ============================================================

const SparklesIcon = ({ size = 16 }: { size?: number }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M12 3l1.912 5.813a2 2 0 001.275 1.275L21 12l-5.813 1.912a2 2 0 00-1.275 1.275L12 21l-1.912-5.813a2 2 0 00-1.275-1.275L3 12l5.813-1.912a2 2 0 001.275-1.275L12 3z" />
  </svg>
);

const SendIcon = ({ size = 16 }: { size?: number }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M22 2L11 13" />
    <path d="M22 2L15 22L11 13L2 9L22 2Z" />
  </svg>
);

// ============================================================
// SUB-COMPONENTS
// ============================================================

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div className={`${styles.messageRow} ${isUser ? styles.messageRowUser : styles.messageRowAssistant}`}>
      {!isUser && (
        <div className={`${styles.avatar} ${styles.avatarAssistant}`}>
          <SparklesIcon size={14} />
        </div>
      )}
      <div>
        <div className={`${styles.bubble} ${isUser ? styles.bubbleUser : styles.bubbleAssistant}`}>
          <div className="whitespace-pre-wrap break-words">{message.content}</div>
        </div>
        {!isUser && message.provider && (
          <div className={styles.providerTag}>
            {formatProvider(message.provider)}
            {message.skill_injected && ' + Skill'}
          </div>
        )}
      </div>
    </div>
  );
};

const ThinkingIndicator: React.FC = () => (
  <div className={`${styles.messageRow} ${styles.messageRowAssistant}`}>
    <div className={`${styles.avatar} ${styles.avatarAssistant}`}>
      <div className="animate-pulse">
        <SparklesIcon size={14} />
      </div>
    </div>
    <div className={styles.thinking}>
      <span>Thinking</span>
      <span className={styles.thinkingDots}>
        <span className={styles.thinkingDot} style={{ animationDelay: '0ms' }} />
        <span className={styles.thinkingDot} style={{ animationDelay: '150ms' }} />
        <span className={styles.thinkingDot} style={{ animationDelay: '300ms' }} />
      </span>
    </div>
  </div>
);

const Greeting: React.FC = () => (
  <div className={styles.greeting}>
    <div className={styles.greetingIcon}>
      <SparklesIcon size={48} />
    </div>
    <h2 className={styles.greetingTitle}>How can I help you today?</h2>
    <p className={styles.greetingSubtitle}>Ask me anything. I'm connected to your LocalAgent.</p>
  </div>
);

// ============================================================
// MAIN COMPONENT
// ============================================================

export interface SimpleChatProps {
  /** THEMIS skill to inject */
  skillName?: string;
  /** Force specific provider */
  provider?: string;
  /** System prompt */
  system?: string;
  /** Header title */
  title?: string;
  /** Show header */
  showHeader?: boolean;
  /** Custom class name */
  className?: string;
  /** Callback on response */
  onResponse?: UseLocalAgentChatOptions['onResponse'];
  /** Callback on error */
  onError?: UseLocalAgentChatOptions['onError'];
}

export const SimpleChat: React.FC<SimpleChatProps> = ({
  skillName,
  provider,
  system,
  title = 'LocalAgent Chat',
  showHeader = true,
  className = '',
  onResponse,
  onError,
}) => {
  const {
    messages,
    isLoading,
    error,
    activeProvider,
    sendMessage,
  } = useLocalAgentChat({
    skill_name: skillName,
    provider,
    system,
    onResponse,
    onError,
  });

  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Auto-resize textarea
  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = '44px';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const message = input;
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = '44px';
    }

    await sendMessage(message);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const canSend = input.trim() && !isLoading;

  return (
    <div className={`${styles.container} ${className}`}>
      {/* Header */}
      {showHeader && (
        <header className={styles.header}>
          <h1 className={styles.headerTitle}>{title}</h1>
          <div className={styles.headerStatus}>
            <span
              className={`${styles.statusDot} ${
                activeProvider
                  ? isLocalProvider(activeProvider)
                    ? styles.statusDotLocal
                    : styles.statusDotCloud
                  : styles.statusDotOffline
              }`}
            />
            <span>
              {activeProvider ? formatProvider(activeProvider) : 'Connecting...'}
            </span>
          </div>
        </header>
      )}

      {/* Messages */}
      <div className={styles.messagesContainer}>
        <div className={styles.messagesInner}>
          {messages.length === 0 && !isLoading && <Greeting />}

          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}

          {isLoading && <ThinkingIndicator />}

          {error && (
            <div className={styles.error}>
              Error: {error}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className={styles.inputContainer}>
        <div className={styles.inputInner}>
          <form onSubmit={handleSubmit} className={styles.inputForm}>
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder="Send a message..."
              className={styles.textarea}
              rows={1}
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={!canSend}
              className={`${styles.sendButton} ${canSend ? styles.sendButtonEnabled : styles.sendButtonDisabled}`}
            >
              <SendIcon size={16} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default SimpleChat;
