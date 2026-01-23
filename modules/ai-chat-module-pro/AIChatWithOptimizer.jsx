/**
 * AIChatWithOptimizer
 * 
 * Complete integration of AIChatModulePro with ClaudeContextOptimizer
 * for production Claude API usage.
 * 
 * FEATURES:
 * - Automatic context compaction when nearing limits
 * - Real-time token usage display
 * - Message consolidation for efficiency
 * - Artifact suggestions for long content
 * - Project knowledge integration
 * - 1M token support for extended conversations
 */

import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import AIChatModulePro, { DEFAULT_CONFIG, THEMES, generateId } from './AIChatModulePro';
import { 
  ClaudeContextOptimizer, 
  createOptimizedSendHandler,
  estimateTokens,
  MODEL_LIMITS 
} from './ClaudeContextOptimizer';

// Token usage display component
const TokenUsageBar = ({ usage, stats, compact = false }) => {
  const getStatusColor = () => {
    if (usage.percentage > 90) return '#ef4444';
    if (usage.percentage > 75) return '#f59e0b';
    return '#22c55e';
  };

  if (compact) {
    return (
      <div className="token-bar-compact">
        <div className="token-bar-fill" style={{ 
          width: `${Math.min(usage.percentage, 100)}%`,
          background: getStatusColor() 
        }} />
        <span className="token-bar-text">{usage.percentage.toFixed(0)}%</span>
      </div>
    );
  }

  return (
    <div className="token-usage">
      <div className="token-usage-header">
        <div className="token-usage-status">
          <div className="token-status-dot" style={{ background: getStatusColor() }} />
          <span className="token-count">
            {usage.current.toLocaleString()} / {usage.available.toLocaleString()} tokens
          </span>
        </div>
        {stats.compactions > 0 && (
          <span className="token-saved">
            {stats.tokensSaved.toLocaleString()} saved ({stats.efficiency})
          </span>
        )}
      </div>
      <div className="token-bar">
        <div 
          className="token-bar-fill" 
          style={{ 
            width: `${Math.min(usage.percentage, 100)}%`,
            background: getStatusColor() 
          }} 
        />
      </div>
      {usage.needsCompaction && (
        <div className="token-warning">
          ⚠️ Context will be compacted soon to continue conversation
        </div>
      )}
    </div>
  );
};

// Artifact suggestion component
const ArtifactSuggestion = ({ type, tokens, onAccept, onDismiss }) => (
  <div className="artifact-suggestion">
    <div className="artifact-suggestion-icon">💡</div>
    <div className="artifact-suggestion-content">
      <strong>Large content detected ({tokens.toLocaleString()} tokens)</strong>
      <p>Consider using an Artifact for this {type} content to improve token efficiency.</p>
    </div>
    <div className="artifact-suggestion-actions">
      <button onClick={onAccept}>Use Artifact</button>
      <button onClick={onDismiss} className="secondary">Dismiss</button>
    </div>
  </div>
);

// Compaction notice component
const CompactionNotice = ({ summary, removedCount, onDismiss }) => (
  <div className="compaction-notice">
    <div className="compaction-notice-header">
      <span>🗜️ Context Compacted</span>
      <button onClick={onDismiss}>×</button>
    </div>
    <p>{removedCount} older messages summarized to continue conversation.</p>
    <details>
      <summary>View Summary</summary>
      <pre>{summary}</pre>
    </details>
  </div>
);

