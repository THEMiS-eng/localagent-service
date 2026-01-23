import React, { useState, useRef, useEffect, useCallback, useMemo, forwardRef, useImperativeHandle } from 'react';

/**
 * AIChatModulePro - Enterprise-grade AI Discussion Component
 * 
 * EXTENSIVE FEATURES:
 * 
 * 1. AUTO-RESIZING INPUT - Grows with content, configurable min/max
 * 2. PROCESSING STATUS - Multi-step progress with timing
 * 3. THINKING BLOCKS - Collapsible reasoning visualization
 * 4. TOOL CALLS - Input/output visualization for AI tools
 * 5. AUTO-FILE CREATION - Creates downloadable file when response exceeds threshold
 * 6. FILE HANDLING - Drag & drop, validation, preview
 * 7. STREAMING - Real-time content with cursor animation
 * 8. CODE BLOCKS - Syntax highlighting with copy
 * 9. THEMING - Full CSS variable customization
 */

const DEFAULT_CONFIG = {
  title: 'AI Assistant',
  subtitle: null,
  placeholder: 'Message AI...',
  emptyStateTitle: 'Start a conversation',
  emptyStateSubtitle: 'Ask anything or upload files to analyze',
  minInputHeight: 44,
  maxInputHeight: 300,
  submitOnEnter: true,
  autoFileEnabled: true,
  autoFileThreshold: 4000,
  autoFileFormat: 'md',
  autoFileName: 'response',
  enableFileUpload: true,
  maxFileSize: 100 * 1024 * 1024,
  maxFiles: 10,
  allowedFileTypes: null,
  showProcessingSteps: true,
  showThinkingBlocks: true,
  showToolCalls: true,
  thinkingBlocksCollapsed: true,
  enableMessageEdit: true,
  enableMessageRetry: true,
  enableMessageCopy: true,
  enableCodeCopy: true,
  autoScrollThreshold: 150,
  showScrollToBottom: true,
  theme: 'dark',
};

const THEMES = {
  dark: {
    '--chat-bg': '#09090b',
    '--chat-bg-secondary': '#0f0f12',
    '--chat-surface': '#18181b',
    '--chat-surface-hover': '#1f1f23',
    '--chat-surface-active': '#27272a',
    '--chat-border': '#27272a',
    '--chat-border-subtle': '#1f1f23',
    '--chat-text': '#fafafa',
    '--chat-text-secondary': '#a1a1aa',
    '--chat-text-muted': '#71717a',
    '--chat-accent': '#6366f1',
    '--chat-accent-hover': '#818cf8',
    '--chat-accent-muted': 'rgba(99, 102, 241, 0.15)',
    '--chat-user-bg': '#1e1b4b',
    '--chat-user-border': '#312e81',
    '--chat-assistant-bg': '#18181b',
    '--chat-assistant-border': '#27272a',
    '--chat-success': '#22c55e',
    '--chat-success-muted': 'rgba(34, 197, 94, 0.15)',
    '--chat-warning': '#f59e0b',
    '--chat-warning-muted': 'rgba(245, 158, 11, 0.15)',
    '--chat-error': '#ef4444',
    '--chat-error-muted': 'rgba(239, 68, 68, 0.15)',
    '--chat-thinking-bg': '#1a1a2e',
    '--chat-thinking-border': '#2d2d5a',
    '--chat-tool-bg': '#0c1a1a',
    '--chat-tool-border': '#1a3a3a',
    '--chat-code-bg': '#0d0d0f',
    '--chat-code-border': '#1f1f23',
    '--chat-scrollbar': '#3f3f46',
    '--chat-radius': '10px',
    '--chat-radius-lg': '14px',
    '--chat-radius-sm': '6px',
    '--chat-font': "'Geist', -apple-system, sans-serif",
    '--chat-font-mono': "'Geist Mono', 'Fira Code', monospace",
    '--chat-transition': '0.15s cubic-bezier(0.4, 0, 0.2, 1)',
  },
  light: {
    '--chat-bg': '#ffffff',
    '--chat-bg-secondary': '#f9fafb',
    '--chat-surface': '#f3f4f6',
    '--chat-surface-hover': '#e5e7eb',
    '--chat-surface-active': '#d1d5db',
    '--chat-border': '#e5e7eb',
    '--chat-border-subtle': '#f3f4f6',
    '--chat-text': '#111827',
    '--chat-text-secondary': '#4b5563',
    '--chat-text-muted': '#6b7280',
    '--chat-accent': '#4f46e5',
    '--chat-accent-hover': '#6366f1',
    '--chat-accent-muted': 'rgba(79, 70, 229, 0.1)',
    '--chat-user-bg': '#eef2ff',
    '--chat-user-border': '#c7d2fe',
    '--chat-assistant-bg': '#f9fafb',
    '--chat-assistant-border': '#e5e7eb',
    '--chat-success': '#16a34a',
    '--chat-success-muted': 'rgba(22, 163, 74, 0.1)',
    '--chat-warning': '#d97706',
    '--chat-warning-muted': 'rgba(217, 119, 6, 0.1)',
    '--chat-error': '#dc2626',
    '--chat-error-muted': 'rgba(220, 38, 38, 0.1)',
    '--chat-thinking-bg': '#f5f3ff',
    '--chat-thinking-border': '#ddd6fe',
    '--chat-tool-bg': '#ecfdf5',
    '--chat-tool-border': '#a7f3d0',
    '--chat-code-bg': '#f8fafc',
    '--chat-code-border': '#e2e8f0',
    '--chat-scrollbar': '#d1d5db',
    '--chat-radius': '10px',
    '--chat-radius-lg': '14px',
    '--chat-radius-sm': '6px',
    '--chat-font': "'Geist', -apple-system, sans-serif",
    '--chat-font-mono': "'Geist Mono', 'Fira Code', monospace",
    '--chat-transition': '0.15s cubic-bezier(0.4, 0, 0.2, 1)',
  },
};

