/**
 * WhisperTranscriber.js
 * Standalone Whisper speech-to-text module using transformers.js
 * Browser-compatible IIFE bundle
 * 
 * Usage:
 *   const whisper = new WhisperTranscriber();
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
    constructor() {
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
     * Check if model is loaded
     */
    isLoaded() {
      return this.loaded && this.pipeline !== null;
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
     * Load Whisper model
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

      const modelKey = model.replace('Xenova/', '');
      if (!MODELS[modelKey] && !model.startsWith('Xenova/')) {
        console.warn('Unknown model: ' + model + ', using ' + DEFAULT_MODEL);
        model = DEFAULT_MODEL;
      }

      this.loading = true;
      this.model = modelKey;

      try {
        // Dynamic import of transformers.js
        const transformers = await import(TRANSFORMERS_CDN);
        const pipeline = transformers.pipeline;
        const env = transformers.env;
        
        // Configure environment
        env.allowLocalModels = false;
        env.useBrowserCache = true;

        // Build model path
        const modelPath = model.startsWith('Xenova/') ? model : 'Xenova/' + model;

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
        
        console.log('✓ Whisper model loaded: ' + modelPath);
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
     * Transcribe audio data
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

      options = options || {};
      const defaultOptions = {
        chunk_length_s: 30,
        stride_length_s: 5,
        return_timestamps: false,
        language: null,  // Auto-detect
        task: 'transcribe'  // or 'translate' to translate to English
      };

      const mergedOptions = Object.assign({}, defaultOptions, options);
      const startTime = performance.now();

      try {
        const result = await this.pipeline(audioData, mergedOptions);
        const duration = (performance.now() - startTime) / 1000;

        return {
          text: (result && result.text) ? result.text.trim() : '',
          language: (result && result.language) ? result.language : null,
          chunks: (result && result.chunks) ? result.chunks : null,
          duration: parseFloat(duration.toFixed(2)),
          audioLength: parseFloat((audioData.length / 16000).toFixed(2))
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
