/**
 * WhisperTranscriber.js
 * Standalone Whisper speech-to-text module
 * Server-first (native whisper-cpp) with browser WASM fallback
 * Browser-compatible IIFE bundle
 *
 * Usage:
 *   const whisper = new WhisperTranscriber({ serverUrl: 'http://localhost:9998/themis' });
 *   await whisper.load('whisper-small', (progress) => console.log(progress));
 *   const result = await whisper.transcribe(audioFloat32Array);
 *   console.log(result.text, result.language);
 */

(function(global) {
  'use strict';

  const MODELS = {
    'whisper-tiny': { size: '~40MB', multilingual: false, speed: 'fastest' },
    'whisper-tiny.en': { size: '~40MB', multilingual: false, speed: 'fastest' },
    'whisper-base': { size: '~75MB', multilingual: true, speed: 'fast' },
    'whisper-small': { size: '~250MB', multilingual: true, speed: 'balanced' },
    'whisper-medium': { size: '~750MB', multilingual: true, speed: 'slow' },
  };

  const DEFAULT_MODEL = 'whisper-small';
  const TRANSFORMERS_CDN = 'https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.1';

  class WhisperTranscriber {
    constructor(options) {
      this.serverUrl = (options && options.serverUrl) || null;
      this.serverAvailable = null;  // null = unknown, true/false = probed
      this.pipeline = null;
      this.model = null;
      this.loading = false;
      this.loaded = false;
    }

    /**
     * Get available models info
     */
    static getModels() {
      return MODELS;
    }

    /**
     * Check if model is loaded (server counts as loaded)
     */
    isLoaded() {
      return (this.loaded && (this.pipeline !== null || this.serverAvailable === true));
    }

    /**
     * Check if currently loading
     */
    isLoading() {
      return this.loading;
    }

    /**
     * Get current model name
     */
    getModel() {
      return this.model;
    }

    /**
     * Check if native whisper-cpp server is available
     */
    async checkServer() {
      if (!this.serverUrl) {
        this.serverAvailable = false;
        return false;
      }
      try {
        var r = await fetch(this.serverUrl + '/api/whisper/status');
        var d = await r.json();
        this.serverAvailable = d.available === true;
        if (this.serverAvailable) {
          console.log('✓ Native whisper-cpp available via server');
        }
      } catch(e) {
        this.serverAvailable = false;
        console.log('[Whisper] Server not reachable, will use browser WASM');
      }
      return this.serverAvailable;
    }

    /**
     * Convert Float32Array@16kHz to WAV blob for server upload
     */
    float32ToWav(samples) {
      var sampleRate = 16000;
      var numChannels = 1;
      var bitsPerSample = 16;
      var byteRate = sampleRate * numChannels * bitsPerSample / 8;
      var blockAlign = numChannels * bitsPerSample / 8;
      var dataSize = samples.length * blockAlign;
      var buffer = new ArrayBuffer(44 + dataSize);
      var view = new DataView(buffer);

      // WAV header
      writeString(view, 0, 'RIFF');
      view.setUint32(4, 36 + dataSize, true);
      writeString(view, 8, 'WAVE');
      writeString(view, 12, 'fmt ');
      view.setUint32(16, 16, true);           // fmt chunk size
      view.setUint16(20, 1, true);            // PCM format
      view.setUint16(22, numChannels, true);
      view.setUint32(24, sampleRate, true);
      view.setUint32(28, byteRate, true);
      view.setUint16(32, blockAlign, true);
      view.setUint16(34, bitsPerSample, true);
      writeString(view, 36, 'data');
      view.setUint32(40, dataSize, true);

      // Convert float32 [-1,1] to int16
      var offset = 44;
      for (var i = 0; i < samples.length; i++) {
        var s = Math.max(-1, Math.min(1, samples[i]));
        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        offset += 2;
      }

      return new Blob([buffer], { type: 'audio/wav' });

      function writeString(view, offset, str) {
        for (var i = 0; i < str.length; i++) {
          view.setUint8(offset + i, str.charCodeAt(i));
        }
      }
    }

    /**
     * Transcribe via native whisper-cpp server
     */
    async transcribeViaServer(audioData) {
      var wavBlob = this.float32ToWav(audioData);
      var formData = new FormData();
      formData.append('file', wavBlob, 'audio.wav');

      var startTime = performance.now();
      var r = await fetch(this.serverUrl + '/api/whisper/transcribe', {
        method: 'POST',
        body: formData
      });

      if (!r.ok) {
        var err = await r.json().catch(function() { return {}; });
        throw new Error(err.error || 'Server transcription failed (' + r.status + ')');
      }

      var data = await r.json();
      var duration = (performance.now() - startTime) / 1000;

      return {
        text: data.text || '',
        language: data.language || null,
        chunks: data.segments || null,
        duration: parseFloat(duration.toFixed(2)),
        audioLength: parseFloat((audioData.length / 16000).toFixed(2)),
        backend: 'whisper-cpp'
      };
    }

    /**
     * Load Whisper model — probes server first, falls back to browser WASM
     * @param {string} model - Model name (whisper-tiny, whisper-small, etc.)
     * @param {function} onProgress - Progress callback ({status, progress, file})
     * @returns {Promise<boolean>} - Success status
     */
    async load(model, onProgress) {
      model = model || DEFAULT_MODEL;

      if (this.loaded && this.model === model) {
        return true;
      }

      if (this.loading) {
        throw new Error('Model is already loading');
      }

      this.loading = true;

      try {
        // Probe server first — if native whisper-cpp is available, skip WASM entirely
        await this.checkServer();
        if (this.serverAvailable) {
          this.model = model.replace('Xenova/', '');
          this.loaded = true;
          this.loading = false;
          if (onProgress) {
            onProgress({ status: 'ready', progress: 100, file: null, loaded: 0, total: 0 });
          }
          console.log('✓ Using native whisper-cpp (server) — skipping browser WASM download');
          return true;
        }
      } catch(e) {
        console.log('[Whisper] Server probe failed, loading browser WASM...');
      }

      // Fall through to browser WASM pipeline
      var modelKey = model.replace('Xenova/', '');
      if (!MODELS[modelKey] && !model.startsWith('Xenova/')) {
        console.warn('Unknown model: ' + model + ', using ' + DEFAULT_MODEL);
        model = DEFAULT_MODEL;
      }

      this.model = modelKey;

      try {
        // Dynamic import of transformers.js
        var transformers = await import(TRANSFORMERS_CDN);
        var pipeline = transformers.pipeline;
        var env = transformers.env;

        // Configure environment
        env.allowLocalModels = false;
        env.useBrowserCache = true;

        // Build model path
        var modelPath = model.startsWith('Xenova/') ? model : 'Xenova/' + model;

        // Load pipeline with progress
        this.pipeline = await pipeline('automatic-speech-recognition', modelPath, {
          progress_callback: function(p) {
            if (onProgress && typeof onProgress === 'function') {
              onProgress({
                status: p.status || 'loading',
                progress: p.progress !== undefined ? Math.round(p.progress) : null,
                file: p.file || null,
                loaded: p.loaded || 0,
                total: p.total || 0
              });
            }
          }
        });

        this.loaded = true;
        this.loading = false;

        console.log('✓ Whisper model loaded (browser WASM): ' + modelPath);
        return true;

      } catch (error) {
        this.loading = false;
        this.loaded = false;
        this.pipeline = null;
        console.error('Whisper load error:', error);
        throw error;
      }
    }

    /**
     * Transcribe audio data — server-first, browser WASM fallback
     * @param {Float32Array} audioData - Audio samples at 16kHz mono
     * @param {object} options - Transcription options
     * @returns {Promise<{text: string, language: string, duration: number}>}
     */
    async transcribe(audioData, options) {
      if (!this.isLoaded()) {
        throw new Error('Model not loaded. Call load() first.');
      }

      if (!(audioData instanceof Float32Array)) {
        throw new Error('audioData must be a Float32Array');
      }

      if (audioData.length === 0) {
        return { text: '', language: null, duration: 0 };
      }

      // Try server first (native whisper-cpp — ~20x faster)
      if (this.serverAvailable) {
        try {
          return await this.transcribeViaServer(audioData);
        } catch(e) {
          console.warn('[Whisper] Server transcription failed, falling back to browser:', e.message);
          // Fall through to browser WASM
        }
      }

      // Browser WASM path
      if (!this.pipeline) {
        throw new Error('No transcription backend available. Server is down and browser model not loaded.');
      }

      options = options || {};
      var defaultOptions = {
        chunk_length_s: 30,
        stride_length_s: 5,
        return_timestamps: false,
        language: null,
        task: 'transcribe'
      };

      var mergedOptions = Object.assign({}, defaultOptions, options);
      var startTime = performance.now();

      try {
        var result = await this.pipeline(audioData, mergedOptions);
        var duration = (performance.now() - startTime) / 1000;

        return {
          text: (result && result.text) ? result.text.trim() : '',
          language: (result && result.language) ? result.language : null,
          chunks: (result && result.chunks) ? result.chunks : null,
          duration: parseFloat(duration.toFixed(2)),
          audioLength: parseFloat((audioData.length / 16000).toFixed(2)),
          backend: 'browser-wasm'
        };

      } catch (error) {
        console.error('Transcription error:', error);
        throw error;
      }
    }

    /**
     * Unload model to free memory
     */
    async unload() {
      if (this.pipeline) {
        this.pipeline = null;
        this.loaded = false;
        this.model = null;
        console.log('✓ Whisper model unloaded');
      }
    }
  }

  // Attach static properties
  WhisperTranscriber.MODELS = MODELS;
  WhisperTranscriber.DEFAULT_MODEL = DEFAULT_MODEL;

  // Export to global
  global.WhisperTranscriber = WhisperTranscriber;

})(typeof window !== 'undefined' ? window : (typeof global !== 'undefined' ? global : this));