// Icons
const Icons = {
  Send: () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>,
  Stop: () => <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>,
  Paperclip: () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg>,
  X: () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6L6 18M6 6l12 12"/></svg>,
  Download: () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>,
  File: () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/></svg>,
  FileCode: () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6"/><path d="M10 12l-2 2 2 2M14 12l2 2-2 2"/></svg>,
  Zip: () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6"/><rect x="10" y="12" width="4" height="6" rx="1"/><path d="M12 12v-2M12 8v-2"/></svg>,
  Image: () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>,
  Copy: () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>,
  Check: () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6L9 17l-5-5"/></svg>,
  ChevronRight: () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18l6-6-6-6"/></svg>,
  Retry: () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 4v6h6M23 20v-6h-6"/><path d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15"/></svg>,
  Edit: () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>,
  Brain: () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9.5 2A2.5 2.5 0 0112 4.5v15a2.5 2.5 0 01-4.96.44 2.5 2.5 0 01-2.96-3.08 3 3 0 01-.34-5.58 2.5 2.5 0 011.32-4.24 2.5 2.5 0 011.98-3A2.5 2.5 0 019.5 2z"/><path d="M14.5 2A2.5 2.5 0 0012 4.5v15a2.5 2.5 0 004.96.44 2.5 2.5 0 002.96-3.08 3 3 0 00.34-5.58 2.5 2.5 0 00-1.32-4.24 2.5 2.5 0 00-1.98-3A2.5 2.5 0 0014.5 2z"/></svg>,
  Tool: () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/></svg>,
  Search: () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>,
  Globe: () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/></svg>,
  Code: () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="16,18 22,12 16,6"/><polyline points="8,6 2,12 8,18"/></svg>,
  ArrowDown: () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 5v14M19 12l-7 7-7-7"/></svg>,
  Sparkles: () => <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3l1.912 5.813a2 2 0 001.275 1.275L21 12l-5.813 1.912a2 2 0 00-1.275 1.275L12 21l-1.912-5.813a2 2 0 00-1.275-1.275L3 12l5.813-1.912a2 2 0 001.275-1.275L12 3z"/></svg>,
  Clock: () => <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>,
  AlertCircle: () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>,
  CheckCircle: () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>,
  Loader: () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="chat-spin"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>,
  Sun: () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>,
  Moon: () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg>,
};

// Utilities
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

const formatDuration = (ms) => {
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  return `${m}m ${(s % 60).toFixed(0)}s`;
};

const generateId = () => Math.random().toString(36).substring(2, 11);

const createDownloadableFile = (content, filename, type = 'text/plain') => {
  const blob = new Blob([content], { type });
  return { name: filename, size: blob.size, type, url: URL.createObjectURL(blob), blob };
};

const getFileIcon = (file) => {
  const type = file.type || '';
  const name = file.name || '';
  if (name.match(/\.(zip|tar|gz|rar|7z)$/i) || type.includes('zip')) return <Icons.Zip />;
  if (type.startsWith('image/')) return <Icons.Image />;
  if (name.match(/\.(js|ts|jsx|tsx|py|rb|go|rs|java|c|cpp|css|html|json|yaml|md|sql|sh)$/i)) return <Icons.FileCode />;
  return <Icons.File />;
};

// Processing Step Component
const ProcessingStep = ({ step, isActive, isComplete }) => {
  const [elapsed, setElapsed] = useState(0);
  
  useEffect(() => {
    if (!isActive || isComplete) return;
    const start = Date.now();
    const interval = setInterval(() => setElapsed(Date.now() - start), 100);
    return () => clearInterval(interval);
  }, [isActive, isComplete]);

  return (
    <div className={`chat-step ${isActive ? 'active' : ''} ${isComplete ? 'complete' : ''}`}>
      <div className="chat-step-icon">
        {isComplete ? <Icons.CheckCircle /> : isActive ? <Icons.Loader /> : <div className="chat-step-dot" />}
      </div>
      <div className="chat-step-content">
        <span className="chat-step-label">{step.label}</span>
        {step.detail && <span className="chat-step-detail">{step.detail}</span>}
      </div>
      {(isActive || isComplete) && (
        <span className="chat-step-time"><Icons.Clock /> {formatDuration(isComplete ? step.duration : elapsed)}</span>
      )}
    </div>
  );
};

// Thinking Block Component
const ThinkingBlock = ({ content, duration, collapsed: init = true }) => {
  const [collapsed, setCollapsed] = useState(init);
  
  return (
    <div className="chat-thinking">
      <button className="chat-thinking-header" onClick={() => setCollapsed(!collapsed)}>
        <Icons.Brain />
        <span>Thinking</span>
        {duration && <span className="chat-thinking-time"><Icons.Clock /> {formatDuration(duration)}</span>}
        <div className={`chat-chevron ${collapsed ? '' : 'open'}`}><Icons.ChevronRight /></div>
      </button>
      {!collapsed && <div className="chat-thinking-content"><pre>{content}</pre></div>}
    </div>
  );
};

