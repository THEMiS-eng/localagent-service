import React, { useRef, useState } from 'react';
import AIChatModulePro, { generateId, createDownloadableFile } from './AIChatModulePro';

/**
 * COMPREHENSIVE DEMO
 * 
 * This demonstrates all features:
 * - Processing steps with timing
 * - Thinking blocks (collapsible)
 * - Tool calls with input/output
 * - Auto-file creation for long responses
 * - File upload/download
 * - Streaming responses
 * - Error handling and retry
 */

// Simulate a full AI response with all features
async function simulateAIResponse(message, files, callbacks) {
  const { 
    onProcessingStep, 
    onProcessingStepUpdate, 
    onThinking, 
    onToolCall, 
    onToolCallUpdate,
    onContentDelta 
  } = callbacks;

  // Step 1: Understanding
  onProcessingStep({ label: 'Understanding request', status: 'running' });
  await delay(800);
  onProcessingStepUpdate(0, { status: 'complete', duration: 800, detail: 'Parsed user intent' });

  // Step 2: Thinking
  onProcessingStep({ label: 'Reasoning', status: 'running' });
  const thinkingContent = `Let me analyze this request...

The user wants: "${message}"
${files?.length ? `\nThey've attached ${files.length} file(s) for context.` : ''}

I should:
1. Consider the context carefully
2. Break down the problem
3. Provide a comprehensive response
4. Include code examples if relevant`;
  
  onThinking({ content: thinkingContent, duration: 1200 });
  await delay(1200);
  onProcessingStepUpdate(1, { status: 'complete', duration: 1200, detail: 'Extended thinking complete' });

  // Step 3: Tool calls (if relevant keywords)
  if (message.toLowerCase().includes('search') || message.toLowerCase().includes('find')) {
    onProcessingStep({ label: 'Using tools', status: 'running' });
    
    onToolCall({
      type: 'web_search',
      name: 'Web Search',
      status: 'running',
      input: { query: message.slice(0, 50) }
    });
    await delay(1500);
    onToolCallUpdate(0, {
      status: 'complete',
      duration: 1500,
      output: {
        results: [
          { title: 'Relevant Result 1', url: 'https://example.com/1' },
          { title: 'Relevant Result 2', url: 'https://example.com/2' },
        ]
      }
    });
    
    onProcessingStepUpdate(2, { status: 'complete', duration: 1500, detail: '1 tool executed' });
  }

  // Step 4: Generating response
  onProcessingStep({ label: 'Generating response', status: 'running' });
  
  // Stream the response
  const response = generateResponse(message, files);
  const words = response.split(' ');
  
  for (let i = 0; i < words.length; i++) {
    await delay(30 + Math.random() * 20);
    onContentDelta(words[i] + ' ');
  }
  
  onProcessingStepUpdate(onProcessingStep.length || 2, { status: 'complete', duration: words.length * 40 });
  
  return response;
}

function generateResponse(message, files) {
  const hasFiles = files?.length > 0;
  
  let response = `Thank you for your message: "${message.slice(0, 50)}${message.length > 50 ? '...' : ''}"

`;

  if (hasFiles) {
    response += `I've received your ${files.length} file(s):
${files.map(f => `- **${f.name}** (${formatSize(f.size)})`).join('\n')}

`;
  }

  response += `Here's a comprehensive response with various formatting:

## Key Points

This demonstrates the chat module's capabilities including **bold text**, *italic text*, and \`inline code\`.

### Code Example

\`\`\`javascript
// Example async function
async function processData(input) {
  const result = await fetch('/api/data', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data: input })
  });
  
  return result.json();
}
\`\`\`

### Features Demonstrated

1. **Processing Steps** - Visual progress indicators
2. **Thinking Blocks** - Collapsible reasoning display
3. **Tool Calls** - Input/output visualization
4. **Auto-File Creation** - Long responses become downloadable
5. **Streaming** - Real-time content delivery

The module supports full markdown rendering, file attachments, and extensive customization.`;

  // Make it long enough to trigger auto-file if we want to demo that
  if (message.toLowerCase().includes('long') || message.toLowerCase().includes('detailed')) {
    response += `

---

## Extended Content (Auto-File Demo)

This additional content demonstrates the auto-file creation feature. When responses exceed the configured threshold (default: 4000 characters), the module automatically:

1. Creates a downloadable file with the full content
2. Truncates the displayed message
3. Shows a download button for the complete response

### Technical Implementation Details

The auto-file system uses the following approach:

\`\`\`typescript
interface AutoFileConfig {
  enabled: boolean;
  threshold: number;      // Character limit
  format: 'md' | 'txt' | 'json';
  fileName: string;
}

function createAutoFile(content: string, config: AutoFileConfig) {
  if (!config.enabled || content.length <= config.threshold) {
    return null;
  }
  
  const blob = new Blob([content], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  
  return {
    name: \`\${config.fileName}-\${Date.now()}.\${config.format}\`,
    size: blob.size,
    url,
    blob
  };
}
\`\`\`

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| autoFileEnabled | boolean | true | Enable auto-file creation |
| autoFileThreshold | number | 4000 | Character limit before creating file |
| autoFileFormat | string | 'md' | Output format (md, txt, json) |
| autoFileName | string | 'response' | Base filename |

### Best Practices

When using the auto-file feature:

- Set appropriate thresholds based on your use case
- Consider the format that best suits your content
- Provide clear UI feedback about file availability
- Handle cleanup of blob URLs when components unmount

This extended section ensures the response exceeds the default 4000 character threshold, triggering the auto-file creation system.`;
  }

  return response;
}

