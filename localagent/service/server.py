#!/usr/bin/env python3
"""
LocalAgent v3 - HTTP API Server
Thin layer - all logic in core/, engine/, routers/
"""
import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn

# Config
HOST = os.environ.get("LOCALAGENT_HOST", "127.0.0.1")
PORT = int(os.environ.get("LOCALAGENT_PORT", 9998))
DEFAULT_PROJECT = "LOCALAGENT"
VERSION = Path(__file__).parent.parent.parent.joinpath("VERSION").read_text().strip() if Path(__file__).parent.parent.parent.joinpath("VERSION").exists() else "0.0.0"

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Imports
from ..engine.project import PROJECTS_DIR
from ..engine.cache import get_cache, invalidate, cached_get
from ..engine.tracking import get_todo, get_backlog, get_bugfixes, add_message, add_todo_item
from ..connectors.dashboard import set_project
from ..connectors.github import REPOS

_cache = get_cache()

# ============================================================
# WEBSOCKET MANAGER
# ============================================================
class WSManager:
    def __init__(self):
        self.connections: List[WebSocket] = []
    
    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)
    
    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)
    
    async def broadcast(self, data: dict):
        for ws in self.connections[:]:
            try:
                await ws.send_json(data)
            except:
                self.disconnect(ws)

ws_manager = WSManager()

# ============================================================
# APP SETUP
# ============================================================
@asynccontextmanager
async def lifespan(app):
    # Startup
    (PROJECTS_DIR / DEFAULT_PROJECT / "current").mkdir(parents=True, exist_ok=True)
    set_project(DEFAULT_PROJECT)
    logger.info(f"LocalAgent v{VERSION} on {HOST}:{PORT}")
    yield
    # Shutdown
    logger.info("Shutting down")