// Tool Call Component
const ToolCall = ({ tool, collapsed: init = true }) => {
  const [collapsed, setCollapsed] = useState(init);
  
  const getIcon = () => {
    switch (tool.type) {
      case 'web_search': return <Icons.Search />;
      case 'web_fetch': return <Icons.Globe />;
      case 'code_execution': return <Icons.Code />;
      default: return <Icons.Tool />;
    }
  };

  return (
    <div className={`chat-tool ${tool.status}`}>
      <button className="chat-tool-header" onClick={() => setCollapsed(!collapsed)}>
        <div className="chat-tool-icon">{getIcon()}</div>
        <span className="chat-tool-name">{tool.name || tool.type}</span>
        {tool.status === 'running' && <Icons.Loader />}
        {tool.status === 'complete' && <Icons.CheckCircle />}
        {tool.status === 'error' && <Icons.AlertCircle />}
        {tool.duration && <span className="chat-tool-time">{formatDuration(tool.duration)}</span>}
        <div className={`chat-chevron ${collapsed ? '' : 'open'}`}><Icons.ChevronRight /></div>
      </button>
      {!collapsed && (
        <div className="chat-tool-content">
          {tool.input && (
            <div className="chat-tool-section">
              <label>Input</label>
              <pre>{typeof tool.input === 'string' ? tool.input : JSON.stringify(tool.input, null, 2)}</pre>
            </div>
          )}
          {tool.output && (
            <div className="chat-tool-section">
              <label>Output</label>
              <pre>{typeof tool.output === 'string' ? tool.output : JSON.stringify(tool.output, null, 2)}</pre>
            </div>
          )}
          {tool.error && (
            <div className="chat-tool-section error">
              <label>Error</label>
              <pre>{tool.error}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Code Block Component
const CodeBlock = ({ code, language, filename }) => {
  const [copied, setCopied] = useState(false);
  
  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="chat-code">
      <div className="chat-code-header">
        <span>{filename || language || 'code'}</span>
        <button onClick={handleCopy}>{copied ? <><Icons.Check /> Copied</> : <><Icons.Copy /> Copy</>}</button>
      </div>
      <pre><code>{code}</code></pre>
    </div>
  );
};

// Auto Generated File Component
const AutoGeneratedFile = ({ file, preview }) => {
  const handleDownload = () => {
    const a = document.createElement('a');
    a.href = file.url;
    a.download = file.name;
    a.click();
  };

  return (
    <div className="chat-autofile">
      <div className="chat-autofile-header">
        <Icons.FileCode />
        <div className="chat-autofile-info">
          <span className="chat-autofile-name">{file.name}</span>
          <span className="chat-autofile-size">{formatFileSize(file.size)}</span>
        </div>
        <button onClick={handleDownload}><Icons.Download /> Download</button>
      </div>
      {preview && (
        <div className="chat-autofile-preview">
          <pre>{preview}</pre>
          <div className="chat-autofile-fade" />
        </div>
      )}
    </div>
  );
};

// File Attachment Component
const FileAttachment = ({ file, onRemove, onDownload }) => {
  const [imageUrl, setImageUrl] = useState(null);
  
  useEffect(() => {
    if (file.type?.startsWith('image/') && file instanceof Blob) {
      const url = URL.createObjectURL(file);
      setImageUrl(url);
      return () => URL.revokeObjectURL(url);
    } else if (file.preview || file.url) {
      setImageUrl(file.preview || file.url);
    }
  }, [file]);

  return (
    <div className="chat-file">
      {imageUrl && file.type?.startsWith('image/') ? (
        <img src={imageUrl} alt={file.name} className="chat-file-img" />
      ) : (
        <div className="chat-file-icon">{getFileIcon(file)}</div>
      )}
      <div className="chat-file-info">
        <span className="chat-file-name" title={file.name}>{file.name}</span>
        <span className="chat-file-size">{formatFileSize(file.size)}</span>
      </div>
      {onRemove && <button className="chat-file-btn remove" onClick={() => onRemove(file)}><Icons.X /></button>}
      {onDownload && <button className="chat-file-btn download" onClick={() => onDownload(file)}><Icons.Download /></button>}
    </div>
  );
};

// Message Component
const Message = ({ message, config, onFileDownload, onRetry, onEdit, isStreaming }) => {
  const [copied, setCopied] = useState(false);
  const [showActions, setShowActions] = useState(false);
  const isUser = message.role === 'user';
  const isError = message.status === 'error';
  
  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content || '');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const renderContent = (content) => {
    if (!content) return null;
    const parts = [];
    let remaining = content;
    let key = 0;
    
    const codeBlockRegex = /```(\w+)?\n?([\s\S]*?)```/g;
    let lastIndex = 0;
    let match;
    
    while ((match = codeBlockRegex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        parts.push(<span key={key++}>{renderInline(content.slice(lastIndex, match.index))}</span>);
      }
      parts.push(<CodeBlock key={key++} code={match[2].trim()} language={match[1]} />);
      lastIndex = match.index + match[0].length;
    }
    
    if (lastIndex < content.length) {
      parts.push(<span key={key++}>{renderInline(content.slice(lastIndex))}</span>);
    }
    return parts;
  };

  const renderInline = (text) => {
    return text.split(/(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g).map((seg, i) => {
      if (seg.startsWith('`') && seg.endsWith('`')) return <code key={i} className="chat-inline-code">{seg.slice(1, -1)}</code>;
      if (seg.startsWith('**') && seg.endsWith('**')) return <strong key={i}>{seg.slice(2, -2)}</strong>;
      if (seg.startsWith('*') && seg.endsWith('*')) return <em key={i}>{seg.slice(1, -1)}</em>;
      return seg;
    });
  };

  return (
    <div 
      className={`chat-msg ${isUser ? 'user' : 'assistant'} ${isError ? 'error' : ''} ${isStreaming ? 'streaming' : ''}`}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {message.processingSteps?.length > 0 && config.showProcessingSteps && (
        <div className="chat-steps">
          {message.processingSteps.map((step, i) => (
            <ProcessingStep key={i} step={step} isActive={step.status === 'running'} isComplete={step.status === 'complete'} />
          ))}
        </div>
      )}

      {message.thinking && config.showThinkingBlocks && (
        <ThinkingBlock content={message.thinking.content} duration={message.thinking.duration} collapsed={config.thinkingBlocksCollapsed} />
      )}

      {message.toolCalls?.length > 0 && config.showToolCalls && (
        <div className="chat-tools">{message.toolCalls.map((tool, i) => <ToolCall key={i} tool={tool} />)}</div>
      )}

      <div className="chat-bubble">
        <div className="chat-content">
          {renderContent(message.content)}
          {isStreaming && <span className="chat-cursor" />}
        </div>

        {message.autoFile && <AutoGeneratedFile file={message.autoFile} preview={message.autoFilePreview} />}

        {message.files?.length > 0 && (
          <div className="chat-files">{message.files.map((f, i) => <FileAttachment key={i} file={f} onDownload={onFileDownload} />)}</div>
        )}

        {isError && message.error && <div className="chat-error-msg"><Icons.AlertCircle /> <span>{message.error}</span></div>}

        <div className="chat-meta">
          {message.timestamp && <span className="chat-time">{new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>}
          {message.model && <span className="chat-model">{message.model}</span>}
        </div>
      </div>

      {showActions && !isStreaming && (
        <div className="chat-actions">
          {config.enableMessageCopy && <button onClick={handleCopy} title="Copy">{copied ? <Icons.Check /> : <Icons.Copy />}</button>}
          {isUser && config.enableMessageEdit && onEdit && <button onClick={() => onEdit(message)} title="Edit"><Icons.Edit /></button>}
          {isError && config.enableMessageRetry && onRetry && <button onClick={() => onRetry(message)} title="Retry"><Icons.Retry /></button>}
        </div>
      )}
    </div>
  );
};

// Empty State
const EmptyState = ({ config }) => (
  <div className="chat-empty">
    <div className="chat-empty-icon"><Icons.Sparkles /></div>
    <h3>{config.emptyStateTitle}</h3>
    <p>{config.emptyStateSubtitle}</p>
  </div>
);

// Main Component
const AIChatModulePro = forwardRef(({ 
  onSendMessage, 
  onStopGeneration,
  initialMessages = [], 
  config: userConfig = {},
  onFileDownload,
  className = '',
}, ref) => {
  const config = useMemo(() => ({ ...DEFAULT_CONFIG, ...userConfig }), [userConfig]);
  
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState('');
  const [files, setFiles] = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState(null);
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const [currentTheme, setCurrentTheme] = useState(config.theme);

  const containerRef = useRef(null);
  const messagesRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const abortRef = useRef(null);

  useImperativeHandle(ref, () => ({
    addMessage: (msg) => setMessages(prev => [...prev, { ...msg, id: generateId(), timestamp: new Date() }]),
    clearMessages: () => setMessages([]),
    setInput: (t) => setInput(t),
    focus: () => textareaRef.current?.focus(),
    scrollToBottom: () => scrollToBottom(),
    getMessages: () => messages,
  }));

  // Apply theme
  useEffect(() => {
    if (containerRef.current) {
      const theme = typeof currentTheme === 'object' ? currentTheme : THEMES[currentTheme] || THEMES.dark;
      Object.entries(theme).forEach(([k, v]) => containerRef.current.style.setProperty(k, v));
    }
  }, [currentTheme]);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = 'auto';
      ta.style.height = `${Math.min(Math.max(ta.scrollHeight, config.minInputHeight), config.maxInputHeight)}px`;
    }
  }, [input, config.minInputHeight, config.maxInputHeight]);

  const scrollToBottom = useCallback((behavior = 'smooth') => {
    messagesRef.current?.scrollTo({ top: messagesRef.current.scrollHeight, behavior });
  }, []);

  useEffect(() => {
    const el = messagesRef.current;
    if (!el) return;
    const handleScroll = () => {
      setShowScrollBtn(el.scrollHeight - el.scrollTop - el.clientHeight > config.autoScrollThreshold);
    };
    el.addEventListener('scroll', handleScroll);
    return () => el.removeEventListener('scroll', handleScroll);
  }, [config.autoScrollThreshold]);

  useEffect(() => {
    if (!showScrollBtn) scrollToBottom('auto');
  }, [messages, showScrollBtn, scrollToBottom]);

  const validateFile = useCallback((file) => {
    if (file.size > config.maxFileSize) return `"${file.name}" exceeds ${formatFileSize(config.maxFileSize)}`;
    if (config.allowedFileTypes) {
      const allowed = config.allowedFileTypes.some(t => t.endsWith('/*') ? file.type.startsWith(t.slice(0, -1)) : file.type === t);
      if (!allowed) return `"${file.name}" type not allowed`;
    }
    return null;
  }, [config.maxFileSize, config.allowedFileTypes]);

  const handleFiles = useCallback((newFiles) => {
    const arr = Array.from(newFiles);
    const errors = [];
    const valid = [];
    arr.forEach(f => {
      if (files.length + valid.length >= config.maxFiles) { errors.push(`Max ${config.maxFiles} files`); return; }
      const err = validateFile(f);
      if (err) errors.push(err);
      else valid.push(f);
    });
    if (errors.length) { setError(errors.join('\n')); setTimeout(() => setError(null), 5000); }
    setFiles(prev => [...prev, ...valid]);
  }, [files.length, config.maxFiles, validateFile]);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    onStopGeneration?.();
    setIsGenerating(false);
  }, [onStopGeneration]);

  const handleSend = useCallback(async () => {
    if ((!input.trim() && files.length === 0) || isGenerating) return;

    const userMsg = { id: generateId(), role: 'user', content: input.trim(), files: files.length ? [...files] : undefined, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setFiles([]);
    setError(null);
    setIsGenerating(true);

    const assistantId = generateId();
    const assistantMsg = { id: assistantId, role: 'assistant', content: '', timestamp: new Date(), processingSteps: [], toolCalls: [] };
    setMessages(prev => [...prev, assistantMsg]);

    abortRef.current = new AbortController();

    try {
      const response = await onSendMessage(userMsg.content, userMsg.files, {
        signal: abortRef.current.signal,
        onProcessingStep: (step) => setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, processingSteps: [...(m.processingSteps || []), step] } : m)),
        onProcessingStepUpdate: (idx, upd) => setMessages(prev => prev.map(m => {
          if (m.id !== assistantId) return m;
          const steps = [...(m.processingSteps || [])];
          steps[idx] = { ...steps[idx], ...upd };
          return { ...m, processingSteps: steps };
        })),
        onThinking: (thinking) => setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, thinking } : m)),
        onToolCall: (tool) => setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, toolCalls: [...(m.toolCalls || []), tool] } : m)),
        onToolCallUpdate: (idx, upd) => setMessages(prev => prev.map(m => {
          if (m.id !== assistantId) return m;
          const tools = [...(m.toolCalls || [])];
          tools[idx] = { ...tools[idx], ...upd };
          return { ...m, toolCalls: tools };
        })),
        onContent: (content) => setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content } : m)),
        onContentDelta: (delta) => setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content: (m.content || '') + delta } : m)),
      });

      let finalContent = '';
      let finalFiles = null;
      let model = null;

      if (typeof response === 'string') {
        finalContent = response;
      } else if (response?.[Symbol.asyncIterator]) {
        for await (const chunk of response) {
          if (typeof chunk === 'string') finalContent += chunk;
          else if (chunk.content) finalContent += chunk.content;
          setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content: finalContent } : m));
        }
      } else if (response) {
        finalContent = response.content || '';
        finalFiles = response.files;
        model = response.model;
      }

      let autoFile = null;
      let autoFilePreview = null;
      if (config.autoFileEnabled && finalContent.length > config.autoFileThreshold) {
        const ext = config.autoFileFormat;
        autoFile = createDownloadableFile(finalContent, `${config.autoFileName}-${Date.now()}.${ext}`);
        autoFilePreview = finalContent.slice(0, 500) + (finalContent.length > 500 ? '...' : '');
        finalContent = finalContent.slice(0, 1000) + `\n\n*[Response truncated. Full content saved to file below.]*`;
      }

      setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content: finalContent, files: finalFiles, model, autoFile, autoFilePreview } : m));
    } catch (err) {
      if (err.name === 'AbortError') {
        setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content: m.content + '\n\n*[Generation stopped]*' } : m));
      } else {
        setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, status: 'error', error: err.message || 'Failed' } : m));
      }
    } finally {
      setIsGenerating(false);
      abortRef.current = null;
    }
  }, [input, files, isGenerating, onSendMessage, config]);

  const handleKeyDown = useCallback((e) => {
    if (config.submitOnEnter ? (e.key === 'Enter' && !e.shiftKey) : (e.key === 'Enter' && (e.ctrlKey || e.metaKey))) {
      e.preventDefault();
      handleSend();
    }
  }, [config.submitOnEnter, handleSend]);

  const handleFileDownload = useCallback((file) => {
    if (onFileDownload) return onFileDownload(file);
    const url = file.url || (file instanceof Blob ? URL.createObjectURL(file) : null);
    if (url) {
      const a = document.createElement('a');
      a.href = url;
      a.download = file.name;
      a.click();
      if (file instanceof Blob && !file.url) URL.revokeObjectURL(url);
    }
  }, [onFileDownload]);

  const handleRetry = useCallback((msg) => {
    const idx = messages.findIndex(m => m.id === msg.id);
    if (idx > 0 && messages[idx - 1].role === 'user') {
      const userMsg = messages[idx - 1];
      setMessages(prev => prev.slice(0, idx - 1));
      setInput(userMsg.content || '');
      if (userMsg.files) setFiles(userMsg.files);
    }
  }, [messages]);

  const handleEdit = useCallback((msg) => {
    const idx = messages.findIndex(m => m.id === msg.id);
    if (idx >= 0) {
      setMessages(prev => prev.slice(0, idx));
      setInput(msg.content || '');
      if (msg.files) setFiles(msg.files);
    }
  }, [messages]);

  return (
    <div ref={containerRef} className={`chat-module ${className}`}
      onDragEnter={(e) => { e.preventDefault(); if (config.enableFileUpload) setIsDragging(true); }}
      onDragLeave={(e) => { e.preventDefault(); if (!e.currentTarget.contains(e.relatedTarget)) setIsDragging(false); }}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => { e.preventDefault(); setIsDragging(false); if (config.enableFileUpload && e.dataTransfer.files.length) handleFiles(e.dataTransfer.files); }}
    >
      <style>{STYLES}</style>

      <div className="chat-header">
        <div className="chat-header-left">
          <h2>{config.title}</h2>
          {config.subtitle && <span>{config.subtitle}</span>}
        </div>
        <button className="chat-theme-btn" onClick={() => setCurrentTheme(p => p === 'dark' ? 'light' : 'dark')}>
          {currentTheme === 'dark' ? <Icons.Sun /> : <Icons.Moon />}
        </button>
      </div>

      <div className="chat-messages" ref={messagesRef}>
        {messages.length === 0 ? <EmptyState config={config} /> : messages.map((msg, i) => (
          <Message key={msg.id || i} message={msg} config={config} onFileDownload={handleFileDownload} onRetry={handleRetry} onEdit={handleEdit} isStreaming={isGenerating && i === messages.length - 1 && msg.role === 'assistant'} />
        ))}
      </div>

      {showScrollBtn && config.showScrollToBottom && (
        <button className="chat-scroll-btn" onClick={() => scrollToBottom()}><Icons.ArrowDown /></button>
      )}

      <div className="chat-input-area">
        {error && <div className="chat-error"><Icons.AlertCircle /> <span>{error}</span> <button onClick={() => setError(null)}><Icons.X /></button></div>}
        {files.length > 0 && <div className="chat-input-files">{files.map((f, i) => <FileAttachment key={i} file={f} onRemove={(file) => setFiles(prev => prev.filter(x => x !== file))} />)}</div>}
        <div className="chat-input-row">
          <div className="chat-input-wrapper">
            {config.enableFileUpload && <button className="chat-attach-btn" onClick={() => fileInputRef.current?.click()}><Icons.Paperclip /></button>}
            <textarea ref={textareaRef} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown} placeholder={config.placeholder} rows={1} disabled={isGenerating} />
          </div>
          {isGenerating ? (
            <button className="chat-send-btn stop" onClick={handleStop}><Icons.Stop /></button>
          ) : (
            <button className="chat-send-btn" onClick={handleSend} disabled={!input.trim() && files.length === 0}><Icons.Send /></button>
          )}
        </div>
        <input ref={fileInputRef} type="file" multiple style={{ display: 'none' }} onChange={(e) => { if (e.target.files) { handleFiles(e.target.files); e.target.value = ''; } }} />
      </div>

      {isDragging && <div className="chat-drop"><Icons.Paperclip /> <span>Drop files here</span></div>}
    </div>
  );
});

