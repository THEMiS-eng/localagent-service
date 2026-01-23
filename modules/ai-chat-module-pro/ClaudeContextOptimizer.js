/**
 * ClaudeContextOptimizer
 * 
 * Intelligent context management for Claude API integration.
 * 
 * FEATURES:
 * 1. Automatic Context Compaction - Summarizes older messages when nearing limit
 * 2. Token Counting & Tracking - Real-time token usage monitoring
 * 3. Message Consolidation - Merges short messages to reduce overhead
 * 4. Smart Truncation - Preserves important context while trimming
 * 5. Artifact Detection - Identifies content suitable for artifacts
 * 6. Project Knowledge Integration - Manages document references
 * 7. Sliding Window with Summaries - Keeps recent messages + summarized history
 */

// Token estimation (Claude uses ~4 chars per token on average)
const CHARS_PER_TOKEN = 4;

// Model context limits
const MODEL_LIMITS = {
  'claude-3-opus': 200000,
  'claude-3-sonnet': 200000,
  'claude-3-haiku': 200000,
  'claude-3.5-sonnet': 200000,
  'claude-3.5-haiku': 200000,
  'claude-sonnet-4': 200000,
  'claude-opus-4': 200000,
  'claude-opus-4-1m': 1000000,    // 1M token access
  'claude-sonnet-4-1m': 1000000,
};

// Default configuration
const DEFAULT_OPTIMIZER_CONFIG = {
  // Context limits
  model: 'claude-sonnet-4',
  maxContextTokens: null,        // Auto-detect from model, or override
  targetContextUsage: 0.85,      // Trigger compaction at 85% usage
  reserveOutputTokens: 8192,     // Reserve tokens for response
  
  // Compaction settings
  enableAutoCompaction: true,
  compactionStrategy: 'smart',   // 'smart', 'sliding-window', 'summarize-all'
  keepRecentMessages: 10,        // Always keep last N messages uncompacted
  summaryMaxTokens: 2000,        // Max tokens for history summary
  
  // Message consolidation
  enableConsolidation: true,
  consolidateThreshold: 50,      // Merge messages under N tokens
  maxConsolidatedMessages: 5,    // Max messages to merge into one
  
  // Artifact optimization
  enableArtifactDetection: true,
  artifactThreshold: 500,        // Suggest artifact for content > N tokens
  artifactTypes: ['code', 'json', 'markdown', 'html', 'csv'],
  
  // Project knowledge
  enableProjectKnowledge: true,
  projectKnowledgeRef: null,     // Reference to project knowledge base
  
  // Callbacks
  onCompaction: null,            // (summary, removedCount) => void
  onTokenWarning: null,          // (usage, limit) => void
  onArtifactSuggestion: null,    // (content, type) => void
};

/**
 * Estimate token count for text
 */
function estimateTokens(text) {
  if (!text) return 0;
  // More accurate estimation considering code, whitespace, etc.
  const codeBlocks = (text.match(/```[\s\S]*?```/g) || []).join('');
  const normalText = text.replace(/```[\s\S]*?```/g, '');
  
  // Code is denser, ~3 chars per token
  const codeTokens = Math.ceil(codeBlocks.length / 3);
  const textTokens = Math.ceil(normalText.length / CHARS_PER_TOKEN);
  
  return codeTokens + textTokens;
}

/**
 * Estimate tokens for a message object
 */
function estimateMessageTokens(message) {
  let tokens = 0;
  
  // Content tokens
  if (typeof message.content === 'string') {
    tokens += estimateTokens(message.content);
  } else if (Array.isArray(message.content)) {
    message.content.forEach(block => {
      if (block.type === 'text') {
        tokens += estimateTokens(block.text);
      } else if (block.type === 'image') {
        // Images cost ~85 tokens per tile (512x512)
        tokens += 85 * (block.tiles || 1);
      } else if (block.type === 'document') {
        tokens += estimateTokens(block.text || '') + 100; // Overhead
      }
    });
  }
  
  // Role overhead (~4 tokens)
  tokens += 4;
  
  // Tool use overhead
  if (message.tool_calls) {
    tokens += 50 * message.tool_calls.length;
  }
  
  return tokens;
}