function formatSize(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Main Demo Component
export default function Demo() {
  const chatRef = useRef(null);
  const [config, setConfig] = useState({
    title: 'AI Assistant Pro',
    subtitle: 'With processing visualization',
    showProcessingSteps: true,
    showThinkingBlocks: true,
    showToolCalls: true,
    thinkingBlocksCollapsed: true,
    autoFileEnabled: true,
    autoFileThreshold: 4000,
  });

  const handleSendMessage = async (message, files, callbacks) => {
    return await simulateAIResponse(message, files, callbacks);
  };

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column',
      height: '100vh', 
      background: '#09090b',
      fontFamily: 'system-ui, sans-serif'
    }}>
      {/* Config Panel */}
      <div style={{
        padding: '12px 20px',
        background: '#18181b',
        borderBottom: '1px solid #27272a',
        display: 'flex',
        gap: '16px',
        flexWrap: 'wrap',
        alignItems: 'center'
      }}>
        <span style={{ color: '#a1a1aa', fontSize: '13px', fontWeight: 500 }}>Features:</span>
        {[
          { key: 'showProcessingSteps', label: 'Processing Steps' },
          { key: 'showThinkingBlocks', label: 'Thinking Blocks' },
          { key: 'showToolCalls', label: 'Tool Calls' },
          { key: 'autoFileEnabled', label: 'Auto-File' },
        ].map(({ key, label }) => (
          <label key={key} style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '6px',
            color: '#fafafa',
            fontSize: '13px',
            cursor: 'pointer'
          }}>
            <input
              type="checkbox"
              checked={config[key]}
              onChange={(e) => setConfig(prev => ({ ...prev, [key]: e.target.checked }))}
              style={{ accentColor: '#6366f1' }}
            />
            {label}
          </label>
        ))}
        <div style={{ flex: 1 }} />
        <span style={{ color: '#71717a', fontSize: '12px' }}>
          Try: "search for X" or "give me a long detailed response"
        </span>
      </div>

      {/* Chat Module */}
      <div style={{ flex: 1, minHeight: 0 }}>
        <AIChatModulePro
          ref={chatRef}
          config={config}
          onSendMessage={handleSendMessage}
          onFileDownload={(file) => {
            console.log('Downloading:', file.name);
            if (file.url) {
              const a = document.createElement('a');
              a.href = file.url;
              a.download = file.name;
              a.click();
            }
          }}
        />
      </div>
    </div>
  );
}