app = FastAPI(title="LocalAgent", version=VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ============================================================
# INCLUDE ROUTERS
# ============================================================
from .routers.themis import router as themis_router
from .routers import todo, bugfix, github, debug, releases, snapshots, modules, config, lint, learning, protocol, skills, llm

todo.set_cache(_cache)
bugfix.set_cache(_cache)
github.set_cache(_cache)
github.set_version_helper(lambda: VERSION)
debug.set_ws_manager(ws_manager)
debug.set_logger(logger)
releases.set_cache(_cache)


# Connectors
from ..connectors.dashboard_connector import router as dashboard_connector_router

app.include_router(todo.router)
app.include_router(bugfix.router)
app.include_router(github.router)
app.include_router(debug.router)
app.include_router(releases.router)
app.include_router(snapshots.router)
app.include_router(modules.router)
app.include_router(config.router)
app.include_router(lint.router)
app.include_router(learning.router)
app.include_router(protocol.router)
app.include_router(skills.router)
app.include_router(llm.router)

# Connectors
app.include_router(dashboard_connector_router)
app.include_router(themis_router)

# ============================================================
# STATIC FILES
# ============================================================
modules_dir = Path(__file__).parent.parent.parent / "modules"
if modules_dir.exists():
    app.mount("/modules", StaticFiles(directory=str(modules_dir)), name="modules")

dashboard_file = Path(__file__).parent.parent.parent / "dashboard" / "index.html"

@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    if dashboard_file.exists():
        return HTMLResponse(dashboard_file.read_text())
    return HTMLResponse("<h1>Dashboard not found</h1>")

@app.get("/chat-pro-standalone.html", response_class=HTMLResponse)
@app.get("/modules/ai-chat-module-pro/chat-pro-standalone.html", response_class=HTMLResponse)
async def serve_chat_module():
    """Serve chat module from external prompt-linter module."""
    import urllib.request
    
    # 1. Check local installed module
    local_paths = [
        Path.home() / ".localagent" / "modules" / "prompt-linter" / "chat-module" / "chat-pro-standalone.html",
        Path.home() / "localagent-modular" / "prompt-linter" / "chat-module" / "chat-pro-standalone.html",
    ]
    for p in local_paths:
        if p.exists():
            return HTMLResponse(p.read_text())
    
    # 2. Fetch from GitHub module
    try:
        url = "https://raw.githubusercontent.com/THEMiS-eng/prompt-linter/main/chat-module/chat-pro-standalone.html"
        with urllib.request.urlopen(url, timeout=10) as resp:
            return HTMLResponse(resp.read().decode('utf-8'))
    except:
        pass
    
    return HTMLResponse("<h1>Chat Module Not Found</h1><p>Install prompt-linter module</p>")

@app.get("/modules/ai-chat-module-pro/PromptLinter.bundle.js")
async def serve_prompt_linter():
    """Serve PromptLinter from prompt-linter module."""
    local_paths = [
        Path.home() / ".localagent" / "modules" / "prompt-linter" / "dist" / "PromptLinter.bundle.js",
        Path.home() / "localagent-modular" / "prompt-linter" / "dist" / "PromptLinter.bundle.js",
    ]
    for p in local_paths:
        if p.exists():
            return Response(content=p.read_text(), media_type="application/javascript")
    
    # Fetch from GitHub
    try:
        import urllib.request
        url = "https://raw.githubusercontent.com/THEMiS-eng/prompt-linter/main/dist/PromptLinter.bundle.js"
        with urllib.request.urlopen(url, timeout=10) as resp:
            return Response(content=resp.read().decode('utf-8'), media_type="application/javascript")
    except:
        pass
    
    return Response(content="// PromptLinter not found", media_type="application/javascript")

@app.get("/modules/whisper-module/WhisperTranscriber.js")
async def serve_whisper():
    """Serve WhisperTranscriber from whisper-module."""
    local_paths = [
        Path.home() / ".localagent" / "modules" / "whisper-module" / "src" / "WhisperTranscriber.js",
        Path.home() / "localagent-modular" / "whisper-module" / "src" / "WhisperTranscriber.js",
    ]
    for p in local_paths:
        if p.exists():
            return Response(content=p.read_text(), media_type="application/javascript")
    
    # Fetch from GitHub
    try:
        import urllib.request
        url = "https://raw.githubusercontent.com/THEMiS-eng/whisper-module/main/src/WhisperTranscriber.js"
        with urllib.request.urlopen(url, timeout=10) as resp:
            return Response(content=resp.read().decode('utf-8'), media_type="application/javascript")
    except:
        pass
    
    return Response(content="// WhisperTranscriber not found", media_type="application/javascript")

@app.get("/outputs/{filename:path}")
async def serve_output(filename: str):
    filepath = PROJECTS_DIR / DEFAULT_PROJECT / "current" / filename
    if not filepath.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(filepath)

# ============================================================
# CORE ENDPOINTS
# ============================================================
@app.get("/api/health")
async def health():
    """Health check with version comparison."""
    from ..connectors.github import get_service_version
    github_version = get_service_version()
    return {
        "status": "ok",
        "version": VERSION,
        "github_version": github_version,
        "project": DEFAULT_PROJECT,
        "project_version": VERSION,
        "github_repos": REPOS,
        "api_key": bool(os.environ.get("ANTHROPIC_API_KEY"))
    }

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            data = await ws.receive_json()
            await ws_manager.broadcast({"type": "echo", "data": data})
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)