/**
 * Detect content type for artifact suggestion
 */
function detectContentType(content) {
  if (!content) return null;
  
  // Code detection
  const codePatterns = [
    { pattern: /```(\w+)?\n[\s\S]{200,}```/, type: 'code' },
    { pattern: /^(import|from|const|let|var|function|class|def|public|private)\s/m, type: 'code' },
    { pattern: /<\?php|<html|<!DOCTYPE/i, type: 'code' },
  ];
  
  for (const { pattern, type } of codePatterns) {
    if (pattern.test(content)) return type;
  }
  
  // JSON detection
  if (/^\s*[\[{]/.test(content) && /[\]}]\s*$/.test(content)) {
    try {
      JSON.parse(content);
      return 'json';
    } catch {}
  }
  
  // Markdown with headers
  if (/^#{1,6}\s.+$/m.test(content) && content.length > 500) {
    return 'markdown';
  }
  
  // CSV detection
  if (/^[\w"]+,[\w"]+/.test(content) && content.split('\n').length > 5) {
    return 'csv';
  }
  
  // HTML
  if (/<(div|span|table|ul|ol|p|h[1-6])[^>]*>/i.test(content)) {
    return 'html';
  }
  
  return null;
}

/**
 * Generate summary prompt for compaction
 */
function createSummaryPrompt(messages) {
  const conversationText = messages.map(m => 
    `${m.role.toUpperCase()}: ${typeof m.content === 'string' ? m.content : JSON.stringify(m.content)}`
  ).join('\n\n---\n\n');
  
  return `Summarize this conversation history concisely, preserving:
1. Key decisions and conclusions
2. Important facts, names, and numbers mentioned
3. Context needed for continuing the conversation
4. Any code or technical details that were established

Be concise but comprehensive. Format as bullet points.

CONVERSATION:
${conversationText}

SUMMARY:`;
}

/**
 * Main Context Optimizer Class
 */
export class ClaudeContextOptimizer {
  constructor(config = {}) {
    this.config = { ...DEFAULT_OPTIMIZER_CONFIG, ...config };
    this.maxTokens = this.config.maxContextTokens || MODEL_LIMITS[this.config.model] || 200000;
    this.history = [];
    this.compactedHistory = null;
    this.tokenUsage = { current: 0, peak: 0 };
    this.stats = {
      totalMessages: 0,
      compactions: 0,
      consolidations: 0,
      artifactsSuggested: 0,
      tokensSaved: 0,
    };
  }

  /**
   * Get current token usage info
   */
  getTokenUsage() {
    const available = this.maxTokens - this.config.reserveOutputTokens;
    return {
      current: this.tokenUsage.current,
      available,
      limit: this.maxTokens,
      percentage: (this.tokenUsage.current / available) * 100,
      remaining: available - this.tokenUsage.current,
      needsCompaction: this.tokenUsage.current > available * this.config.targetContextUsage,
    };
  }

  /**
   * Add a message and optimize if needed
   */
  async addMessage(message, options = {}) {
    const messageTokens = estimateMessageTokens(message);
    
    // Check for artifact suggestion
    if (this.config.enableArtifactDetection && message.role === 'assistant') {
      this.checkArtifactSuggestion(message.content);
    }
    
    // Add to history
    this.history.push({
      ...message,
      _tokens: messageTokens,
      _timestamp: Date.now(),
    });
    
    this.tokenUsage.current += messageTokens;
    this.tokenUsage.peak = Math.max(this.tokenUsage.peak, this.tokenUsage.current);
    this.stats.totalMessages++;
    
    // Check if compaction needed
    const usage = this.getTokenUsage();
    if (usage.needsCompaction && this.config.enableAutoCompaction) {
      await this.compact(options.summaryClient);
    }
    
    // Warn if approaching limit
    if (usage.percentage > 90 && this.config.onTokenWarning) {
      this.config.onTokenWarning(usage.current, usage.available);
    }
    
    return usage;
  }

