# AI Chat Module Pro

Enterprise-grade chat component for AI applications with **built-in Claude API context optimizer** and **prompt linter**.

## 🚀 Key Capabilities

### Context Optimizer
- **Automatic Compaction** - Summarizes older messages when nearing context limit
- **1M Token Support** - Extended conversations with claude-opus-4-1m / claude-sonnet-4-1m
- **Message Consolidation** - Merges short messages to reduce overhead
- **Artifact Detection** - Suggests artifacts for long code/content
- **Project Knowledge** - Reference documents without re-uploading
- **Real-time Token Tracking** - Visual usage bar with warnings

### Prompt Linter (NEW)
- **Language Detection** - Auto-detect FR/EN
- **Task Type Inference** - create/modify/explain/analyze/fix
- **Specificity Scoring** - Rate prompt quality 0-100
- **Issue Detection** - Negations, conflicts, vague references
- **Auto-Fix** - Smart rewrites for better results
- **Token Estimation** - Cost prediction before sending

## Features

| Feature | Description |
|---------|-------------|
| **Auto-Resizing Input** | Dynamic height (44-300px), Shift+Enter for newlines |
| **Processing Steps** | Multi-step progress with timing, status updates |
| **Thinking Blocks** | Collapsible reasoning display with duration |
| **Tool Calls** | Input/output visualization, status tracking |
| **Auto-File Creation** | Creates downloadable file when response > threshold |
| **File Upload** | Drag & drop, validation, image previews, ZIP support |
| **Streaming** | Real-time content with cursor, stop button |
| **Code Blocks** | Copy button, language labels, inline code |
| **Theming** | Dark/Light toggle, full CSS variable control |

## Quick Start

```jsx
import AIChatModulePro from './AIChatModulePro';

function App() {
  const handleSend = async (message, files, callbacks) => {
    // Show processing step
    callbacks.onProcessingStep({ label: 'Processing', status: 'running' });
    
    // Call your API
    const response = await fetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message })
    });
    
    // Update step
    callbacks.onProcessingStepUpdate(0, { status: 'complete', duration: 1000 });
    
    return response.json();
  };

  return (
    <div style={{ height: '100vh' }}>
      <AIChatModulePro onSendMessage={handleSend} />
    </div>
  );
}
```

## Callback API

```jsx
const handleSend = async (message, files, callbacks) => {
  // Available callbacks:
  callbacks.onProcessingStep({ label, status, detail })
  callbacks.onProcessingStepUpdate(index, { status, duration, detail })
  callbacks.onThinking({ content, duration })
  callbacks.onToolCall({ type, name, status, input })
  callbacks.onToolCallUpdate(index, { status, duration, output, error })
  callbacks.onContent(fullContent)
  callbacks.onContentDelta(chunk)  // For streaming
  
  // Abort signal for cancellation
  callbacks.signal.aborted
};
```

## Configuration

```jsx
<AIChatModulePro
  config={{
    // Appearance
    title: 'AI Assistant',
    subtitle: 'Powered by Claude',
    placeholder: 'Ask anything...',
    theme: 'dark', // 'dark', 'light', or custom object
    
    // Input behavior
    minInputHeight: 44,
    maxInputHeight: 300,
    submitOnEnter: true,
    
    // Auto-file (creates file when response exceeds threshold)
    autoFileEnabled: true,
    autoFileThreshold: 4000,
    autoFileFormat: 'md',
    autoFileName: 'response',
    
    // File upload
    enableFileUpload: true,
    maxFileSize: 100 * 1024 * 1024,
    maxFiles: 10,
    allowedFileTypes: null, // null = all types
    
    // Feature toggles
    showProcessingSteps: true,
    showThinkingBlocks: true,
    showToolCalls: true,
    thinkingBlocksCollapsed: true,
    enableMessageEdit: true,
    enableMessageRetry: true,
    enableMessageCopy: true,
    enableCodeCopy: true,
    showScrollToBottom: true,
  }}
  onSendMessage={handleSend}
  onStopGeneration={() => console.log('Stopped')}
  onFileDownload={(file) => window.open(file.url)}
  initialMessages={[]}
/>
```

## Ref API