@app.post("/api/chat")
async def chat_endpoint(data: Dict[str, Any]):
    """Chat with Claude - uses chat_handler for logic, supports multimodal."""
    from ..core.chat_handler import (
        detect_tracking_type, create_tracking_entry, mark_tracking_done,
        lint_message, build_conversation_context, handle_conversation,
        execute_negotiation, process_tasks
    )
    from ..core.constraints import validate_action, get_constraints_for_context
    from ..connectors.llm import call_claude

    message = data.get("message", "").strip()
    history = data.get("history", [])

    # Extract attachments for multimodal support
    attachments = data.get("attachments", [])
    images = []
    doc_texts = []

    for att in attachments:
        att_data = att.get("data", "")
        att_type = att.get("type", "")
        att_name = att.get("name", "file")

        if att_data and att_type.startswith("image/"):
            images.append({
                "data": att_data,
                "type": att_type,
                "name": att_name
            })
        elif att_data:
            # Handle document files (docx, pdf, txt, etc.)
            try:
                import base64
                import io

                # Remove data URL prefix if present
                if "," in att_data:
                    att_data = att_data.split(",", 1)[1]

                file_bytes = base64.b64decode(att_data)

                if att_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or att_name.endswith(".docx"):
                    # Extract text from DOCX
                    try:
                        from docx import Document
                        doc = Document(io.BytesIO(file_bytes))
                        text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
                        if text:
                            doc_texts.append(f"=== Content of {att_name} ===\n{text}\n=== End of {att_name} ===")
                            logger.info(f"Extracted {len(text)} chars from DOCX: {att_name}")
                    except Exception as e:
                        logger.error(f"Failed to extract DOCX: {e}")
                        doc_texts.append(f"[Could not extract text from {att_name}: {e}]")

                elif att_type == "application/pdf" or att_name.endswith(".pdf"):
                    # Extract text from PDF
                    try:
                        import pdfplumber
                        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                            text = "\n".join([page.extract_text() or "" for page in pdf.pages])
                        if text:
                            doc_texts.append(f"=== Content of {att_name} ===\n{text}\n=== End of {att_name} ===")
                            logger.info(f"Extracted {len(text)} chars from PDF: {att_name}")
                    except Exception as e:
                        logger.error(f"Failed to extract PDF: {e}")
                        doc_texts.append(f"[Could not extract text from {att_name}: {e}]")

                elif att_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" or att_name.endswith(".xlsx"):
                    # Extract text from XLSX
                    try:
                        import openpyxl
                        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
                        sheets_text = []
                        for ws in wb.worksheets:
                            rows = []
                            for row in ws.iter_rows(values_only=True):
                                cells = [str(c) if c is not None else "" for c in row]
                                if any(cells):
                                    rows.append("\t".join(cells))
                            if rows:
                                sheets_text.append(f"--- Sheet: {ws.title} ---\n" + "\n".join(rows))
                        wb.close()
                        text = "\n\n".join(sheets_text)
                        if text:
                            doc_texts.append(f"=== Content of {att_name} ===\n{text}\n=== End of {att_name} ===")
                            logger.info(f"Extracted {len(text)} chars from XLSX: {att_name}")
                    except ImportError:
                        doc_texts.append(f"[XLSX extraction requires openpyxl - file stored: {att_name}]")
                    except Exception as e:
                        logger.error(f"Failed to extract XLSX: {e}")
                        doc_texts.append(f"[Could not extract text from {att_name}: {e}]")

                elif att_name.lower().endswith(".eml"):
                    # Extract text from EML (stdlib - no external deps)
                    try:
                        import email
                        from email import policy
                        msg = email.message_from_bytes(file_bytes, policy=policy.default)
                        parts = []
                        parts.append(f"From: {msg.get('From', '')}")
                        parts.append(f"To: {msg.get('To', '')}")
                        parts.append(f"Date: {msg.get('Date', '')}")
                        parts.append(f"Subject: {msg.get('Subject', '')}")
                        parts.append("---")
                        body = msg.get_body(preferencelist=('plain', 'html'))
                        if body:
                            content = body.get_content()
                            if body.get_content_type() == 'text/html':
                                import re
                                content = re.sub(r'<[^>]+>', ' ', content)
                                content = re.sub(r'\s+', ' ', content).strip()
                            parts.append(content)
                        text = "\n".join(parts)
                        if text:
                            doc_texts.append(f"=== Content of {att_name} ===\n{text}\n=== End of {att_name} ===")
                            logger.info(f"Extracted {len(text)} chars from EML: {att_name}")
                    except Exception as e:
                        logger.error(f"Failed to extract EML: {e}")
                        doc_texts.append(f"[Could not extract text from {att_name}: {e}]")

                elif att_name.lower().endswith(".msg"):
                    # Extract text from Outlook MSG
                    try:
                        import extract_msg
                        msg = extract_msg.Message(io.BytesIO(file_bytes))
                        parts = []
                        parts.append(f"From: {msg.sender or ''}")
                        parts.append(f"To: {msg.to or ''}")
                        parts.append(f"Date: {msg.date or ''}")
                        parts.append(f"Subject: {msg.subject or ''}")
                        parts.append("---")
                        if msg.body:
                            parts.append(msg.body)
                        msg.close()
                        text = "\n".join(parts)
                        if text:
                            doc_texts.append(f"=== Content of {att_name} ===\n{text}\n=== End of {att_name} ===")
                            logger.info(f"Extracted {len(text)} chars from MSG: {att_name}")
                    except ImportError:
                        doc_texts.append(f"[MSG extraction requires extract-msg - file stored: {att_name}]")
                    except Exception as e:
                        logger.error(f"Failed to extract MSG: {e}")
                        doc_texts.append(f"[Could not extract text from {att_name}: {e}]")

                elif att_name.lower().endswith(".xer"):
                    # Parse Primavera P6 XER (pipe-delimited text format)
                    try:
                        raw = file_bytes.decode("utf-8", errors="ignore")
                        lines = raw.split("\n")
                        sections = []
                        current_table = None
                        current_fields = []
                        current_rows = []
                        for line in lines:
                            line = line.rstrip("\r")
                            if line.startswith("%T\t"):
                                if current_table and current_rows:
                                    sections.append(f"--- {current_table} ({len(current_rows)} rows) ---")
                                    for row in current_rows[:20]:
                                        sections.append(row)
                                    if len(current_rows) > 20:
                                        sections.append(f"  ... and {len(current_rows) - 20} more rows")
                                current_table = line.split("\t", 1)[1] if "\t" in line else line[3:]
                                current_fields = []
                                current_rows = []
                            elif line.startswith("%F\t"):
                                current_fields = line.split("\t")[1:]
                            elif line.startswith("%R\t"):
                                vals = line.split("\t")[1:]
                                if current_fields:
                                    row = ", ".join(f"{k}={v}" for k, v in zip(current_fields, vals) if v.strip())
                                else:
                                    row = "\t".join(vals)
                                current_rows.append(f"  {row}")
                        if current_table and current_rows:
                            sections.append(f"--- {current_table} ({len(current_rows)} rows) ---")
                            for row in current_rows[:20]:
                                sections.append(row)
                        text = "\n".join(sections)
                        if text:
                            doc_texts.append(f"=== Content of {att_name} (P6 XER) ===\n{text}\n=== End of {att_name} ===")
                            logger.info(f"Extracted {len(text)} chars from XER: {att_name}")
                    except Exception as e:
                        logger.error(f"Failed to parse XER: {e}")
                        doc_texts.append(f"[Could not parse XER file {att_name}: {e}]")

                elif att_name.lower().endswith((".mpp", ".dwg", ".pst", ".ost")):
                    # Binary formats without local parsers - store and note
                    ext = att_name.rsplit(".", 1)[-1].upper()
                    doc_texts.append(f"[Attached {ext} file: {att_name} — binary format stored as evidence, text extraction not available locally]")
                    logger.info(f"Stored binary file without extraction: {att_name} ({ext})")

                elif att_type.startswith("text/") or att_name.endswith((".txt", ".md", ".json", ".csv")):
                    # Plain text files
                    text = file_bytes.decode("utf-8", errors="ignore")
                    if text:
                        doc_texts.append(f"=== Content of {att_name} ===\n{text}\n=== End of {att_name} ===")
                        logger.info(f"Read {len(text)} chars from text file: {att_name}")

            except Exception as e:
                logger.error(f"Failed to process attachment {att_name}: {e}")

    # If documents attached, include their content in the message
    if doc_texts:
        doc_context = "\n\n".join(doc_texts)
        message = f"{message}\n\n[ATTACHED DOCUMENTS]\n{doc_context}" if message else f"Please analyze these documents:\n\n{doc_context}"
        logger.info(f"Added {len(doc_texts)} document(s) to context")

    # If images attached, use direct multimodal call (run in thread to avoid blocking event loop)
    if images:
        logger.info(f"Multimodal chat with {len(images)} image(s)")
        result = await asyncio.to_thread(
            call_claude,
            message or "Describe what you see in this image.",
            "",
            "You are a helpful assistant. Analyze images carefully and describe what you see.",
            images
        )
        return {
            "status": "ok" if result.get("success") else "error",
            "response": result.get("response", result.get("error", "Error")),
            "detail": result.get("detail", ""),
            "ai_source": "claude",
            "images_received": len(images),
            "protocol": [
                {"step": "context", "label": f"📎 {len(images)} image(s)", "status": "complete"},
                {"step": "complete", "label": "🤖 CLAUDE (multimodal)", "status": "complete"}
            ]
        }

    if not message:
        return {"error": "Empty message", "response": "Empty message"}

    # Documents attached or chat message → direct Claude call (single call, fast)
    # Only use negotiation for explicit file-creation commands (rare)
    if doc_texts or not message.lower().startswith(("create file ", "generate file ")):
        context = build_conversation_context(history)
        response = await asyncio.to_thread(handle_conversation, message, context, DEFAULT_PROJECT)
        return {"status": "ok", "response": response, "tracking": None}

    # Explicit file creation requests → negotiation path
    tracking_type, title = detect_tracking_type(message)
    tracking_entry = None
    if tracking_type:
        tracking_entry = create_tracking_entry(tracking_type, title, message)
        invalidate(tracking_type.lower(), DEFAULT_PROJECT)

    optimized, lint_report, _ = lint_message(message, DEFAULT_PROJECT)
    valid, violations = validate_action("chat", {"message": message})

    add_message(DEFAULT_PROJECT, "user", message)
    context = build_conversation_context(history)
    success, result = await asyncio.to_thread(execute_negotiation, optimized, DEFAULT_PROJECT, context)

    if success:
        tasks = result.get("tasks", [])
        saved_files, attachments = process_tasks(tasks, DEFAULT_PROJECT)
        response = f"✅ {len(tasks)} tasks completed"
        if saved_files:
            response += f"\n📁 Files: {', '.join(saved_files)}"
        if tracking_entry:
            mark_tracking_done(tracking_entry, tracking_type)
            invalidate(tracking_type.lower(), DEFAULT_PROJECT)
    else:
        # Negotiation failed — fallback to conversation
        raw_response = result.get("raw_response", "")
        if raw_response:
            response = raw_response
        else:
            try:
                response = await asyncio.to_thread(handle_conversation, message, context, DEFAULT_PROJECT)
            except Exception:
                response = f"❌ Failed: {result.get('error', 'unknown')}"
        attachments = []

    add_message(DEFAULT_PROJECT, "agent", response)
    return {"status": "ok" if success else "error", "response": response, "files": attachments, "tracking": tracking_entry}