  /**
   * Consolidate short consecutive messages from same role
   */
  consolidateMessages(messages) {
    if (!this.config.enableConsolidation) return messages;
    
    const consolidated = [];
    let buffer = [];
    let bufferRole = null;
    let bufferTokens = 0;
    
    const flushBuffer = () => {
      if (buffer.length === 0) return;
      
      if (buffer.length === 1) {
        consolidated.push(buffer[0]);
      } else {
        // Merge messages
        const mergedContent = buffer.map(m => 
          typeof m.content === 'string' ? m.content : JSON.stringify(m.content)
        ).join('\n\n');
        
        consolidated.push({
          role: bufferRole,
          content: mergedContent,
          _consolidated: buffer.length,
          _tokens: estimateTokens(mergedContent),
        });
        
        this.stats.consolidations++;
        this.stats.tokensSaved += buffer.reduce((sum, m) => sum + (m._tokens || 0), 0) - estimateTokens(mergedContent);
      }
      
      buffer = [];
      bufferRole = null;
      bufferTokens = 0;
    };
    
    for (const msg of messages) {
      const msgTokens = msg._tokens || estimateMessageTokens(msg);
      
      // Check if we should buffer this message
      const shouldBuffer = 
        msgTokens < this.config.consolidateThreshold &&
        buffer.length < this.config.maxConsolidatedMessages &&
        (bufferRole === null || bufferRole === msg.role);
      
      if (shouldBuffer) {
        buffer.push(msg);
        bufferRole = msg.role;
        bufferTokens += msgTokens;
      } else {
        flushBuffer();
        
        if (msgTokens < this.config.consolidateThreshold) {
          buffer.push(msg);
          bufferRole = msg.role;
          bufferTokens = msgTokens;
        } else {
          consolidated.push(msg);
        }
      }
    }
    
    flushBuffer();
    return consolidated;
  }

  /**
   * Compact history to reduce token usage
   */
  async compact(summaryClient = null) {
    if (this.history.length <= this.config.keepRecentMessages) {
      return false; // Not enough messages to compact
    }
    
    const recentCount = this.config.keepRecentMessages;
    const toCompact = this.history.slice(0, -recentCount);
    const toKeep = this.history.slice(-recentCount);
    
    let summary;
    
    switch (this.config.compactionStrategy) {
      case 'summarize-all':
        summary = await this.generateSummary(toCompact, summaryClient);
        break;
        
      case 'sliding-window':
        // Just drop old messages, keep a brief note
        summary = this.createSlidingWindowSummary(toCompact);
        break;
        
      case 'smart':
      default:
        // Smart: summarize important parts, drop redundant
        summary = await this.smartCompact(toCompact, summaryClient);
        break;
    }
    
    // Calculate tokens saved
    const oldTokens = toCompact.reduce((sum, m) => sum + (m._tokens || 0), 0);
    const newTokens = estimateTokens(summary);
    this.stats.tokensSaved += oldTokens - newTokens;
    
    // Update history
    this.compactedHistory = {
      summary,
      messageCount: toCompact.length,
      tokens: newTokens,
      timestamp: Date.now(),
    };
    
    this.history = toKeep;
    this.tokenUsage.current = newTokens + toKeep.reduce((sum, m) => sum + (m._tokens || 0), 0);
    this.stats.compactions++;
    
    // Callback
    if (this.config.onCompaction) {
      this.config.onCompaction(summary, toCompact.length);
    }
    
    return true;
  }

  /**
   * Generate summary using Claude API
   */
  async generateSummary(messages, client) {
    if (!client) {
      // Fallback to simple extraction
      return this.createSimpleSummary(messages);
    }
    
    try {
      const response = await client.messages.create({
        model: 'claude-3-haiku-20240307', // Use fast model for summaries
        max_tokens: this.config.summaryMaxTokens,
        messages: [{
          role: 'user',
          content: createSummaryPrompt(messages),
        }],
      });
      
      return response.content[0].text;
    } catch (error) {
      console.warn('Summary generation failed, using fallback:', error);
      return this.createSimpleSummary(messages);
    }
  }