```jsx
const chatRef = useRef();

// Available methods:
chatRef.current.addMessage({ role: 'assistant', content: '...' })
chatRef.current.clearMessages()
chatRef.current.setInput('text')
chatRef.current.focus()
chatRef.current.scrollToBottom()
chatRef.current.getMessages()
```

## Response Formats

```jsx
// Simple string
return 'Hello!';

// Object with files
return {
  content: 'Here is your file',
  files: [{ name: 'result.txt', size: 1024, url: 'blob:...' }],
  model: 'claude-3'
};

// Streaming (use callbacks)
for await (const chunk of stream) {
  callbacks.onContentDelta(chunk);
}
return; // Content already set
```

## Theme Customization

```jsx
const customTheme = {
  '--chat-bg': '#0a0a0a',
  '--chat-surface': '#141414',
  '--chat-border': '#2a2a2a',
  '--chat-text': '#ffffff',
  '--chat-text-muted': '#888888',
  '--chat-accent': '#6366f1',
  '--chat-accent-hover': '#818cf8',
  '--chat-user-bg': '#1e1b4b',
  '--chat-assistant-bg': '#18181b',
  '--chat-success': '#22c55e',
  '--chat-error': '#ef4444',
  '--chat-thinking-bg': '#1a1a2e',
  '--chat-tool-bg': '#0c1a1a',
  '--chat-code-bg': '#0d0d0f',
  '--chat-radius': '10px',
  '--chat-font': "'Geist', sans-serif",
  '--chat-font-mono': "'Geist Mono', monospace",
};

<AIChatModulePro config={{ theme: customTheme }} />
```

## Files

- `AIChatModulePro.jsx` - Main component (~1200 lines)
- `ClaudeContextOptimizer.js` - Context management & token optimization
- `AIChatWithOptimizer.jsx` - Integrated component with optimizer
- `Demo.jsx` - Full feature demonstration

## Context Optimizer Usage

### Basic Setup

```jsx
import Anthropic from '@anthropic-ai/sdk';
import AIChatWithOptimizer from './AIChatWithOptimizer';

const client = new Anthropic({ apiKey: 'your-api-key' });

function App() {
  return (
    <AIChatWithOptimizer
      anthropicClient={client}
      model="claude-sonnet-4-20250514"
      maxTokens={8192}
      systemPrompt="You are a helpful assistant."
      onTokenUpdate={(usage) => console.log('Tokens:', usage)}
      onCompaction={(summary, count) => console.log(`Compacted ${count} messages`)}
    />
  );
}
```

### Optimizer Configuration

```jsx
<AIChatWithOptimizer
  anthropicClient={client}
  model="claude-opus-4-1m"  // 1M token model
  optimizerConfig={{
    // Context management
    targetContextUsage: 0.85,      // Compact at 85% usage
    reserveOutputTokens: 8192,     // Reserve for response
    
    // Compaction
    enableAutoCompaction: true,
    compactionStrategy: 'smart',   // 'smart', 'sliding-window', 'summarize-all'
    keepRecentMessages: 10,        // Keep last N uncompacted
    summaryMaxTokens: 2000,
    
    // Consolidation
    enableConsolidation: true,
    consolidateThreshold: 50,      // Merge messages < 50 tokens
    
    // Artifacts
    enableArtifactDetection: true,
    artifactThreshold: 500,        // Suggest artifact > 500 tokens
  }}
/>
```

### Standalone Optimizer

```jsx
import { ClaudeContextOptimizer, estimateTokens } from './ClaudeContextOptimizer';

const optimizer = new ClaudeContextOptimizer({
  model: 'claude-sonnet-4',
  enableAutoCompaction: true,
  onCompaction: (summary, count) => {
    console.log(`Compacted ${count} messages into summary`);
  },
});

// Add messages
await optimizer.addMessage({ role: 'user', content: 'Hello!' });
await optimizer.addMessage({ role: 'assistant', content: 'Hi there!' });

// Get optimized messages for API
const messages = optimizer.getOptimizedMessages();

// Check usage
const usage = optimizer.getTokenUsage();
console.log(`${usage.current}/${usage.available} tokens (${usage.percentage.toFixed(1)}%)`);

// Get stats
const stats = optimizer.getStats();
console.log(`Saved ${stats.tokensSaved} tokens (${stats.efficiency})`);
```