// Main integrated component
export default function AIChatWithOptimizer({
  // Anthropic client (required)
  anthropicClient,
  
  // Model configuration
  model = 'claude-sonnet-4-20250514',
  maxTokens = 8192,
  systemPrompt = null,
  tools = null,
  
  // Optimizer configuration
  optimizerConfig = {},
  
  // Chat configuration
  chatConfig = {},
  
  // Project knowledge
  projectKnowledge = null,
  
  // Callbacks
  onTokenUpdate = null,
  onCompaction = null,
  onError = null,
  
  // Initial state
  initialMessages = [],
  
  className = '',
}) {
  // Initialize optimizer
  const optimizer = useMemo(() => {
    return new ClaudeContextOptimizer({
      model,
      ...optimizerConfig,
      projectKnowledgeRef: projectKnowledge?.name,
      onCompaction: (summary, count) => {
        setCompactionInfo({ summary, count, visible: true });
        onCompaction?.(summary, count);
      },
      onTokenWarning: (current, limit) => {
        console.warn(`Token warning: ${current}/${limit}`);
      },
      onArtifactSuggestion: (content, type) => {
        setArtifactSuggestion({ content, type, tokens: estimateTokens(content), visible: true });
      },
    });
  }, [model, optimizerConfig, projectKnowledge, onCompaction]);

  // State
  const [tokenUsage, setTokenUsage] = useState(optimizer.getTokenUsage());
  const [stats, setStats] = useState(optimizer.getStats());
  const [compactionInfo, setCompactionInfo] = useState({ visible: false });
  const [artifactSuggestion, setArtifactSuggestion] = useState({ visible: false });
  const chatRef = useRef(null);

  // Load initial messages into optimizer
  useEffect(() => {
    initialMessages.forEach(msg => {
      optimizer.addMessage(msg);
    });
    setTokenUsage(optimizer.getTokenUsage());
    setStats(optimizer.getStats());
  }, []);

  // Create optimized send handler
  const handleSendMessage = useCallback(async (message, files, callbacks) => {
    try {
      // Add user message to optimizer
      await optimizer.addMessage({ role: 'user', content: message });
      setTokenUsage(optimizer.getTokenUsage());
      setStats(optimizer.getStats());
      
      // Get optimized messages
      const messages = optimizer.getOptimizedMessages();
      
      // Report optimization step
      const currentStats = optimizer.getStats();
      callbacks.onProcessingStep({ 
        label: 'Optimizing context', 
        status: 'complete',
        duration: 50,
        detail: `${currentStats.currentTokens.toLocaleString()} tokens${currentStats.compactions > 0 ? ` (${currentStats.efficiency} saved)` : ''}`
      });
      
      // Prepare request
      callbacks.onProcessingStep({ label: 'Calling Claude API', status: 'running' });
      
      const requestMessages = [...messages];
      
      // Handle file attachments
      if (files?.length) {
        const lastMsg = requestMessages[requestMessages.length - 1];
        if (lastMsg.role === 'user' && typeof lastMsg.content === 'string') {
          const contentParts = [{ type: 'text', text: lastMsg.content }];
          
          for (const file of files) {
            if (file.type.startsWith('image/')) {
              const base64 = await fileToBase64(file);
              contentParts.push({
                type: 'image',
                source: { type: 'base64', media_type: file.type, data: base64 }
              });
            } else {
              // For non-image files, add as text reference
              contentParts.push({
                type: 'text',
                text: `\n[Attached file: ${file.name} (${formatFileSize(file.size)})]`
              });
            }
          }
          
          lastMsg.content = contentParts;
        }
      }
      
      // Make API call with streaming
      const requestBody = {
        model,
        max_tokens: maxTokens,
        messages: requestMessages,
        stream: true,
      };
      
      if (systemPrompt) {
        requestBody.system = systemPrompt;
      }
      
      if (tools) {
        requestBody.tools = tools;
      }
      
      // Add project knowledge to system prompt
      if (projectKnowledge) {
        const knowledgeContext = `[Project Knowledge: ${projectKnowledge.name}]\n${projectKnowledge.summary || ''}\n\n`;
        requestBody.system = knowledgeContext + (requestBody.system || '');
      }
      
      const stream = await anthropicClient.messages.stream(requestBody);
      
      callbacks.onProcessingStepUpdate(1, { status: 'complete', duration: 100 });
      callbacks.onProcessingStep({ label: 'Generating response', status: 'running' });
      
      let fullContent = '';
      let thinkingContent = '';
      let inputTokens = 0;
      let outputTokens = 0;
      
      for await (const event of stream) {
        switch (event.type) {
          case 'message_start':
            if (event.message?.usage) {
              inputTokens = event.message.usage.input_tokens;
            }
            break;
            
          case 'content_block_start':
            if (event.content_block?.type === 'thinking') {
              callbacks.onThinking({ content: '', duration: 0 });
            }
            break;
            
          case 'content_block_delta':
            if (event.delta?.type === 'thinking_delta') {
              thinkingContent += event.delta.thinking;
              callbacks.onThinking({ content: thinkingContent });
            } else if (event.delta?.type === 'text_delta') {
              fullContent += event.delta.text;
              callbacks.onContentDelta(event.delta.text);
            }
            break;
            
          case 'message_delta':
            if (event.usage) {
              outputTokens = event.usage.output_tokens;
            }
            break;
            
          case 'content_block_stop':
            if (thinkingContent) {
              callbacks.onThinking({ content: thinkingContent, duration: Date.now() });
            }
            break;
        }
      }
      
      // Add assistant response to optimizer
      await optimizer.addMessage({ role: 'assistant', content: fullContent });
      
      // Update token usage
      const newUsage = optimizer.getTokenUsage();
      setTokenUsage(newUsage);
      setStats(optimizer.getStats());
      onTokenUpdate?.(newUsage);
      
      callbacks.onProcessingStepUpdate(2, { 
        status: 'complete', 
        detail: `${outputTokens.toLocaleString()} tokens`
      });
      
      return {
        content: fullContent,
        model,
        usage: { input_tokens: inputTokens, output_tokens: outputTokens },
      };
      
    } catch (error) {
      console.error('Chat error:', error);
      onError?.(error);
      throw error;
    }
  }, [anthropicClient, model, maxTokens, systemPrompt, tools, projectKnowledge, optimizer, onTokenUpdate, onError]);

  // Stop generation handler
  const handleStopGeneration = useCallback(() => {
    // The abort would be handled by the streaming client
    console.log('Generation stopped by user');
  }, []);

  // Merged chat config
  const mergedChatConfig = useMemo(() => ({
    ...DEFAULT_CONFIG,
    title: 'Claude Assistant',
    subtitle: `${model} • Optimized Context`,
    showProcessingSteps: true,
    showThinkingBlocks: true,
    ...chatConfig,
  }), [model, chatConfig]);

  return (
    <div className={`chat-with-optimizer ${className}`}>
      <style>{OPTIMIZER_STYLES}</style>
      
      {/* Token usage bar */}
      <div className="optimizer-header">
        <TokenUsageBar usage={tokenUsage} stats={stats} />
      </div>
      
      {/* Compaction notice */}
      {compactionInfo.visible && (
        <CompactionNotice 
          summary={compactionInfo.summary}
          removedCount={compactionInfo.count}
          onDismiss={() => setCompactionInfo(prev => ({ ...prev, visible: false }))}
        />
      )}
      
      {/* Artifact suggestion */}
      {artifactSuggestion.visible && (
        <ArtifactSuggestion
          type={artifactSuggestion.type}
          tokens={artifactSuggestion.tokens}
          onAccept={() => {
            // Handle artifact creation
            setArtifactSuggestion(prev => ({ ...prev, visible: false }));
          }}
          onDismiss={() => setArtifactSuggestion(prev => ({ ...prev, visible: false }))}
        />
      )}
      
      {/* Main chat */}
      <div className="chat-main">
        <AIChatModulePro
          ref={chatRef}
          config={mergedChatConfig}
          onSendMessage={handleSendMessage}
          onStopGeneration={handleStopGeneration}
          initialMessages={initialMessages}
        />
      </div>
    </div>
  );
}