  /**
   * Create simple summary without API call
   */
  createSimpleSummary(messages) {
    const keyPoints = [];
    
    for (const msg of messages) {
      const content = typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content);
      
      // Extract key information
      // Questions and answers
      if (msg.role === 'user' && content.includes('?')) {
        const question = content.split('?')[0] + '?';
        if (question.length < 200) keyPoints.push(`Q: ${question.trim()}`);
      }
      
      // Code blocks (just note they exist)
      const codeBlocks = content.match(/```(\w+)?/g);
      if (codeBlocks) {
        const langs = [...new Set(codeBlocks.map(b => b.replace('```', '') || 'code'))];
        keyPoints.push(`Code shared: ${langs.join(', ')}`);
      }
      
      // Lists and decisions
      if (content.includes('1.') || content.includes('- ')) {
        const listItems = content.match(/^[\d\-\*]\.\s*.+$/gm);
        if (listItems && listItems.length <= 5) {
          keyPoints.push(...listItems.slice(0, 3));
        }
      }
    }
    
    return `[Conversation Summary - ${messages.length} messages]\n\n` + 
           (keyPoints.length > 0 ? keyPoints.slice(0, 15).join('\n') : 'General discussion');
  }

  /**
   * Create sliding window summary (minimal)
   */
  createSlidingWindowSummary(messages) {
    const userMessages = messages.filter(m => m.role === 'user').length;
    const assistantMessages = messages.filter(m => m.role === 'assistant').length;
    
    return `[Previous conversation: ${userMessages} user messages, ${assistantMessages} assistant responses - context trimmed for length]`;
  }

  /**
   * Smart compaction - analyze and preserve important content
   */
  async smartCompact(messages, client) {
    // Score messages by importance
    const scored = messages.map((msg, idx) => {
      let score = 0;
      const content = typeof msg.content === 'string' ? msg.content : '';
      
      // Code is important
      if (content.includes('```')) score += 30;
      
      // Questions are important
      if (content.includes('?')) score += 20;
      
      // Names/entities
      if (/[A-Z][a-z]+\s[A-Z][a-z]+/.test(content)) score += 10;
      
      // Numbers/data
      if (/\d{4,}|\$[\d,]+|[\d.]+%/.test(content)) score += 15;
      
      // Recent messages more important
      score += (idx / messages.length) * 20;
      
      // Tool use
      if (msg.tool_calls) score += 25;
      
      return { msg, score, idx };
    });
    
    // Sort by score, keep top important
    scored.sort((a, b) => b.score - a.score);
    const important = scored.slice(0, Math.ceil(messages.length * 0.3));
    important.sort((a, b) => a.idx - b.idx); // Restore order
    
    // Generate summary for important messages
    if (client && important.length > 3) {
      return await this.generateSummary(important.map(i => i.msg), client);
    }
    
    return this.createSimpleSummary(important.map(i => i.msg));
  }

  /**
   * Check if content should be suggested as artifact
   */
  checkArtifactSuggestion(content) {
    if (!content || typeof content !== 'string') return;
    
    const tokens = estimateTokens(content);
    if (tokens < this.config.artifactThreshold) return;
    
    const contentType = detectContentType(content);
    if (contentType && this.config.artifactTypes.includes(contentType)) {
      this.stats.artifactsSuggested++;
      
      if (this.config.onArtifactSuggestion) {
        this.config.onArtifactSuggestion(content, contentType);
      }
      
      return { type: contentType, tokens };
    }
    
    return null;
  }

  /**
   * Get optimized messages for API call
   */
  getOptimizedMessages(options = {}) {
    let messages = [];
    
    // Add compacted history as system context if exists
    if (this.compactedHistory) {
      messages.push({
        role: 'user',
        content: `[CONVERSATION CONTEXT]\n${this.compactedHistory.summary}\n[END CONTEXT]\n\nContinuing from above context:`,
      });
      messages.push({
        role: 'assistant',
        content: 'I understand the context. Please continue.',
      });
    }
    
    // Add current history
    let currentMessages = [...this.history];
    
    // Consolidate if enabled
    if (this.config.enableConsolidation) {
      currentMessages = this.consolidateMessages(currentMessages);
    }
    
    // Add project knowledge reference if available
    if (this.config.enableProjectKnowledge && this.config.projectKnowledgeRef) {
      const knowledgeNote = `[Using project knowledge: ${this.config.projectKnowledgeRef}]`;
      if (messages.length > 0) {
        messages[0].content = knowledgeNote + '\n\n' + messages[0].content;
      }
    }
    
    // Clean messages for API
    messages.push(...currentMessages.map(m => ({
      role: m.role,
      content: m.content,
      ...(m.tool_calls && { tool_calls: m.tool_calls }),
      ...(m.tool_call_id && { tool_call_id: m.tool_call_id }),
    })));
    
    return messages;
  }

  /**
   * Get optimizer statistics
   */
  getStats() {
    return {
      ...this.stats,
      currentTokens: this.tokenUsage.current,
      peakTokens: this.tokenUsage.peak,
      historyLength: this.history.length,
      hasCompactedHistory: !!this.compactedHistory,
      compactedMessageCount: this.compactedHistory?.messageCount || 0,
      efficiency: this.stats.tokensSaved > 0 
        ? ((this.stats.tokensSaved / (this.tokenUsage.current + this.stats.tokensSaved)) * 100).toFixed(1) + '%'
        : '0%',
    };
  }

  /**
   * Reset optimizer state
   */
  reset() {
    this.history = [];
    this.compactedHistory = null;
    this.tokenUsage = { current: 0, peak: 0 };
  }

  /**
   * Export conversation for backup/transfer
   */
  export() {
    return {
      history: this.history,
      compactedHistory: this.compactedHistory,
      tokenUsage: this.tokenUsage,
      stats: this.stats,
      config: this.config,
      exportedAt: Date.now(),
    };
  }

  /**
   * Import conversation
   */
  import(data) {
    this.history = data.history || [];
    this.compactedHistory = data.compactedHistory || null;
    this.tokenUsage = data.tokenUsage || { current: 0, peak: 0 };
    this.stats = { ...this.stats, ...data.stats };
  }
}