### Compaction Strategies

| Strategy | Description | Best For |
|----------|-------------|----------|
| `smart` | Scores messages by importance, summarizes key content | General use |
| `sliding-window` | Drops old messages, keeps minimal note | Speed-critical |
| `summarize-all` | Full summary via Claude Haiku | Maximum context preservation |

### Token Estimation

```jsx
import { estimateTokens, estimateMessageTokens } from './ClaudeContextOptimizer';

// Text
const tokens = estimateTokens("Hello, world!"); // ~4

// Full message
const msgTokens = estimateMessageTokens({
  role: 'user',
  content: [
    { type: 'text', text: 'Describe this image' },
    { type: 'image', tiles: 4 }  // ~340 tokens
  ]
});
```

### Project Knowledge Integration

```jsx
<AIChatWithOptimizer
  anthropicClient={client}
  projectKnowledge={{
    name: 'Product Documentation',
    summary: 'API reference, tutorials, and guides for ProductX v2.0',
    // Documents are stored in Claude Projects, not re-sent each message
  }}
/>
```

## License

MIT

---

## Prompt Linter Usage

### Basic Usage

```javascript
import { lintPrompt, optimizePrompt, getLintSummary } from './PromptLinter';

// Analyze a prompt
const report = lintPrompt("create something cool");
console.log(report.score);        // 45 (low score)
console.log(report.issues);       // [{type: 'ambiguousScope', ...}]
console.log(report.optimized);    // Improved version

// Get human-readable summary
console.log(getLintSummary("don't use loops, make it short but detailed"));
// 🔍 Prompt Analysis (score: 32/100)
//    Language: EN
//    Task type: unknown
//    Issues (2):
//    🔴 Negations detected
//    🔴 Conflicting instructions
```

### Integration with Chat Module

```jsx
import AIChatModulePro from './AIChatModulePro';
import { lintPrompt, optimizePrompt } from './PromptLinter';

function App() {
  const handleSend = async (message, files, callbacks) => {
    // Lint the prompt before sending
    const lintReport = lintPrompt(message);
    
    // Show lint step
    callbacks.onProcessingStep({ 
      label: `Linting (score: ${lintReport.score})`, 
      status: 'running' 
    });
    
    // Use optimized prompt if score is low
    const finalMessage = lintReport.score < 70 
      ? lintReport.optimized 
      : message;
    
    callbacks.onProcessingStepUpdate(0, { 
      status: 'complete', 
      detail: lintReport.issues.length 
        ? `${lintReport.issues.length} issues auto-fixed` 
        : 'No issues'
    });
    
    // Continue with API call...
    const response = await fetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message: finalMessage })
    });
    
    return response.json();
  };

  return <AIChatModulePro onSendMessage={handleSend} />;
}
```

### Lint Report Structure

```javascript
{
  language: 'en',           // Detected language
  taskType: {
    type: 'create',         // create|modify|explain|analyze|fix|unknown
    expectedOutput: 'file',
    confidence: 0.8
  },
  specificity: {
    score: 65,
    wordCount: 12,
    suggestions: ['Add specific numbers']
  },
  tokens: {
    inputTokens: 45,
    estimatedOutputTokens: 675,
    estimatedCost: 0.0112
  },
  issues: [
    {
      type: 'negation',
      severity: 'high',
      message: 'Negations detected',
      matches: ["don't"],
      fix: 'Reframe positively'
    }
  ],
  issueCount: 1,
  score: 52,                // Overall score 0-100
  optimized: '...',         // Auto-fixed prompt
  suggestions: ['...'],
  needsOptimization: true   // score < 70
}
```

### Available Functions

| Function | Description |
|----------|-------------|
| `lintPrompt(text)` | Full analysis with issues and optimization |
| `optimizePrompt(text)` | Apply auto-fixes to improve prompt |
| `detectLanguage(text)` | Returns 'en' or 'fr' |
| `inferTaskType(text, lang)` | Detect task type |
| `calculateSpecificity(text, lang)` | Score specificity 0-100 |
| `estimateTokens(text)` | Estimate input/output tokens and cost |
| `getLintSummary(text)` | Human-readable analysis string |
