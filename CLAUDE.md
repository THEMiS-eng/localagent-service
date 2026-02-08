# CLAUDE.md — THEMiS-QS Project Rules

## Critical: Do NOT Regress These

### Drag-and-Drop on Center Pane (iframe area)
The center pane contains an iframe (`#localagent-chat`). Iframes are separate browsing contexts — drag events do NOT bubble to the parent. The fix uses a **two-layer defense**:

1. **Raw DOM disabling (index.html ~line 12883)** — `window.addEventListener('dragenter', enable, true)` fires in the CAPTURE phase (before children). It synchronously sets `pointer-events: none` on both the iframe AND `.chat-iframe-container` via raw DOM. This makes them transparent to events, so the `<section>` (pane-center) React `onDrop` handler catches the drop. A visual-only overlay (`dropLayerRef`, always `pointer-events: none`) shows "Drop files here" feedback.

2. **Iframe postMessage fallback (standalone.html ~line 1062)** — Early IIFE registers `document.drop` handler in THEMIS mode. If a drop reaches the iframe, it converts files to base64 and sends `parent.postMessage({ type: 'iframe-file-drop', files })`. Parent listens and adds to `attachedFiles`.

3. **CSS belt+suspenders (index.html ~line 152)** — `.pane-center.dragging-files .chat-iframe-container iframe { pointer-events: none }` via React state `isDragging`.

**NEVER change this to use React state alone for toggling pointer-events. React re-render is ASYNC and creates a race condition. The raw DOM manipulation in the capture-phase listener is what makes it work.**

### Rules
- **DO NOT** use `setState` to toggle `isDragging` as the primary mechanism — it's too slow
- **DO NOT** rely on an overlay div catching events over the iframe — overlays don't reliably intercept OS-level file drags over iframes
- **DO NOT** remove the capture-phase `window.dragenter` listener
- **DO NOT** remove the iframe `pointer-events: none` toggling in the `enable()` function
- **DO NOT** remove the iframe's own drop handler in standalone.html (postMessage fallback)

### File Attachment Preview (click-to-preview)
- **Attachment pills (index.html ~line 14236)**: Click opens fullscreen overlay with `<img>` for images, `<object>` for PDF, `<iframe>` for text
- **Conversation file cards (standalone.html ~line 2668)**: Click opens fullscreen preview overlay inside iframe
- Images use base64 data URLs (`f.preview`), NOT server URLs — everything works offline

### Evidence QuickLook Preview (PreviewModal)
- **Backend (themis.py ~line 441)**: `GET /api/evidence/{id}/quicklook` serves images/PDF/text natively, uses macOS `qlmanage` for everything else
- **Frontend (index.html ~line 9961)**: `<iframe>` for PDF/text, `<img>` for images/qlmanage thumbnails, fallback div on error

## Architecture Reminders
- **LOCAL APP** — NO cloud APIs, NO external services
- **Files are HUGE** — index.html=14.5K+ lines, standalone.html=2.7K+ lines. Always read specific sections.
- **Browser caches aggressively** — always tell user Cmd+Shift+R after changes
- **Embed mode hides inputs** — parent provides unified input, iframe hides its own via `body.themis-embed` rules