/**
 * Token Counter Component for UI
 */
export function TokenCounter({ optimizer, showDetails = false }) {
  const usage = optimizer.getTokenUsage();
  const stats = optimizer.getStats();
  
  const getStatusColor = () => {
    if (usage.percentage > 90) return '#ef4444';
    if (usage.percentage > 75) return '#f59e0b';
    return '#22c55e';
  };
  
  return {
    render: () => `
      <div class="token-counter" style="
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 12px;
        background: var(--chat-surface, #18181b);
        border: 1px solid var(--chat-border, #27272a);
        border-radius: 8px;
        font-size: 12px;
        font-family: var(--chat-font-mono, monospace);
      ">
        <div style="display: flex; align-items: center; gap: 6px;">
          <div style="
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: ${getStatusColor()};
          "></div>
          <span>${usage.current.toLocaleString()} / ${usage.available.toLocaleString()}</span>
        </div>
        
        <div style="
          flex: 1;
          height: 4px;
          background: var(--chat-border, #27272a);
          border-radius: 2px;
          overflow: hidden;
        ">
          <div style="
            width: ${Math.min(usage.percentage, 100)}%;
            height: 100%;
            background: ${getStatusColor()};
            transition: width 0.3s ease;
          "></div>
        </div>
        
        <span style="color: var(--chat-text-muted, #71717a);">
          ${usage.percentage.toFixed(1)}%
        </span>
        
        ${showDetails ? `
          <span style="color: var(--chat-text-muted, #71717a); font-size: 10px;">
            Saved: ${stats.tokensSaved.toLocaleString()} | 
            Compactions: ${stats.compactions}
          </span>
        ` : ''}
      </div>
    `,
    usage,
    stats,
  };
}

