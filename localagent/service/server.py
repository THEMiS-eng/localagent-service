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
from fastapi.responses import HTMLResponse, FileResponse
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
    """Chat with Claude - uses chat_handler for logic."""
    from ..core.chat_handler import (
        detect_tracking_type, create_tracking_entry, mark_tracking_done,
        lint_message, build_conversation_context, handle_conversation,
        execute_negotiation, process_tasks
    )
    from ..core.constraints import validate_action, get_constraints_for_context
    
    message = data.get("message", "").strip()
    history = data.get("history", [])
    
    if not message:
        return {"error": "Empty message", "response": "Empty message"}
    
    # Auto-detect and create tracking
    tracking_type, title = detect_tracking_type(message)
    tracking_entry = None
    if tracking_type:
        tracking_entry = create_tracking_entry(tracking_type, title, message)
        invalidate(tracking_type.lower(), DEFAULT_PROJECT)
        logger.info(f"Created {tracking_entry['id']}")
    
    # Lint
    optimized, lint_report, is_conversation = lint_message(message, DEFAULT_PROJECT)
    
    # Handle simple conversation
    if is_conversation:
        context = build_conversation_context(history)
        response = handle_conversation(message, context, DEFAULT_PROJECT)
        return {"status": "ok", "response": response, "tracking": tracking_entry}
    
    # Validate constraints
    valid, violations = validate_action("chat", {"message": message})
    
    # Negotiate with Claude
    add_message(DEFAULT_PROJECT, "user", message)
    context = build_conversation_context(history)
    success, result = execute_negotiation(optimized, DEFAULT_PROJECT, context)
    
    # Process result
    if success:
        tasks = result.get("tasks", [])
        saved_files, attachments = process_tasks(tasks, DEFAULT_PROJECT)
        response = f"✅ {len(tasks)} tasks completed"
        if saved_files:
            response += f"\n📁 Files: {', '.join(saved_files)}"
        
        # Mark tracking as done
        if tracking_entry:
            mark_tracking_done(tracking_entry, tracking_type)
            invalidate(tracking_type.lower(), DEFAULT_PROJECT)
    else:
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
async def clear_outputs():
    """Clear output files."""
    output_dir = PROJECTS_DIR / DEFAULT_PROJECT / "current"
    if output_dir.exists():
        for f in output_dir.iterdir():
            if f.is_file():
                f.unlink()
    return {"cleared": True}

@app.get("/api/update/check")
async def check_update():
    """Check for updates."""
    from ..connectors.github import get_service_version
    github_version = get_service_version()
    return {"local": VERSION, "github": github_version, "update_available": github_version and github_version > VERSION}

@app.post("/api/update/install")
async def install_update(data: Dict[str, Any]):
    """Install update from GitHub."""
    from ..core.updater import install_update
    version = data.get("version")
    result = install_update(version)
    return result

# ============================================================
# RUN
# ============================================================
def run():
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")

if __name__ == "__main__":
    run()