@app.post("/api/claude/complete")
async def claude_complete(data: Dict[str, Any]):
    """Direct Claude completion."""
    from ..connectors.llm import call_claude
    prompt = data.get("prompt", "")
    system = data.get("system", "")
    if not prompt:
        raise HTTPException(400, "No prompt")
    result = call_claude(prompt, system)
    return result

@app.get("/api/outputs")
async def get_outputs():
    """Get output files."""
    from ..engine.tracking import get_output_files
    return get_output_files(DEFAULT_PROJECT)

@app.get("/api/conversation")
async def get_conversation():
    """Get conversation history."""
    from ..engine.tracking import get_conversation
    return {"messages": get_conversation(DEFAULT_PROJECT)}

@app.get("/api/errors")
async def get_errors():
    """Get pending errors."""
    from ..core.debugger import get_pending_errors
    return {"errors": get_pending_errors()}

@app.post("/api/clear")
async def clear_outputs(data: Dict[str, Any] = None):
    """Clear output files. Requires confirmation."""
    data = data or {}

    # SECURITY: Require explicit confirmation to prevent accidental deletion
    if data.get("confirm") != True:
        return {"error": "Confirmation required. Send {\"confirm\": true} to proceed.", "cleared": False}

    output_dir = PROJECTS_DIR / DEFAULT_PROJECT / "current"
    deleted_files = []

    if output_dir.exists():
        for f in output_dir.iterdir():
            if f.is_file():
                deleted_files.append(f.name)
                f.unlink()

    logger.warning(f"Cleared {len(deleted_files)} files from {output_dir}")
    return {"cleared": True, "files_deleted": len(deleted_files), "files": deleted_files}