/**
 * Integration helper for AIChatModulePro
 */
export function createOptimizedSendHandler(anthropicClient, optimizer, options = {}) {
  const {
    model = 'claude-sonnet-4-20250514',
    maxTokens = 8192,
    systemPrompt = null,
    tools = null,
    onTokenUpdate = null,
  } = options;
  
  return async function optimizedSendMessage(message, files, callbacks) {
    // Add user message to optimizer
    await optimizer.addMessage({ role: 'user', content: message });
    
    // Get optimized messages
    const messages = optimizer.getOptimizedMessages();
    
    // Notify token update
    if (onTokenUpdate) {
      onTokenUpdate(optimizer.getTokenUsage());
    }
    
    // Report processing step
    callbacks.onProcessingStep({ label: 'Optimizing context', status: 'running' });
    const stats = optimizer.getStats();
    callbacks.onProcessingStepUpdate(0, { 
      status: 'complete', 
      duration: 50,
      detail: `${stats.currentTokens.toLocaleString()} tokens (${stats.efficiency} saved)`
    });
    
    // Make API call
    callbacks.onProcessingStep({ label: 'Calling Claude API', status: 'running' });
    
    try {
      const requestBody = {
        model,
        max_tokens: maxTokens,
        messages,
        ...(systemPrompt && { system: systemPrompt }),
        ...(tools && { tools }),
        stream: true,
      };
      
      // Handle files if present
      if (files?.length) {
        const lastMessage = messages[messages.length - 1];
        if (lastMessage.role === 'user') {
          lastMessage.content = [
            { type: 'text', text: lastMessage.content },
            ...await Promise.all(files.map(async f => {
              if (f.type.startsWith('image/')) {
                const base64 = await fileToBase64(f);
                return { type: 'image', source: { type: 'base64', media_type: f.type, data: base64 } };
              }
              return { type: 'text', text: `[File: ${f.name}]` };
            })),
          ];
        }
      }
      
      const stream = await anthropicClient.messages.stream(requestBody);
      
      callbacks.onProcessingStepUpdate(1, { status: 'complete', duration: 100, detail: 'Streaming response' });
      callbacks.onProcessingStep({ label: 'Generating response', status: 'running' });
      
      let fullContent = '';
      let thinkingContent = '';
      let inputTokens = 0;
      let outputTokens = 0;
      
      for await (const event of stream) {
        if (event.type === 'content_block_delta') {
          if (event.delta.type === 'thinking_delta') {
            thinkingContent += event.delta.thinking;
            callbacks.onThinking({ content: thinkingContent });
          } else if (event.delta.type === 'text_delta') {
            fullContent += event.delta.text;
            callbacks.onContentDelta(event.delta.text);
          }
        } else if (event.type === 'message_delta') {
          if (event.usage) {
            outputTokens = event.usage.output_tokens;
          }
        } else if (event.type === 'message_start') {
          if (event.message.usage) {
            inputTokens = event.message.usage.input_tokens;
          }
        }
      }
      
      // Add assistant response to optimizer
      await optimizer.addMessage({ role: 'assistant', content: fullContent });
      
      // Final token update
      if (onTokenUpdate) {
        onTokenUpdate(optimizer.getTokenUsage());
      }
      
      callbacks.onProcessingStepUpdate(2, { 
        status: 'complete', 
        detail: `${outputTokens} tokens generated`
      });
      
      return {
        content: fullContent,
        model,
        usage: { input_tokens: inputTokens, output_tokens: outputTokens },
      };
      
    } catch (error) {
      callbacks.onProcessingStepUpdate(1, { status: 'error' });
      throw error;
    }
  };
}

/**
 * Helper: Convert file to base64
 */
async function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// Export utilities
export {
  estimateTokens,
  estimateMessageTokens,
  detectContentType,
  MODEL_LIMITS,
  DEFAULT_OPTIMIZER_CONFIG,
};