AIChatModulePro.displayName = 'AIChatModulePro';

const STYLES = `
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500&display=swap');

.chat-module { display:flex; flex-direction:column; height:100%; min-height:400px; background:var(--chat-bg); font-family:var(--chat-font); color:var(--chat-text); position:relative; overflow:hidden; }
.chat-module * { box-sizing:border-box; }

.chat-header { display:flex; align-items:center; justify-content:space-between; padding:16px 20px; background:var(--chat-surface); border-bottom:1px solid var(--chat-border); flex-shrink:0; }
.chat-header-left { display:flex; flex-direction:column; gap:2px; }
.chat-header h2 { font-size:16px; font-weight:600; margin:0; letter-spacing:-0.02em; }
.chat-header span { font-size:12px; color:var(--chat-text-muted); }
.chat-theme-btn { background:none; border:none; color:var(--chat-text-muted); cursor:pointer; padding:8px; border-radius:var(--chat-radius-sm); display:flex; }
.chat-theme-btn:hover { color:var(--chat-text); background:var(--chat-surface-hover); }

.chat-messages { flex:1; overflow-y:auto; padding:24px 20px; display:flex; flex-direction:column; gap:24px; }
.chat-messages::-webkit-scrollbar { width:8px; }
.chat-messages::-webkit-scrollbar-track { background:transparent; }
.chat-messages::-webkit-scrollbar-thumb { background:var(--chat-scrollbar); border-radius:4px; }

.chat-empty { flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; padding:40px 20px; }
.chat-empty-icon { width:64px; height:64px; background:var(--chat-accent-muted); border-radius:var(--chat-radius-lg); display:flex; align-items:center; justify-content:center; color:var(--chat-accent); margin-bottom:16px; }
.chat-empty h3 { font-size:18px; font-weight:600; margin:0 0 8px; }
.chat-empty p { font-size:14px; color:var(--chat-text-muted); margin:0; max-width:300px; }

.chat-msg { display:flex; flex-direction:column; gap:12px; max-width:85%; position:relative; animation:msgIn 0.25s ease-out; }
@keyframes msgIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
.chat-msg.user { align-self:flex-end; align-items:flex-end; }
.chat-msg.assistant { align-self:flex-start; align-items:flex-start; }

.chat-bubble { padding:14px 18px; border-radius:var(--chat-radius-lg); line-height:1.6; font-size:14px; max-width:100%; }
.chat-msg.user .chat-bubble { background:var(--chat-user-bg); border:1px solid var(--chat-user-border); border-bottom-right-radius:var(--chat-radius-sm); }
.chat-msg.assistant .chat-bubble { background:var(--chat-assistant-bg); border:1px solid var(--chat-assistant-border); border-bottom-left-radius:var(--chat-radius-sm); }
.chat-msg.error .chat-bubble { border-color:var(--chat-error); background:var(--chat-error-muted); }

.chat-content { white-space:pre-wrap; word-break:break-word; }
.chat-content strong { font-weight:600; }
.chat-content em { font-style:italic; }

.chat-cursor { display:inline-block; width:2px; height:1.2em; background:var(--chat-accent); margin-left:2px; animation:blink 1s step-end infinite; vertical-align:text-bottom; }
@keyframes blink { 50% { opacity:0; } }

.chat-inline-code { background:var(--chat-code-bg); border:1px solid var(--chat-code-border); padding:2px 6px; border-radius:4px; font-family:var(--chat-font-mono); font-size:13px; }

.chat-code { margin:12px 0; border-radius:var(--chat-radius); overflow:hidden; background:var(--chat-code-bg); border:1px solid var(--chat-code-border); }
.chat-code-header { display:flex; align-items:center; justify-content:space-between; padding:8px 14px; background:var(--chat-surface); border-bottom:1px solid var(--chat-code-border); }
.chat-code-header span { font-size:11px; font-weight:500; color:var(--chat-text-muted); text-transform:uppercase; letter-spacing:0.05em; }
.chat-code-header button { display:flex; align-items:center; gap:4px; background:none; border:none; color:var(--chat-text-muted); font-size:11px; cursor:pointer; padding:4px 8px; border-radius:4px; }
.chat-code-header button:hover { color:var(--chat-text); background:var(--chat-surface-hover); }
.chat-code pre { padding:14px; margin:0; overflow-x:auto; font-family:var(--chat-font-mono); font-size:13px; line-height:1.5; }

.chat-steps { display:flex; flex-direction:column; gap:6px; padding:12px 14px; background:var(--chat-surface); border:1px solid var(--chat-border); border-radius:var(--chat-radius); }
.chat-step { display:flex; align-items:center; gap:10px; padding:6px 0; font-size:13px; }
.chat-step-icon { display:flex; color:var(--chat-text-muted); }
.chat-step.active .chat-step-icon { color:var(--chat-accent); }
.chat-step.complete .chat-step-icon { color:var(--chat-success); }
.chat-step-dot { width:14px; height:14px; border-radius:50%; border:2px solid var(--chat-border); }
.chat-step-content { flex:1; display:flex; flex-direction:column; gap:2px; }
.chat-step-label { font-weight:500; color:var(--chat-text-secondary); }
.chat-step.active .chat-step-label, .chat-step.complete .chat-step-label { color:var(--chat-text); }
.chat-step-detail { font-size:12px; color:var(--chat-text-muted); }
.chat-step-time { display:flex; align-items:center; gap:4px; font-size:11px; color:var(--chat-text-muted); font-family:var(--chat-font-mono); }

.chat-thinking { background:var(--chat-thinking-bg); border:1px solid var(--chat-thinking-border); border-radius:var(--chat-radius); overflow:hidden; }
.chat-thinking-header { display:flex; align-items:center; gap:8px; width:100%; padding:10px 14px; background:none; border:none; color:var(--chat-text); cursor:pointer; font-size:13px; text-align:left; }
.chat-thinking-header:hover { background:var(--chat-surface-hover); }
.chat-thinking-header svg:first-child { color:var(--chat-accent); }
.chat-thinking-header span:first-of-type { font-weight:500; flex:1; }
.chat-thinking-time { display:flex; align-items:center; gap:4px; font-size:11px; color:var(--chat-text-muted); font-family:var(--chat-font-mono); }
.chat-chevron { color:var(--chat-text-muted); transition:transform var(--chat-transition); }
.chat-chevron.open { transform:rotate(90deg); }
.chat-thinking-content { padding:0 14px 14px; border-top:1px solid var(--chat-thinking-border); }
.chat-thinking-content pre { margin:12px 0 0; font-family:var(--chat-font-mono); font-size:12px; line-height:1.6; color:var(--chat-text-secondary); white-space:pre-wrap; word-break:break-word; }

.chat-tools { display:flex; flex-direction:column; gap:8px; }
.chat-tool { background:var(--chat-tool-bg); border:1px solid var(--chat-tool-border); border-radius:var(--chat-radius); overflow:hidden; }
.chat-tool.error { border-color:var(--chat-error); }
.chat-tool-header { display:flex; align-items:center; gap:8px; width:100%; padding:10px 14px; background:none; border:none; color:var(--chat-text); cursor:pointer; font-size:13px; text-align:left; }
.chat-tool-header:hover { background:var(--chat-surface-hover); }
.chat-tool-icon { display:flex; color:var(--chat-success); }
.chat-tool.error .chat-tool-icon { color:var(--chat-error); }
.chat-tool-name { font-weight:500; flex:1; }
.chat-tool-time { font-size:11px; color:var(--chat-text-muted); font-family:var(--chat-font-mono); }
.chat-tool-content { padding:0 14px 14px; border-top:1px solid var(--chat-tool-border); }
.chat-tool-section { margin-top:12px; }
.chat-tool-section.error pre { color:var(--chat-error); }
.chat-tool-section label { display:block; font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:0.05em; color:var(--chat-text-muted); margin-bottom:6px; }
.chat-tool-content pre { margin:0; padding:10px; background:var(--chat-bg); border-radius:var(--chat-radius-sm); font-family:var(--chat-font-mono); font-size:11px; line-height:1.5; overflow-x:auto; white-space:pre-wrap; word-break:break-all; }

.chat-autofile { margin-top:16px; background:var(--chat-surface); border:1px solid var(--chat-border); border-radius:var(--chat-radius); overflow:hidden; }
.chat-autofile-header { display:flex; align-items:center; gap:12px; padding:12px 14px; border-bottom:1px solid var(--chat-border); }
.chat-autofile-header svg:first-child { color:var(--chat-accent); }
.chat-autofile-info { flex:1; display:flex; flex-direction:column; gap:2px; }
.chat-autofile-name { font-weight:500; font-size:13px; }
.chat-autofile-size { font-size:11px; color:var(--chat-text-muted); }
.chat-autofile-header button { display:flex; align-items:center; gap:6px; padding:8px 14px; background:var(--chat-accent); border:none; border-radius:var(--chat-radius-sm); color:white; font-size:12px; font-weight:500; cursor:pointer; }
.chat-autofile-header button:hover { background:var(--chat-accent-hover); }
.chat-autofile-preview { position:relative; max-height:200px; overflow:hidden; }
.chat-autofile-preview pre { margin:0; padding:14px; font-family:var(--chat-font-mono); font-size:12px; line-height:1.5; white-space:pre-wrap; word-break:break-word; color:var(--chat-text-secondary); }
.chat-autofile-fade { position:absolute; bottom:0; left:0; right:0; height:60px; background:linear-gradient(transparent, var(--chat-surface)); pointer-events:none; }

.chat-files { display:flex; flex-wrap:wrap; gap:8px; margin-top:12px; }
.chat-file { display:flex; align-items:center; gap:10px; padding:10px 12px; background:var(--chat-surface); border:1px solid var(--chat-border); border-radius:var(--chat-radius); max-width:240px; }
.chat-file-icon { flex-shrink:0; color:var(--chat-accent); }
.chat-file-img { width:44px; height:44px; object-fit:cover; border-radius:var(--chat-radius-sm); flex-shrink:0; }
.chat-file-info { flex:1; min-width:0; display:flex; flex-direction:column; gap:2px; }
.chat-file-name { font-size:13px; font-weight:500; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.chat-file-size { font-size:11px; color:var(--chat-text-muted); }
.chat-file-btn { flex-shrink:0; background:none; border:none; color:var(--chat-text-muted); cursor:pointer; padding:6px; border-radius:var(--chat-radius-sm); display:flex; }
.chat-file-btn.remove:hover { color:var(--chat-error); background:var(--chat-error-muted); }
.chat-file-btn.download:hover { color:var(--chat-accent); background:var(--chat-accent-muted); }

.chat-error-msg { display:flex; align-items:center; gap:8px; margin-top:12px; padding:10px 12px; background:var(--chat-error-muted); border-radius:var(--chat-radius-sm); color:var(--chat-error); font-size:13px; }

.chat-meta { display:flex; align-items:center; gap:10px; margin-top:8px; font-size:11px; color:var(--chat-text-muted); }
.chat-model { padding:2px 6px; background:var(--chat-surface); border-radius:4px; font-family:var(--chat-font-mono); }

.chat-actions { position:absolute; top:0; right:0; display:flex; gap:4px; padding:4px; background:var(--chat-surface); border:1px solid var(--chat-border); border-radius:var(--chat-radius-sm); box-shadow:0 4px 12px rgba(0,0,0,0.2); transform:translateY(-50%); animation:actionsIn 0.15s ease-out; }
.chat-msg.user .chat-actions { right:auto; left:0; }
@keyframes actionsIn { from { opacity:0; transform:translateY(-50%) scale(0.95); } to { opacity:1; transform:translateY(-50%) scale(1); } }
.chat-actions button { background:none; border:none; color:var(--chat-text-muted); cursor:pointer; padding:6px; border-radius:4px; display:flex; }
.chat-actions button:hover { color:var(--chat-text); background:var(--chat-surface-hover); }

.chat-scroll-btn { position:absolute; bottom:100px; right:20px; width:40px; height:40px; background:var(--chat-surface); border:1px solid var(--chat-border); border-radius:50%; display:flex; align-items:center; justify-content:center; color:var(--chat-text); cursor:pointer; box-shadow:0 4px 12px rgba(0,0,0,0.2); z-index:10; }
.chat-scroll-btn:hover { background:var(--chat-surface-hover); transform:translateY(-2px); }

.chat-input-area { padding:16px 20px; background:var(--chat-bg-secondary); border-top:1px solid var(--chat-border); flex-shrink:0; }
.chat-error { display:flex; align-items:center; gap:10px; padding:12px 14px; background:var(--chat-error-muted); border:1px solid var(--chat-error); border-radius:var(--chat-radius); color:var(--chat-error); font-size:13px; margin-bottom:12px; animation:msgIn 0.2s ease-out; }
.chat-error span { flex:1; }
.chat-error button { background:none; border:none; color:var(--chat-error); cursor:pointer; padding:4px; display:flex; }

.chat-input-files { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:12px; }
.chat-input-row { display:flex; align-items:flex-end; gap:12px; }
.chat-input-wrapper { flex:1; display:flex; align-items:flex-end; gap:8px; background:var(--chat-surface); border:1px solid var(--chat-border); border-radius:var(--chat-radius-lg); padding:8px 12px; transition:all var(--chat-transition); }
.chat-input-wrapper:focus-within { border-color:var(--chat-accent); box-shadow:0 0 0 3px var(--chat-accent-muted); }
.chat-attach-btn { flex-shrink:0; background:none; border:none; color:var(--chat-text-muted); cursor:pointer; padding:8px; border-radius:var(--chat-radius-sm); display:flex; }
.chat-attach-btn:hover { color:var(--chat-accent); background:var(--chat-accent-muted); }
.chat-input-wrapper textarea { flex:1; background:none; border:none; color:var(--chat-text); font-family:var(--chat-font); font-size:14px; line-height:1.5; resize:none; outline:none; min-height:24px; max-height:300px; padding:4px 0; }
.chat-input-wrapper textarea::placeholder { color:var(--chat-text-muted); }
.chat-input-wrapper textarea:disabled { opacity:0.6; }

.chat-send-btn { flex-shrink:0; width:44px; height:44px; background:var(--chat-accent); border:none; border-radius:var(--chat-radius); display:flex; align-items:center; justify-content:center; color:white; cursor:pointer; transition:all var(--chat-transition); }
.chat-send-btn:hover:not(:disabled) { background:var(--chat-accent-hover); transform:scale(1.02); }
.chat-send-btn:disabled { opacity:0.5; cursor:not-allowed; }
.chat-send-btn.stop { background:var(--chat-error); }
.chat-send-btn.stop:hover { filter:brightness(1.1); }

.chat-drop { position:absolute; inset:0; background:rgba(99, 102, 241, 0.1); border:2px dashed var(--chat-accent); border-radius:inherit; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:12px; color:var(--chat-accent); font-size:16px; font-weight:500; z-index:100; animation:dropIn 0.2s ease-out; }
@keyframes dropIn { from { opacity:0; } to { opacity:1; } }

.chat-spin { animation:spin 1s linear infinite; }
@keyframes spin { from { transform:rotate(0deg); } to { transform:rotate(360deg); } }

@media (max-width:640px) {
  .chat-msg { max-width:95%; }
  .chat-messages { padding:16px 12px; }
  .chat-input-area { padding:12px; }
  .chat-header { padding:12px 16px; }
}
`;

export default AIChatModulePro;
export { DEFAULT_CONFIG, THEMES, formatFileSize, formatDuration, generateId, createDownloadableFile };
