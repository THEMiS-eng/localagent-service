# LocalAgent Chat

Minimal chat components connected to LocalAgent LLM backend.

## Features

- Multi-provider support (MLX, Ollama, Claude, OpenAI)
- Automatic fallback chain (local first, cloud backup)
- THEMIS skill injection
- 100% offline capable (with local providers)
- Clean Vercel-inspired design
- Dark mode support

## Quick Start

### Standalone (No Build Required)

1. Start LocalAgent backend:
```bash
python -m localagent.service.server
```

2. Open in browser:
```
http://localhost:9998/modules/localagent-chat/standalone.html
```

Or with a skill:
```
http://localhost:9998/modules/localagent-chat/standalone.html?skill=construction-forensics
```

### React Component

```tsx
import { SimpleChat } from '@localagent/chat';

function App() {
  return (
    <SimpleChat
      skillName="construction-forensics"
      title="THEMIS Assistant"
      onResponse={(res) => console.log('Provider:', res.provider)}
    />
  );
}
```

### Hook Only

```tsx
import { useLocalAgentChat } from '@localagent/chat';

function MyCustomChat() {
  const {
    messages,
    isLoading,
    error,
    activeProvider,
    sendMessage,
  } = useLocalAgentChat({
    skill_name: 'construction-forensics',
  });

  // Build your own UI...
}
```

### API Functions

```typescript
import { complete, getProviders, setProvider, getStatus } from '@localagent/chat';

// Send completion
const result = await complete({
  prompt: 'Hello!',
  skill_name: 'construction-forensics',
  fallback: true,
});

// Get providers
const { providers, available, active } = await getProviders();

// Set provider
await setProvider('ollama');

// Get full status
const { llm, skills } = await getStatus();
```

## Props (SimpleChat)

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `skillName` | `string` | - | THEMIS skill to inject |
| `provider` | `string` | - | Force specific provider |
| `system` | `string` | - | System prompt |
| `title` | `string` | `'LocalAgent Chat'` | Header title |
| `showHeader` | `boolean` | `true` | Show header |
| `className` | `string` | - | Custom class |
| `onResponse` | `function` | - | Callback on response |
| `onError` | `function` | - | Callback on error |

## Providers

| Provider | Type | Priority | Description |
|----------|------|----------|-------------|
| `mlx` | Local | 0 | Apple Silicon (M1/M2/M3) |
| `ollama` | Local | 1 | Ollama server |
| `claude` | Cloud | 1 | Anthropic API |
| `openai` | Cloud | 2 | OpenAI API |

Fallback order: mlx → ollama → claude → openai

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/llm/complete` | POST | Send completion |
| `/api/llm/providers` | GET | List providers |
| `/api/llm/provider` | POST | Set active provider |
| `/api/llm/status` | GET | Full status |
| `/api/llm/test` | POST | Test provider |

## Files

```
localagent-chat/
├── lib/
│   └── localagent-provider.ts   # API + Hook
├── components/
│   └── SimpleChat.tsx           # React component
├── standalone.html              # No-build version
├── index.ts                     # Exports
├── package.json
└── README.md
```
