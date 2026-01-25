# Whisper Module

Standalone speech-to-text module using OpenAI Whisper via transformers.js.

## Features

- **Multilingual**: Supports 99+ languages with auto-detection
- **Offline**: Runs entirely in browser after model download
- **Cached**: Model cached in browser IndexedDB
- **Configurable**: Multiple model sizes (tiny → medium)

## Quick Start

```html
<script type="module">
import { WhisperTranscriber } from './WhisperTranscriber.js';

const whisper = new WhisperTranscriber();

// Load model (cached after first download)
await whisper.load('whisper-small', (p) => {
  console.log(`Loading: ${p.progress}%`);
});

// Transcribe audio (Float32Array at 16kHz)
const result = await whisper.transcribe(audioData);
console.log(result.text);      // "Hello world"
console.log(result.language);  // "en"
console.log(result.duration);  // 1.23 (seconds)
</script>
```

## API Reference

### Constructor

```javascript
const whisper = new WhisperTranscriber();
```

### Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `load(model, onProgress)` | Load Whisper model | `Promise<boolean>` |
| `transcribe(audioData, options)` | Transcribe audio | `Promise<{text, language, duration}>` |
| `isLoaded()` | Check if ready | `boolean` |
| `isLoading()` | Check if loading | `boolean` |
| `getModel()` | Get current model name | `string` |
| `unload()` | Free memory | `Promise<void>` |

### Available Models

| Model | Size | Multilingual | Speed |
|-------|------|--------------|-------|
| `whisper-tiny` | ~40MB | No | Fastest |
| `whisper-tiny.en` | ~40MB | No | Fastest |
| `whisper-base` | ~75MB | Yes | Fast |
| `whisper-small` | ~250MB | Yes | Balanced |
| `whisper-medium` | ~750MB | Yes | Slow |

### Transcription Options

```javascript
await whisper.transcribe(audioData, {
  language: null,        // Auto-detect (or 'en', 'fr', 'es', etc.)
  task: 'transcribe',    // or 'translate' (to English)
  chunk_length_s: 30,    // Process in 30s chunks
  stride_length_s: 5,    // Overlap between chunks
  return_timestamps: false
});
```

## Recording Audio

To get `Float32Array` audio at 16kHz:

```javascript
// Request microphone
const stream = await navigator.mediaDevices.getUserMedia({ 
  audio: { sampleRate: 16000, channelCount: 1 } 
});

// Create AudioContext
const audioCtx = new AudioContext({ sampleRate: 16000 });
const source = audioCtx.createMediaStreamSource(stream);

// Collect samples
const samples = [];
const processor = audioCtx.createScriptProcessor(4096, 1, 1);
processor.onaudioprocess = (e) => {
  samples.push(new Float32Array(e.inputBuffer.getChannelData(0)));
};
source.connect(processor);
processor.connect(audioCtx.destination);

// Later: merge samples
const merged = mergeFloat32Arrays(samples);
const result = await whisper.transcribe(merged);
```

## Integration Example

```javascript
// Lazy-load only when user clicks mic
let whisper = null;

async function onMicClick() {
  if (!whisper) {
    whisper = new WhisperTranscriber();
    await whisper.load('whisper-small', updateProgress);
  }
  startRecording();
}
```

## Browser Support

- Chrome 76+
- Firefox 78+
- Safari 14.1+
- Edge 79+

Requires:
- ES Modules
- Web Audio API
- IndexedDB (for caching)

## Memory Management

The model uses ~500MB-1GB RAM when loaded. Call `unload()` when done:

```javascript
// Free memory when not needed
await whisper.unload();
```

## Error Handling

```javascript
try {
  await whisper.load('whisper-small');
} catch (e) {
  if (e.message.includes('network')) {
    console.error('Network error - check connection');
  } else {
    console.error('Load failed:', e);
  }
}

try {
  const result = await whisper.transcribe(audioData);
} catch (e) {
  console.error('Transcription failed:', e);
}
```