@app.get("/api/update/check")
async def check_update():
    """Check for updates."""
    from ..connectors.github import get_service_version
    github_version = get_service_version()
    return {"local": VERSION, "github": github_version, "update_available": github_version and github_version > VERSION}

@app.post("/api/update/install")
async def install_update_endpoint(data: Dict[str, Any]):
    """Install update from GitHub."""
    from ..core.updater import install_from_github
    download_url = data.get("download_url")
    result = install_from_github(download_url)
    return result

# ============================================================
# AUTO-FIX & ANALYZE (called by debug router)
# ============================================================
async def auto_fix_error(error_id: str):
    """Auto-fix an error using Claude."""
    from ..core.debugger import get_pending_errors
    from ..connectors.llm import call_claude
    
    errors = get_pending_errors()
    error = next((e for e in errors if e.get("id") == error_id), None)
    
    if not error:
        return {"success": False, "error": f"Error {error_id} not found"}
    
    prompt = f"""Fix this error:
Message: {error.get('message', '')}
Source: {error.get('source', '')}
Stack: {error.get('stack', '')[:500]}

Provide a brief fix description and code if applicable."""
    
    result = call_claude(prompt, "You are a debugging assistant. Provide concise fixes.")
    
    if result.get("success"):
        return {
            "success": True,
            "error_id": error_id,
            "fix_suggestion": result.get("response", "")
        }
    return {"success": False, "error": "Claude call failed"}


async def analyze_error_with_claude(error_id: str):
    """Analyze an error using Claude."""
    from ..core.debugger import get_pending_errors
    from ..connectors.llm import call_claude
    
    errors = get_pending_errors()
    error = next((e for e in errors if e.get("id") == error_id), None)
    
    if not error:
        return {"success": False, "error": f"Error {error_id} not found"}
    
    prompt = f"""Analyze this error:
Message: {error.get('message', '')}
Source: {error.get('source', '')}
File: {error.get('file', '')}
Line: {error.get('line', '')}
Stack: {error.get('stack', '')[:500]}

Provide:
1. Root cause analysis
2. Severity (low/medium/high/critical)
3. Recommended fix"""
    
    result = call_claude(prompt, "You are a senior debugger. Analyze errors precisely.")
    
    if result.get("success"):
        return {
            "success": True,
            "error_id": error_id,
            "analysis": result.get("response", "")
        }
    return {"success": False, "error": "Analysis failed"}

# ============================================================
# RUN
# ============================================================
def run():
    uvicorn.run(app, host=HOST, port=PORT, log_level="info", timeout_keep_alive=300)

if __name__ == "__main__":
    run()