// Helper functions
async function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// Styles
const OPTIMIZER_STYLES = `
.chat-with-optimizer {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--chat-bg, #09090b);
}

.optimizer-header {
  padding: 12px 16px;
  background: var(--chat-surface, #18181b);
  border-bottom: 1px solid var(--chat-border, #27272a);
}

.chat-main {
  flex: 1;
  min-height: 0;
}

/* Token Usage */
.token-usage {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.token-usage-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.token-usage-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.token-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.token-count {
  font-size: 12px;
  font-family: var(--chat-font-mono, monospace);
  color: var(--chat-text, #fafafa);
}

.token-saved {
  font-size: 11px;
  color: var(--chat-success, #22c55e);
}

.token-bar {
  height: 4px;
  background: var(--chat-border, #27272a);
  border-radius: 2px;
  overflow: hidden;
}

.token-bar-fill {
  height: 100%;
  transition: width 0.3s ease, background 0.3s ease;
}

.token-bar-compact {
  position: relative;
  height: 20px;
  background: var(--chat-border, #27272a);
  border-radius: 4px;
  overflow: hidden;
}

.token-bar-compact .token-bar-fill {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
}

.token-bar-compact .token-bar-text {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 600;
  color: white;
  text-shadow: 0 1px 2px rgba(0,0,0,0.5);
}

.token-warning {
  font-size: 11px;
  color: var(--chat-warning, #f59e0b);
  padding: 6px 10px;
  background: var(--chat-warning-muted, rgba(245, 158, 11, 0.15));
  border-radius: 6px;
}

/* Compaction Notice */
.compaction-notice {
  margin: 12px 16px;
  padding: 12px;
  background: var(--chat-accent-muted, rgba(99, 102, 241, 0.15));
  border: 1px solid var(--chat-accent, #6366f1);
  border-radius: var(--chat-radius, 10px);
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

.compaction-notice-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.compaction-notice-header span {
  font-weight: 600;
  color: var(--chat-accent, #6366f1);
}

.compaction-notice-header button {
  background: none;
  border: none;
  color: var(--chat-text-muted, #71717a);
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
}

.compaction-notice p {
  font-size: 13px;
  color: var(--chat-text-secondary, #a1a1aa);
  margin: 0 0 8px;
}

.compaction-notice details {
  font-size: 12px;
}

.compaction-notice summary {
  cursor: pointer;
  color: var(--chat-accent, #6366f1);
  margin-bottom: 8px;
}

.compaction-notice pre {
  margin: 0;
  padding: 10px;
  background: var(--chat-bg, #09090b);
  border-radius: 6px;
  font-size: 11px;
  font-family: var(--chat-font-mono, monospace);
  white-space: pre-wrap;
  max-height: 200px;
  overflow-y: auto;
}

/* Artifact Suggestion */
.artifact-suggestion {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin: 12px 16px;
  padding: 12px;
  background: var(--chat-success-muted, rgba(34, 197, 94, 0.15));
  border: 1px solid var(--chat-success, #22c55e);
  border-radius: var(--chat-radius, 10px);
  animation: slideIn 0.3s ease;
}

.artifact-suggestion-icon {
  font-size: 24px;
}

.artifact-suggestion-content {
  flex: 1;
}

.artifact-suggestion-content strong {
  display: block;
  color: var(--chat-success, #22c55e);
  margin-bottom: 4px;
}

.artifact-suggestion-content p {
  font-size: 12px;
  color: var(--chat-text-secondary, #a1a1aa);
  margin: 0;
}

.artifact-suggestion-actions {
  display: flex;
  gap: 8px;
}

.artifact-suggestion-actions button {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.artifact-suggestion-actions button:first-child {
  background: var(--chat-success, #22c55e);
  border: none;
  color: white;
}

.artifact-suggestion-actions button:first-child:hover {
  filter: brightness(1.1);
}

.artifact-suggestion-actions button.secondary {
  background: none;
  border: 1px solid var(--chat-border, #27272a);
  color: var(--chat-text-muted, #71717a);
}

.artifact-suggestion-actions button.secondary:hover {
  background: var(--chat-surface-hover, #1f1f23);
}
`;

// Export components and utilities
export { 
  TokenUsageBar, 
  ArtifactSuggestion, 
  CompactionNotice,
  ClaudeContextOptimizer,
  MODEL_LIMITS,
};
