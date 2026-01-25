#!/usr/bin/env python3
"""
LocalAgent v3.0 - Service Worker Server
HTTP API on localhost:9998

Architecture:
- This is a THIN HTTP layer
- ALL operations go through core/orchestrator.py
- Orchestrator handles: snapshots, learning, constraints, git

Endpoints:
- /api/health
- /api/claude/complete -> orchestrator.call_llm()
- /api/github/* -> orchestrator.github_*()
- /api/deploy/release -> release_publisher.create_release()
- /api/learning/* -> core/learning.py
- /api/constraints -> core/constraints.py
- /api/update/* -> core/release_listener.py
- /api/debug/* -> core/debugger.py
- /api/apps/* -> app registration
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# ============================================================
# INTERNAL IMPORTS - All LocalAgent modules
# ============================================================

from ..engine.project import (
    PROJECTS_DIR, 
    get_version as get_project_version,
    list_snapshots,
    create_snapshot,
    rollback as restore_snapshot,
    init_project,
    list_projects,
    project_exists,
)
from ..engine.tracking import (
    get_conversation, get_backlog, get_todo, get_changelog,
    get_output_files, get_outputs_path,
    add_message, add_backlog_item, add_todo_item,
    toggle_todo, save_todo, save_backlog, save_bugfixes,
    complete_backlog_item,
    get_bugfixes, get_pending_bugfixes, add_bugfix,
)
from ..connectors.dashboard import (
    get_status as dash_status, 
    set_project,
)
from ..connectors.github import (
    get_service_version,
    get_dashboard_version,
    REPOS,
    fetch_github_version,
    github_push as push_to_github,
    github_create_release as create_github_release,
    github_list_releases,
    get_repos,
    _get_token,
    _load_config as get_repo_config,
    _save_config as save_repo_config,
    github_repo_exists,
    github_delete_release,
    github_clone,
    github_sync,
)
from ..connectors.llm import call_claude
from ..core.constraints import (
    get_all_constraints,
    get_constraints_for_context,
    get_constraint,
    validate_action,
    build_system_prompt,
)
from ..core.negotiator import negotiate_request, validate_response
from ..core.learning import (
    load_learned_errors,
    learn_from_error,
    has_learned_solution,
    get_error_context_for_retry,
)
from ..core.protocol import PROTOCOL_STEPS, ProtocolExecutor, ProtocolExecution
from ..core.debugger import (
    log_error,
    get_pending_errors as get_errors,
    mark_error_fixed,
    format_errors_for_claude,
    learn_from_fix,
    get_learned_fix,
    set_github_issue,
    set_claude_analysis,
    auto_fix_error,
    create_github_issue_for_error,
    analyze_error_with_claude,
    get_error_context_for_claude,
    get_debug_stats,
)
from ..roadmap.prompt_optimizer import lint_prompt, preprocess_for_negotiation

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("localagent")


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def set_repo_url(url: str):
    """Set temporary repo URL in config."""
    config = get_repo_config()
    # Parse owner/repo from URL
    if "github.com/" in url:
        parts = url.split("github.com/")[-1].strip("/").split("/")
        if len(parts) >= 2:
            config["owner_repo"] = f"{parts[0]}/{parts[1]}"
            config["url"] = url
    save_repo_config(config)


def list_releases(limit: int = 10) -> list:
    """List releases from configured repo."""
    return github_list_releases(limit=limit)

# ============================================================
# WEBSOCKET CONNECTION MANAGER
# ============================================================

class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_personal(self, websocket: WebSocket, message: dict):
        await websocket.send_json(message)

ws_manager = ConnectionManager()

# ============================================================
# PATHS & CONFIG
# ============================================================

SERVICE_DIR = Path.home() / ".localagent"
CONFIG_DIR = SERVICE_DIR / "config"
APPS_DIR = SERVICE_DIR / "apps"

HOST = os.environ.get("LOCALAGENT_HOST", "127.0.0.1")
PORT = int(os.environ.get("LOCALAGENT_PORT", "9998"))

# Read version from VERSION file
def _read_version() -> str:
    """Read version from VERSION file."""
    version_paths = [
        SERVICE_DIR / "VERSION",
        SERVICE_DIR.parent / "VERSION",
        Path(__file__).parent.parent.parent / "VERSION",
    ]
    for vp in version_paths:
        if vp.exists():
            return vp.read_text().strip()
    return "0.0.0"

VERSION = _read_version()

DEFAULT_PROJECT = "LOCALAGENT"

def _ensure_dirs():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    APPS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# API KEY (separate from orchestrator for bootstrap)
# ============================================================

def get_api_key() -> Optional[str]:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]
    for p in [CONFIG_DIR / "api_key", SERVICE_DIR / "api_key", Path.home() / ".localagent-dev" / "api_key"]:
        if p.exists():
            return p.read_text().strip()
    return None

def set_api_key(key: str):
    _ensure_dirs()
    (CONFIG_DIR / "api_key").write_text(key.strip())

# ============================================================
# FASTAPI APP
# ============================================================

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    _ensure_dirs()
    # Initialize project on startup
    
    # Ensure project directory exists
    project_dir = PROJECTS_DIR / DEFAULT_PROJECT / "current"
    project_dir.mkdir(parents=True, exist_ok=True)
    
    set_project(DEFAULT_PROJECT)
    logger.info(f"LocalAgent v{VERSION} started on {HOST}:{PORT}")
    logger.info(f"Project: {DEFAULT_PROJECT}")
    logger.info(f"Outputs: {project_dir}")
    
    # Auto-sync with GitHub on startup
    try:
        from ..connectors.github import get_service_version, get_dashboard_version, REPOS
        from ..main import VERSION as LOCAL_VERSION
        
        github_version = get_service_version()
        logger.info(f"Local version: {LOCAL_VERSION}")
        logger.info(f"GitHub version: {github_version}")
        logger.info(f"Repos: {REPOS}")
        
        # Compare versions
        def version_tuple(v):
            try:
                return tuple(int(x) for x in str(v).split("."))
            except:
                return (0, 0, 0)
        
        local_v = version_tuple(LOCAL_VERSION)
        github_v = version_tuple(github_version)
        
        # Import Path for all paths below
        from pathlib import Path
        
        if local_v > github_v:
            logger.info(f"Local ({LOCAL_VERSION}) > GitHub ({github_version}) - Auto-pushing...")
            from ..connectors.github import github_push
            from ..engine.tracking import add_release_item
            
            # Push service
            service_dir = str(Path.home() / "localagent_v3")
            result = github_push(service_dir, "service", version=LOCAL_VERSION, create_release=True)
            if result.get("success"):
                logger.info(f"✅ Auto-pushed service v{LOCAL_VERSION}")
                # Log release
                add_release_item(
                    DEFAULT_PROJECT,
                    f"V{LOCAL_VERSION}",
                    "RELEASE",
                    f"Service updated to v{LOCAL_VERSION}",
                    LOCAL_VERSION,
                    result.get("commit_sha")
                )
            else:
                logger.warning(f"⚠️ Auto-push failed: {result.get('error')}")
            
            # Push dashboard
            dashboard_dir = str(Path.home() / "localagent_v3" / "dashboard")
            result = github_push(dashboard_dir, "dashboard", version=LOCAL_VERSION, create_release=True)
            if result.get("success"):
                logger.info(f"✅ Auto-pushed dashboard v{LOCAL_VERSION}")
                add_release_item(
                    DEFAULT_PROJECT,
                    f"D{LOCAL_VERSION}",
                    "RELEASE",
                    f"Dashboard updated to v{LOCAL_VERSION}",
                    LOCAL_VERSION,
                    result.get("commit_sha")
                )
            else:
                logger.warning(f"⚠️ Dashboard push failed: {result.get('error')}")
                
        elif github_v > local_v:
            logger.info(f"GitHub ({github_version}) > Local ({LOCAL_VERSION}) - Update available")
        else:
            logger.info(f"Versions in sync: {LOCAL_VERSION}")
        
        # === AUTO-PUSH MODULES ===
        # Check each module in /modules/ folder
        modules_dir = Path.home() / "localagent_v3" / "modules"
        if modules_dir.exists():
            for module_path in modules_dir.iterdir():
                if module_path.is_dir():
                    module_name = module_path.name
                    pkg_file = module_path / "package.json"
                    
                    if pkg_file.exists():
                        try:
                            import json as json_mod
                            pkg = json_mod.loads(pkg_file.read_text())
                            local_module_version = pkg.get("version", "0.0.0")
                            
                            # Check if module repo is configured
                            module_repo = None
                            for key, repo in REPOS.items():
                                if module_name in repo:
                                    module_repo = repo
                                    break
                            
                            if module_repo:
                                # Get GitHub version
                                try:
                                    import urllib.request
                                    url = f"https://api.github.com/repos/{module_repo}/releases/latest"
                                    req = urllib.request.Request(url, headers={"User-Agent": "LocalAgent"})
                                    resp = urllib.request.urlopen(req, timeout=5)
                                    data = json_mod.loads(resp.read())
                                    github_module_version = data.get("tag_name", "v0.0.0").lstrip("v")
                                except:
                                    github_module_version = "0.0.0"
                                
                                local_mv = version_tuple(local_module_version)
                                github_mv = version_tuple(github_module_version)
                                
                                if local_mv > github_mv:
                                    logger.info(f"Module {module_name}: Local ({local_module_version}) > GitHub ({github_module_version}) - Auto-pushing...")
                                    
                                    # Push module
                                    result = github_push(str(module_path), "chat-module", version=local_module_version, create_release=True)
                                    if result.get("success"):
                                        logger.info(f"✅ Auto-pushed {module_name} v{local_module_version}")
                                    else:
                                        logger.warning(f"⚠️ Module push failed: {result.get('error')}")
                                elif github_mv > local_mv:
                                    logger.info(f"Module {module_name}: GitHub ({github_module_version}) > Local ({local_module_version}) - Update available")
                                else:
                                    logger.info(f"Module {module_name}: v{local_module_version} in sync")
                        except Exception as e:
                            logger.warning(f"Module {module_name} check failed: {e}")
            
    except Exception as e:
        logger.warning(f"GitHub sync check failed: {e}")
    
    yield
    logger.info("LocalAgent shutting down")

app = FastAPI(title="LocalAgent Service Worker", version=VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ============================================================
# STATIC FILES FOR MODULES
# ============================================================

from fastapi.staticfiles import StaticFiles

def _find_modules_dir():
    """Find modules directory with multiple fallback paths."""
    candidates = [
        Path(__file__).parent.parent.parent / "modules",  # localagent_v3/modules/
        Path.home() / "localagent_v3" / "modules",  # ~/localagent_v3/modules/
        Path.cwd() / "modules",  # ./modules/
    ]
    for p in candidates:
        if p.exists() and p.is_dir():
            logger.info(f"Modules directory found: {p}")
            return p
    logger.warning(f"Modules directory not found. Tried: {[str(p) for p in candidates]}")
    return None

# Mount modules directory for static file serving
_modules_dir = _find_modules_dir()
if _modules_dir:
    app.mount("/modules", StaticFiles(directory=str(_modules_dir)), name="modules")
    logger.info(f"Mounted /modules -> {_modules_dir}")

# ============================================================
# DASHBOARD (serves static HTML - decoupled from service worker)
# ============================================================

from fastapi.responses import HTMLResponse, FileResponse

def _find_dashboard():
    """Find dashboard HTML with multiple fallback paths."""
    candidates = [
        Path(__file__).parent.parent.parent / "dashboard" / "index.html",  # localagent_v3/dashboard/
        Path(__file__).parent.parent / "dashboard" / "index.html",  # localagent/dashboard/
        Path.home() / "localagent_v3" / "dashboard" / "index.html",  # ~/localagent_v3/dashboard/
        Path.cwd() / "dashboard" / "index.html",  # ./dashboard/
    ]
    for p in candidates:
        if p.exists():
            logger.info(f"Dashboard found: {p}")
            return p
    logger.warning(f"Dashboard not found. Tried: {[str(p) for p in candidates]}")
    return None

DASHBOARD_HTML = _find_dashboard()

@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve standalone dashboard HTML."""
    if DASHBOARD_HTML and DASHBOARD_HTML.exists():
        return HTMLResponse(DASHBOARD_HTML.read_text())
    return HTMLResponse("""
        <html><body style="font-family:system-ui;padding:40px;">
        <h1>LocalAgent Service Worker v""" + VERSION + """</h1>
        <p>Dashboard HTML not found.</p>
        <p>Expected at: ~/localagent_v3/dashboard/index.html</p>
        <p>API available at <a href="/api/health">/api/health</a></p>
        <p>Docs at <a href="/docs">/docs</a></p>
        </body></html>
    """)

@app.get("/manifest.json")
async def manifest():
    """Serve PWA manifest for install prompt."""
    from fastapi.responses import JSONResponse
    if DASHBOARD_HTML:
        manifest_path = DASHBOARD_HTML.parent / "manifest.json"
        if manifest_path.exists():
            import json
            return JSONResponse(json.loads(manifest_path.read_text()))
    return JSONResponse({
        "name": "LocalAgent Dashboard",
        "short_name": "LocalAgent",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#f5f5f5",
        "theme_color": "#1a73e8"
    })

# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
async def health():
    
    project_dir = PROJECTS_DIR / DEFAULT_PROJECT / "current"
    
    # Get service version from GitHub (ENV012)
    github_version = get_service_version()
    project_version = get_project_version(DEFAULT_PROJECT)
    
    return {
        "status": "ok",
        "version": VERSION,  # Local version for comparison
        "github_version": github_version,  # Version from GitHub releases
        "project": DEFAULT_PROJECT,
        "project_version": project_version,  # Project's own version
        "project_path": str(project_dir),
        "project_exists": project_dir.exists(),
        "api_key": get_api_key() is not None,
        "websocket_clients": len(ws_manager.active_connections),
        "github_repos": REPOS,
        "timestamp": datetime.now().isoformat()
    }

# ============================================================
# PROJECT MANAGEMENT
# ============================================================

@app.get("/api/projects")
async def list_projects():
    """List available projects."""
    if not PROJECTS_DIR.exists():
        return {"projects": [], "current": DEFAULT_PROJECT}
    projects = [d.name for d in PROJECTS_DIR.iterdir() if d.is_dir()]
    return {"projects": projects, "current": DEFAULT_PROJECT}

@app.post("/api/project/select")
async def select_project(data: Dict[str, Any]):
    """Select active project."""
    global DEFAULT_PROJECT
    project = data.get("project", "")
    if not project:
        raise HTTPException(400, "Project name required")
    
    
    project_dir = PROJECTS_DIR / project
    if not project_dir.exists():
        # Create it
        (project_dir / "current").mkdir(parents=True, exist_ok=True)
    
    DEFAULT_PROJECT = project
    set_project(project)
    logger.info(f"Project switched to: {project}")
    return {"success": True, "project": project}


# ============================================================
# PROTOCOL TRACKING API
# ============================================================

# In-memory store for execution history (persisted to file)
_execution_history: List[Dict] = []
_execution_history_file = Path.home() / ".localagent" / "execution_history.json"

def _load_execution_history():
    """Load execution history from file."""
    global _execution_history
    try:
        if _execution_history_file.exists():
            _execution_history = json.loads(_execution_history_file.read_text())
    except Exception as e:
        logger.error(f"Failed to load execution history: {e}")
        _execution_history = []

def _save_execution_history():
    """Save execution history to file."""
    try:
        _execution_history_file.parent.mkdir(parents=True, exist_ok=True)
        _execution_history_file.write_text(json.dumps(_execution_history[-100:], indent=2))  # Keep last 100
    except Exception as e:
        logger.error(f"Failed to save execution history: {e}")

def record_execution(execution_data: Dict):
    """Record a protocol execution for history."""
    _execution_history.append({
        "execution_id": execution_data.get("execution_id"),
        "todo_id": execution_data.get("todo_id"),
        "todo_title": execution_data.get("todo_title"),
        "status": execution_data.get("status"),
        "github_version_before": execution_data.get("github_version_before"),
        "github_version_after": execution_data.get("github_version_after"),
        "violations": execution_data.get("violations", []),
        "started_at": execution_data.get("started_at"),
        "completed_at": execution_data.get("completed_at"),
    })
    _save_execution_history()

# Load history on startup
_load_execution_history()

@app.get("/api/protocol/history")
async def get_protocol_history(limit: int = Query(20, ge=1, le=100)):
    """Get protocol execution history."""
    return {
        "executions": _execution_history[-limit:][::-1],  # Most recent first
        "total": len(_execution_history)
    }

@app.get("/api/protocol/steps")
async def get_protocol_steps():
    """Get protocol step definitions."""
    return {"steps": PROTOCOL_STEPS}

@app.post("/api/protocol/notify")
async def notify_protocol_event(data: Dict[str, Any]):
    """Receive protocol events and broadcast via WebSocket."""
    event_type = data.get("type")
    
    # Broadcast to all connected clients
    await ws_manager.broadcast(data)
    
    # Record completed executions
    if event_type == "protocol_end":
        record_execution(data)
    
    return {"success": True}

# ============================================================
# WEBSOCKET (real-time updates)
# ============================================================

# Store for tracking known versions
_known_versions: Dict[str, str] = {}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates to dashboard/clients."""
    await ws_manager.connect(websocket)
    
    # Send welcome message
    await ws_manager.send_personal(websocket, {
        "type": "connected",
        "version": VERSION,
        "message": "Connected to LocalAgent Service Worker"
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # Handle ping
            if data.get("type") == "ping":
                await ws_manager.send_personal(websocket, {"type": "pong"})
            
            # Handle version check request
            elif data.get("type") == "check_update":
                owner = data.get("owner", "")
                repo = data.get("repo", "")
                current_version = data.get("current_version", "")
                
                if owner and repo:
                    update_info = await check_repo_update(owner, repo, current_version)
                    await ws_manager.send_personal(websocket, {
                        "type": "update_status",
                        "repo": f"{owner}/{repo}",
                        **update_info
                    })
            
            # Handle subscribe to updates
            elif data.get("type") == "subscribe":
                # Client wants to receive update notifications
                await ws_manager.send_personal(websocket, {
                    "type": "subscribed",
                    "message": "You will receive update notifications"
                })
    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


async def check_repo_update(owner: str, repo: str, current_version: str) -> dict:
    """Check if a newer version is available on GitHub."""
    import urllib.request
    import urllib.error
    
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "LocalAgent"})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        
        latest_version = data.get("tag_name", "")
        
        # Compare versions
        def parse_version(v):
            import re
            match = re.search(r'(\d+)\.(\d+)\.(\d+)', v)
            if match:
                return tuple(map(int, match.groups()))
            return (0, 0, 0)
        
        current = parse_version(current_version)
        latest = parse_version(latest_version)
        
        update_available = latest > current
        
        return {
            "update_available": update_available,
            "current_version": current_version,
            "latest_version": latest_version,
            "release_name": data.get("name", ""),
            "release_url": data.get("html_url", ""),
            "published_at": data.get("published_at", "")
        }
    
    except Exception as e:
        return {
            "update_available": False,
            "error": str(e)
        }


async def broadcast_update_available(repo: str, version: str, url: str):
    """Broadcast update notification to all connected clients."""
    await ws_manager.broadcast({
        "type": "update_available",
        "repo": repo,
        "version": version,
        "url": url,
        "message": f"New version {version} available for {repo}"
    })

# ============================================================
# DASHBOARD API ENDPOINTS (for dynamic HTML)
# ============================================================

@app.get("/api/status")
async def get_status():
    """Get agent status for dashboard."""
    set_project(DEFAULT_PROJECT)
    return dash_status()

@app.get("/api/conversation")
async def get_conversation_endpoint(project: str = Query(default=None)):
    """Get conversation history."""
    return get_conversation(project or DEFAULT_PROJECT)

@app.get("/api/backlog")
async def get_backlog_endpoint(project: str = Query(default=None)):
    """Get backlog items."""
    return get_backlog(project or DEFAULT_PROJECT)

@app.get("/api/todo")
async def get_todo_endpoint(project: str = Query(default=None)):
    """Get TODO items."""
    return get_todo(project or DEFAULT_PROJECT)

@app.get("/api/changelog")
async def get_changelog_endpoint(project: str = Query(default=None)):
    """Get changelog."""
    return get_changelog(project or DEFAULT_PROJECT)

@app.get("/api/release-notes/preview")
async def preview_release_notes(project: str = Query(default=None), version: str = Query(default=None)):
    """Preview auto-generated release notes before publishing."""
    from ..engine.tracking import generate_release_notes
    from pathlib import Path
    
    # Get version from VERSION file if not provided
    if not version:
        version_file = Path.home() / "localagent_v3" / "VERSION"
        if version_file.exists():
            version = version_file.read_text().strip()
        else:
            version = "0.0.0"
    
    notes = generate_release_notes(project or DEFAULT_PROJECT, version)
    return {
        "version": version,
        "notes": notes,
        "project": project or DEFAULT_PROJECT
    }

@app.get("/api/errors")
async def get_errors_endpoint(project: str = Query(default=None)):
    """Get learned errors."""
    return load_learned_errors(project or DEFAULT_PROJECT)

@app.get("/api/constraints")
async def get_constraints_endpoint():
    """Get all constraints."""
    return {"constraints": get_all_constraints()}

@app.get("/api/snapshots")
async def get_snapshots_endpoint(project: str = Query(default=None)):
    """Get project snapshots."""
    snapshots = list_snapshots(project or DEFAULT_PROJECT)
    return {"snapshots": snapshots, "count": len(snapshots)}

@app.get("/api/outputs")
async def get_outputs_endpoint(project: str = Query(default=None)):
    """Get output files list."""
    return get_output_files(project or DEFAULT_PROJECT)

from fastapi.responses import FileResponse

@app.get("/outputs/{filename:path}")
async def serve_output_file(filename: str, project: str = Query(default=None)):
    """Serve output file."""
    filepath = get_outputs_path(project or DEFAULT_PROJECT) / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath)

@app.post("/api/chat")
async def chat_endpoint(data: Dict[str, Any]):
    """
    Handle chat message with FULL PROTOCOL visualization.
    Returns protocol steps for dashboard display.
    """
    
    set_project(DEFAULT_PROJECT)
    message = data.get("message", "").strip()
    history = data.get("history", [])  # Get conversation history
    
    if not message:
        return {"error": "Empty message", "response": "Empty message"}
    
    # Track protocol steps for frontend
    protocol_steps = []
    
    # === STEP 1: LINT ===
    protocol_steps.append({"step": "lint", "status": "running", "label": "Linting prompt"})
    lint_result = lint_prompt(message)
    optimized_prompt, lint_report = preprocess_for_negotiation(message, DEFAULT_PROJECT)
    
    # Check if this is just conversation (not a task)
    from ..roadmap.prompt_optimizer import is_conversational
    is_conversation = is_conversational(message) or lint_report.get("task_type", {}).get("type") == "conversation"
    
    protocol_steps[0] = {
        "step": "lint",
        "status": "complete",
        "label": f"Linting ({lint_report['score']}/100)",
        "score": lint_report['score'],
        "issues": lint_report.get('issues', []),
        "optimized": optimized_prompt if optimized_prompt != message else None,
        "is_conversation": is_conversation
    }
    
    # Build conversation context from history
    conversation_context = ""
    if history:
        conversation_context = "Previous conversation:\n"
        for msg in history[-6:]:  # Last 6 messages (3 exchanges)
            role = msg.get("role", "user")
            content = msg.get("content", "")[:500]  # Truncate long messages
            conversation_context += f"{role.upper()}: {content}\n"
        conversation_context += "\n---\nCurrent message:\n"
    
    # If it's just conversation, skip task execution and respond directly
    if is_conversation:
        protocol_steps.append({
            "step": "conversation",
            "status": "complete", 
            "label": "Conversation mode (no tasks)"
        })
        
        add_message(DEFAULT_PROJECT, "user", message)
        
        # Call Claude for simple conversation (no task format required)
        try:
            full_prompt = conversation_context + message if conversation_context else message
            result = call_claude(full_prompt, f"This is a casual conversation. Respond naturally in the same language as the user. Do NOT return JSON or tasks. Be helpful and remember the context of our conversation. Project: {DEFAULT_PROJECT}")
            response_text = result.get("response", "I'm here to help!") if result.get("success") else "Hello! How can I help you?"
        except:
            response_text = "Hello! How can I help you today?"
        
        add_message(DEFAULT_PROJECT, "assistant", response_text)
        
        return {
            "status": "ok",
            "response": response_text,
            "protocol": protocol_steps,
            "thinking": "Conversation detected - no task execution",
            "tasks": [],
            "files": [],
            "tokens": lint_report.get("tokens", {}).get("estimated", 0)
        }
    
    # === STEP 2: CONSTRAINTS ===
    protocol_steps.append({"step": "constraints", "status": "running", "label": "Checking constraints"})
    is_valid, violations = validate_action("chat", {"message": message, "project": DEFAULT_PROJECT})
    constraints_context = get_constraints_for_context()
    
    protocol_steps[1] = {
        "step": "constraints",
        "status": "complete" if is_valid else "warning",
        "label": f"Constraints ({'OK' if is_valid else f'{len(violations)} violations'})",
        "valid": is_valid,
        "violations": violations,
        "context": constraints_context[:500] if constraints_context else None
    }
    
    # === STEP 3: NEGOTIATE ===
    protocol_steps.append({"step": "negotiate", "status": "running", "label": "Negotiating with Claude"})
    
    add_message(DEFAULT_PROJECT, "user", message)
    
    # Include conversation history in context
    full_context = f"PROJECT: {DEFAULT_PROJECT}\n{constraints_context}"
    if conversation_context:
        full_context = conversation_context + full_context
    
    success, result = negotiate_request(
        project=DEFAULT_PROJECT,
        instruction=optimized_prompt,
        call_claude_fn=call_claude,
        context=full_context,
        max_retries=3
    )
    
    attempts = result.get("attempts", [])
    protocol_steps[2] = {
        "step": "negotiate",
        "status": "complete" if success else "error",
        "label": f"Negotiation ({len(attempts)} attempts)",
        "success": success,
        "attempts": len(attempts),
        "error": result.get("error") if not success else None
    }
    
    # === STEP 4: EXECUTE TASKS ===
    if success:
        tasks = result.get("tasks", [])
        protocol_steps.append({
            "step": "execute",
            "status": "complete",
            "label": f"Executed {len(tasks)} tasks",
            "tasks": [{"id": t.get("id"), "type": t.get("type")} for t in tasks]
        })
        
        # Build response
        response_lines = []
        
        # First, add Claude's message (the actual response!)
        # But clean it - remove any code blocks that shouldn't be there
        claude_message = result.get("message", "")
        if claude_message:
            # Remove code blocks from message (they should be in task.content, not message)
            import re
            # Remove ```...``` blocks
            claude_message = re.sub(r'```[\s\S]*?```', '', claude_message)
            # Remove HTML tags that look like full documents
            if '<html' in claude_message.lower() or '<!doctype' in claude_message.lower():
                # Extract just the first sentence before any HTML
                parts = re.split(r'<[!a-zA-Z]', claude_message, 1)
                claude_message = parts[0].strip()
            # Remove excessive code-like content (more than 10 lines starting with spaces/tabs)
            lines_check = claude_message.split('\n')
            if len([l for l in lines_check if l.startswith('  ') or l.startswith('\t')]) > 10:
                # Too much code-like content, truncate
                clean_lines = []
                for line in lines_check:
                    if line.startswith('  ') or line.startswith('\t') or line.strip().startswith('<'):
                        if clean_lines and not clean_lines[-1].endswith(':'):
                            break
                    clean_lines.append(line)
                claude_message = '\n'.join(clean_lines[:5])
            
            claude_message = claude_message.strip()
            if claude_message:
                response_lines.append(claude_message)
                response_lines.append("")
        
        if lint_report["issue_count"] > 0:
            response_lines.append(f"🔍 Linter: {lint_report['issue_count']} issues (score: {lint_report['score']})")
        
        if tasks:
            response_lines.append(f"✅ {len(tasks)} tasks validated (ACK)")
        
        saved_files = []
        file_attachments = []  # For downloadable files
        
        for task in tasks:
            task_id = task.get("id", "T???")
            task_type = task.get("type", "unknown").lower()
            
            # Log task for debugging
            print(f"   Processing task: {task_id} type={task_type}")
            
            # Check if this is a file creation task (various possible type names)
            is_file_task = task_type in ("create_file", "file", "create", "write_file", "create_file", "write", "code", "html")
            # Also check if there's filename + content regardless of type
            has_file_content = (task.get("filename") or task.get("file_path") or task.get("file")) and (task.get("content") or task.get("code"))
            
            if is_file_task or has_file_content:
                filename = task.get("filename") or task.get("file_path") or task.get("file") or f"{task_id}.txt"
                content = task.get("content", "") or task.get("code", "") or task.get("html", "")
                if filename and content:
                    from ..engine.tracking import register_output_file
                    from pathlib import Path
                    clean_name = Path(filename).name
                    filepath = register_output_file(DEFAULT_PROJECT, clean_name, content)
                    saved_files.append(clean_name)
                    response_lines.append(f"📄 {task_id}: Created {clean_name}")
                    print(f"   ✓ Saved file: {clean_name} ({len(content)} bytes)")
                    
                    # Add to attachments for download
                    file_attachments.append({
                        "name": clean_name,
                        "url": f"/outputs/{clean_name}",
                        "size": len(content),
                        "type": Path(clean_name).suffix.lower()
                    })
                else:
                    print(f"   ✗ Task has no content: filename={filename}, content_len={len(content) if content else 0}")
            else:
                response_lines.append(f"📋 {task_id}: {task.get('description', '')[:50]}")
        
        if saved_files:
            response_lines.append(f"\n📁 Files: {', '.join(saved_files)}")
        
        usage = result.get("usage", {})
        if usage:
            tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
            response_lines.append(f"💰 Tokens: {tokens}")
        
        response = "\n".join(response_lines)
    else:
        response = f"❌ Failed after {len(attempts)} attempts\nError: {result.get('error', 'unknown')}"
        if result.get("detail"):
            response += f"\nDetail: {result.get('detail')[:200]}"
        file_attachments = []
    
    add_message(DEFAULT_PROJECT, "agent", response)
    
    return {
        "status": "ok" if success else "error",
        "response": response,
        "protocol": protocol_steps,
        "thinking": constraints_context[:300] if constraints_context else None,
        "files": file_attachments,
        "tokens": result.get("usage", {}).get("input_tokens", 0) + result.get("usage", {}).get("output_tokens", 0) if success else 0
    }

@app.post("/api/backlog/add")
async def add_backlog_endpoint(data: Dict[str, Any]):
    """Add backlog item."""
    item_id = add_backlog_item(DEFAULT_PROJECT, data.get("title", ""), data.get("priority", "medium"))
    return {"id": item_id}

@app.post("/api/todo/add")
async def add_todo_endpoint(data: Dict[str, Any]):
    """Add TODO item (roadmap only, no release)."""
    item_id = add_todo_item(DEFAULT_PROJECT, data.get("title", ""), data.get("category", "todo"))
    return {"id": item_id, "triggers_release": False}

@app.post("/api/nth/add")
async def add_nth_endpoint(data: Dict[str, Any]):
    """Add NTH item (roadmap only, no release)."""
    item_id = add_todo_item(DEFAULT_PROJECT, data.get("title", ""), "nth")
    return {"id": item_id, "triggers_release": False}

@app.post("/api/todo/complete")
async def complete_todo_endpoint(data: Dict[str, Any]):
    """Mark TODO item as done (manual toggle, no release)."""
    item_id = data.get("id", "")
    success = toggle_todo(DEFAULT_PROJECT, item_id)
    return {"success": success, "id": item_id}

@app.post("/api/todo/restore")
async def restore_todo_endpoint(data: Dict[str, Any]):
    """Restore a completed TODO back to pending."""
    item_id = data.get("id", "")
    
    todo = get_todo(DEFAULT_PROJECT)
    for item in todo:
        if item["id"] == item_id:
            item["done"] = False
            item["status"] = "pending"
            item.pop("completed", None)
            item.pop("version", None)
            item.pop("commit_sha", None)
            item.pop("release_url", None)
            save_todo(DEFAULT_PROJECT, todo)
            return {"success": True, "id": item_id, "status": "pending"}
    
    return {"success": False, "error": f"TODO {item_id} not found"}

@app.post("/api/todo/restore-all")
async def restore_all_todos_endpoint():
    """Restore ALL completed TODOs back to pending."""
    
    todo = get_todo(DEFAULT_PROJECT)
    restored = []
    for item in todo:
        if item.get("done") or item.get("status") == "done":
            item["done"] = False
            item["status"] = "pending"
            item.pop("completed", None)
            item.pop("version", None)
            item.pop("commit_sha", None)
            item.pop("release_url", None)
            restored.append(item["id"])
    
    save_todo(DEFAULT_PROJECT, todo)
    return {"success": True, "restored": restored, "count": len(restored)}

# ============================================================
# BUGFIX API (Always triggers release)
# ============================================================

@app.get("/api/bugfix")
async def get_bugfixes_endpoint(project: str = Query(default=None)):
    """Get all bugfixes."""
    return {"bugfixes": get_bugfixes(project or DEFAULT_PROJECT)}

@app.get("/api/bugfix/pending")
async def get_pending_bugfixes_endpoint(project: str = Query(default=None)):
    """Get pending bugfixes."""
    return {"bugfixes": get_pending_bugfixes(project or DEFAULT_PROJECT)}

@app.post("/api/bugfix/add")
async def add_bugfix_endpoint(data: Dict[str, Any]):
    """
    Add a bugfix entry (records it, doesn't apply yet).
    Call /api/bugfix/apply after fix is complete.
    """
    item_id = add_bugfix(
        DEFAULT_PROJECT,
        data.get("title", ""),
        data.get("description", ""),
        data.get("source", "manual")
    )
    return {"id": item_id, "status": "pending", "triggers_release": False}

@app.post("/api/bugfix/apply")
async def apply_bugfix_endpoint(data: Dict[str, Any]):
    """
    Apply a bugfix - this TRIGGERS a release.
    
    This pushes to GitHub and creates a release. The LOCAL version
    is NOT updated - user must install the update to get new version.
    
    Required:
        - bugfix_id: The bugfix ID (BF001)
        - commit_sha: Git commit SHA (REQUIRED)
        
    Optional:
        - version: Version to release (auto-incremented if not provided)
        - files_changed: List of modified files
        - push: Whether to push to GitHub (default: true)
    """
    
    bugfix_id = data.get("bugfix_id")
    commit_sha = data.get("commit_sha")
    
    if not bugfix_id:
        raise HTTPException(400, "bugfix_id required")
    if not commit_sha:
        raise HTTPException(400, "commit_sha required - bugfixes must be linked to git commits")
    
    # Get or calculate version - based on GitHub version
    version = data.get("version")
    if not version:
        github_version = get_service_version()
        parts = github_version.split(".")
        if len(parts) == 3:
            version = f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"
        else:
            version = increment_version(DEFAULT_PROJECT)
    
    # Apply bugfix (records in tracking)
    success = apply_bugfix(
        DEFAULT_PROJECT,
        bugfix_id,
        version,
        commit_sha,
        data.get("files_changed", [])
    )
    
    if not success:
        raise HTTPException(404, f"Bugfix {bugfix_id} not found")
    
    result = {
        "success": True,
        "bugfix_id": bugfix_id,
        "version": version,
        "commit_sha": commit_sha,
        "triggers_release": True,
        "note": "Update available - install to apply new version"
    }
    
    # Push to GitHub if requested
    if data.get("push", True):
        from pathlib import Path
        service_dir = Path.home() / "localagent_v3"
        
        # UPDATE VERSION FILES BEFORE PUSHING
        # This ensures the zip contains the correct version
        version_file = service_dir / "VERSION"
        main_py = service_dir / "localagent" / "main.py"
        server_py = service_dir / "localagent" / "service" / "server.py"
        
        # Read current versions for replacement
        if version_file.exists():
            old_version = version_file.read_text().strip()
            version_file.write_text(version)
        
        if main_py.exists():
            content = main_py.read_text()
            content = content.replace(f'VERSION = "{old_version}"', f'VERSION = "{version}"')
            main_py.write_text(content)
        
        if server_py.exists():
            content = server_py.read_text()
            content = content.replace(f'VERSION = "{old_version}"', f'VERSION = "{version}"')
            server_py.write_text(content)
        
        # Generate release notes
        release_notes = generate_release_notes(DEFAULT_PROJECT, version)
        
        # Push and create release
        loop = asyncio.get_event_loop()
        push_result = await loop.run_in_executor(
            None,
            lambda: github_push(str(service_dir), "service", version=version, create_release=True)
        )
        
        result["push"] = push_result
        result["release_notes"] = release_notes
    
    return result

# ============================================================
# RELEASE MANAGEMENT
# ============================================================

@app.get("/api/releases")
async def get_releases_endpoint(project: str = Query(default=None)):
    """Get release log."""
    return {"releases": get_release_log(project or DEFAULT_PROJECT)}

@app.post("/api/releases")
async def add_release_endpoint(data: Dict[str, Any]):
    """Manually add a release entry."""
    
    add_release_item(
        project=data.get("project", DEFAULT_PROJECT),
        item_id=data.get("id", "MANUAL"),
        item_type=data.get("type", "RELEASE"),
        title=data.get("title", ""),
        version=data.get("version", ""),
        commit_sha=data.get("commit_sha")
    )
    return {"success": True}

@app.post("/api/releases/seed")
async def seed_releases_endpoint(data: Dict[str, Any] = None):
    """Seed release log with version history. Use force=true to overwrite."""
    
    data = data or {}
    force = data.get("force", False)
    
    releases = get_release_log(DEFAULT_PROJECT)
    if releases and not force:
        return {"success": False, "message": "Releases already exist. Use force=true to overwrite.", "count": len(releases)}
    
    if force:
        save_release_log(DEFAULT_PROJECT, [])  # Clear existing
    
    # Seed with recent versions
    history = [
        ("3.0.47", "RELEASE", "Release seed API, version correction"),
        ("3.0.46", "BUGFIX", "Release logging on auto-push"),
        ("3.0.45", "TODO", "Release notes modal on version click"),
        ("3.0.44", "BUGFIX", "Chat scroll fix (min-height:0), module auto-push"),
        ("3.0.43", "TODO", "Full protocol integration, real-time linting, GitHub chat-module display"),
        ("3.0.42", "TODO", "Unified dark theme dashboard with Chat Pro embedded"),
        ("3.0.41", "BUGFIX", "GitHub org permission fallback to user account"),
        ("3.0.40", "TODO", "Module init with GitHub API repo creation"),
    ]
    
    for version, item_type, title in history:
        add_release_item(
            DEFAULT_PROJECT,
            f"V{version}",
            item_type,
            title,
            version
        )
    
    return {"success": True, "seeded": len(history)}

@app.get("/api/releases/{version}")
async def get_release_by_version(version: str, project: str = Query(default=None)):
    """Get releases for a specific version."""
    return {"releases": get_releases_for_version(project or DEFAULT_PROJECT, version)}

@app.get("/api/release-notes")
async def get_release_notes_endpoint(version: str = Query(default=None), project: str = Query(default=None)):
    """Generate release notes."""
    notes = generate_release_notes(project or DEFAULT_PROJECT, version)
    return {"notes": notes, "version": version}

@app.get("/api/release-notes/github")
async def get_github_release_notes_endpoint(version: str = Query(default=None)):
    """Fetch release notes from GitHub releases."""
    import urllib.request
    import json as json_mod
    
    repo = REPOS.get("service", "")
    if not repo:
        return {"notes": None, "error": "No service repo configured"}
    
    try:
        token = _get_token()
        headers = {"User-Agent": "LocalAgent"}
        if token:
            headers["Authorization"] = f"token {token}"
        
        if version:
            # Get specific release
            url = f"https://api.github.com/repos/{repo}/releases/tags/v{version}"
        else:
            # Get latest release
            url = f"https://api.github.com/repos/{repo}/releases/latest"
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json_mod.loads(resp.read())
            return {
                "version": data.get("tag_name", "").lstrip("v"),
                "name": data.get("name"),
                "notes": data.get("body", ""),
                "published_at": data.get("published_at"),
                "html_url": data.get("html_url")
            }
    except Exception as e:
        return {"notes": None, "error": str(e)}

@app.get("/api/release-notes/github/all")
async def get_all_github_releases_endpoint(limit: int = Query(default=10)):
    """Fetch all release notes from GitHub."""
    import urllib.request
    import json as json_mod
    
    repo = REPOS.get("service", "")
    if not repo:
        return {"releases": [], "error": "No service repo configured"}
    
    try:
        token = _get_token()
        headers = {"User-Agent": "LocalAgent"}
        if token:
            headers["Authorization"] = f"token {token}"
        
        url = f"https://api.github.com/repos/{repo}/releases?per_page={limit}"
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json_mod.loads(resp.read())
            releases = [{
                "version": r.get("tag_name", "").lstrip("v"),
                "name": r.get("name"),
                "notes": r.get("body", ""),
                "published_at": r.get("published_at"),
                "html_url": r.get("html_url")
            } for r in data]
            return {"releases": releases}
    except Exception as e:
        return {"releases": [], "error": str(e)}

@app.get("/api/release-notes/full")
async def get_full_release_notes_endpoint(project: str = Query(default=None)):
    """Generate full release notes for all versions."""
    notes = generate_full_release_notes(project or DEFAULT_PROJECT)
    return {"notes": notes}

# ============================================================
# ROADMAP
# ============================================================

@app.get("/api/roadmap")
async def get_roadmap_endpoint(project: str = Query(default=None)):
    """Get roadmap (pending TODOs and NTHs)."""
    return get_roadmap(project or DEFAULT_PROJECT)

@app.get("/api/roadmap/md")
async def get_roadmap_md_endpoint(project: str = Query(default=None)):
    """Generate roadmap markdown."""
    md = generate_roadmap_md(project or DEFAULT_PROJECT)
    return {"markdown": md}

# ============================================================
# TODO BATCH PROCESSING - PROTOCOL COMPLIANT (v3.0.30)
# ============================================================

@app.post("/api/todo/process")
async def process_todo_batch(data: Dict[str, Any]):
    """
    Process TODO items with STRICT PROTOCOL ENFORCEMENT.
    
    Uses ProtocolExecutor which enforces:
    1. Fetch version from GitHub (ENV012)
    2. Calculate next version
    3. Snapshot BEFORE (ENV003)
    4. Build Claude context with version (ENV015)
    5. Call Claude
    6. Validate response (CTX001, CTX003, CTX004)
    7. Execute tasks
    8. Snapshot AFTER (ENV014)
    9. Git commit (ENV004)
    10. Git push (ENV009)
    11. Create GitHub release (ENV012)
    12. Verify release (ENV013)
    13. Mark TODO done
    
    Every step is tracked and logged.
    """
    
    project = data.get("project", DEFAULT_PROJECT)
    max_items = data.get("max_items", 1)
    github_repo = data.get("github_repo", REPOS.get("service", "THEMiS-eng/localagent"))
    github_token = data.get("github_token")
    
    # Get pending TODOs
    todos = get_todo(project)
    pending = [t for t in todos if not t.get("done") and t.get("status") != "done"]
    
    if not pending:
        return {"success": True, "message": "No pending TODOs", "processed": 0}
    
    results = []
    
    # Wrapper for Claude call that matches protocol signature
    def claude_wrapper(system: str, user: str) -> str:
        return call_claude(
            system_prompt=system,
            user_message=user,
            max_tokens=4000
        )
    
    for todo in pending[:max_items]:
        todo_id = todo.get("id")
        todo_title = todo.get("title", "")
        
        # Execute with full protocol
        execution = process_todo_with_protocol(
            project=project,
            github_repo=github_repo,
            todo_id=todo_id,
            todo_title=todo_title,
            call_claude_fn=claude_wrapper,
            github_token=github_token
        )
        
        # Convert to result format
        result = {
            "id": todo_id,
            "title": todo_title,
            "execution_id": execution.execution_id,
            "status": execution.status,
            "version_before": execution.github_version_before,
            "version_after": execution.github_version_after,
            "files": execution.files_created,
            "release_url": execution.release_url,
            "steps": [
                {
                    "step": s.name,
                    "status": s.status,
                    "error": s.error
                }
                for s in execution.steps
            ],
            "violations": execution.violations,
            "success": execution.status == "success"
        }
        results.append(result)
        
        # Stop on failure
        if execution.status != "success":
            logger.error(f"❌ Protocol failed for {todo_id}, stopping batch")
            break
    
    success_count = sum(1 for r in results if r.get("success"))
    
    return {
        "success": success_count == len(results),
        "processed": len(results),
        "successful": success_count,
        "failed": len(results) - success_count,
        "remaining": len(pending) - len(results),
        "results": results
    }

@app.get("/api/todo/pending")
async def get_pending_todos():
    """Get pending TODO items ready for processing."""
    
    todos = get_todo(DEFAULT_PROJECT)
    pending = [t for t in todos if not t.get("done") and t.get("status") != "done"]
    
    return {
        "count": len(pending),
        "items": pending
    }

@app.post("/api/todo/process-all")
async def process_all_todos(data: Dict[str, Any]):
    """
    Process ALL pending TODOs sequentially.
    Each TODO = 1 build + 1 git release.
    
    Use with caution - this will process all items.
    """
    
    todos = get_todo(DEFAULT_PROJECT)
    pending = [t for t in todos if not t.get("done") and t.get("status") != "done"]
    
    if not pending:
        return {"success": True, "message": "No pending TODOs", "processed": 0}
    
    # Process all by calling process with max_items = total pending
    data["max_items"] = len(pending)
    return await process_todo_batch(data)

@app.post("/api/clear")
async def clear_conversation_endpoint():
    """Clear conversation."""
    clear_conversation(DEFAULT_PROJECT)
    return {"status": "cleared"}

@app.post("/api/outputs/delete")
async def delete_output_endpoint(data: Dict[str, Any]):
    """Delete output file."""
    success = delete_output_file(DEFAULT_PROJECT, data.get("filename", ""))
    return {"status": "deleted" if success else "not_found"}

# ============================================================
# CLAUDE API (via orchestrator)
# ============================================================

class ClaudeRequest(BaseModel):
    message: str
    system: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    app_id: Optional[str] = "themis"
    project: Optional[str] = DEFAULT_PROJECT
    max_tokens: int = 4096

@app.post("/api/claude/complete")
async def claude_complete(req: ClaudeRequest):
    """
    Call Claude with FULL PROTOCOL:
    0. LINT prompt (detect issues, optimize)
    1. Negotiate with retry intelligence
    2. Validate ACK
    3. Execute tasks
    
    Context Injection (ENV011/ENV012/ENV015):
    - Console errors (ENV011)
    - Version info (ENV012/ENV015)
    - Known bugfixes
    """
    
    api_key = get_api_key()
    if not api_key:
        raise HTTPException(503, "No API key configured")
    
    # === STEP 0: LINT PROMPT ===
    optimized_prompt, lint_report = preprocess_for_negotiation(req.message, req.project)
    
    logger.info(f"LINTER: score={lint_report['score']}, issues={lint_report['issue_count']}")
    
    # Build context with injections
    context_parts = []
    
    # ENV012/ENV015: INJECT VERSION CONTEXT
    version_context = await get_version_context_for_claude()
    if version_context:
        context_parts.append(version_context)
    
    # ENV011: INJECT CONSOLE ERRORS FOR SELF-CORRECTION
    console_errors = get_console_errors_for_claude()
    if console_errors:
        context_parts.append(console_errors)
        logger.info(f"Injecting {len(_console_errors)} console errors")
    
    # INJECT KNOWN BUGFIXES
    bugfixes_context = get_bugfixes_context()
    if bugfixes_context:
        context_parts.append(bugfixes_context)
    
    # INJECT CONSTRAINTS (ENV/CTX)
    constraints = get_all_constraints()
    if constraints:
        constraints_text = "CONSTRAINTS (MUST RESPECT):\n"
        for c in constraints:
            sev = c.get("severity", "MEDIUM")
            constraints_text += f"- [{c['id']}] ({sev}) {c['rule']}\n"
        context_parts.append(constraints_text)
    
    # Add lint report summary
    if lint_report["issue_count"] > 0:
        lint_summary = f"LINTER REPORT (score: {lint_report['score']}):\n"
        for issue in lint_report["issues"][:5]:
            lint_summary += f"- {issue['message']}\n"
        context_parts.append(lint_summary)
    
    # Add user context
    if req.context:
        context_parts.append(f"USER CONTEXT:\n{json.dumps(req.context, indent=2, default=str)}")
    
    full_context = "\n\n".join(context_parts)
    
    if req.system:
        full_context = f"SYSTEM: {req.system}\n\n{full_context}"
    
    # === STEP 1-2: NEGOTIATE WITH CLAUDE ===
    # Create a simple call function for the negotiator
    def call_claude_fn(prompt: str, context: str):
        """Sync Claude call for negotiator."""
        import urllib.request
        import urllib.error
        
        system = req.system or "You are a helpful assistant."
        if context:
            system += f"\n\nCONTEXT:\n{context}"
        
        body = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": req.max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}]
        }).encode()
        
        try:
            http_req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=body,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
            )
            resp = urllib.request.urlopen(http_req, timeout=180)
            data = json.loads(resp.read())
            text = data.get("content", [{}])[0].get("text", "").strip()
            return {"success": True, "response": text, "usage": data.get("usage", {})}
        except urllib.error.HTTPError as e:
            return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Run negotiation in executor
    loop = asyncio.get_event_loop()
    success, result = await loop.run_in_executor(
        None,
        lambda: negotiate_request(
            project=req.project,
            instruction=optimized_prompt,  # Use OPTIMIZED prompt
            call_claude_fn=call_claude_fn,
            context=full_context,
            max_retries=3
        )
    )
    
    if success:
        tasks = result.get("tasks", [])
        return {
            "success": True,
            "text": result.get("raw_response", ""),
            "tasks": tasks,
            "task_count": len(tasks),
            "usage": result.get("usage", {}),
            "attempts": len(result.get("attempts", [])),
            "lint_report": {
                "score": lint_report["score"],
                "issue_count": lint_report["issue_count"],
                "optimized": optimized_prompt != req.message
            },
            "context_injected": {
                "version_info": bool(version_context),
                "console_errors": len(_console_errors) if _console_errors else 0,
                "bugfixes": len(_known_bugfixes) if _known_bugfixes else 0
            }
        }
    
    # Handle failure
    return {
        "success": False,
        "error": result.get("error", "Unknown error"),
        "error_type": result.get("error_type"),
        "attempts": len(result.get("attempts", [])),
        "split_required": result.get("split_required", False),
        "parts": result.get("parts", []),
        "lint_report": {
            "score": lint_report["score"],
            "issue_count": lint_report["issue_count"]
        }
    }

# ============================================================
# GITHUB (via orchestrator)
# ============================================================

@app.get("/api/github/status")
async def github_status():
    """Check GitHub configuration status."""
    
    token = _get_token()
    if not token:
        return {"configured": False, "error": "No GitHub token"}
    
    # Get chat-module version if exists
    chat_module_version = None
    if "chat-module" in REPOS:
        try:
            import urllib.request
            url = f"https://api.github.com/repos/{REPOS['chat-module']}/releases/latest"
            req = urllib.request.Request(url, headers={"User-Agent": "LocalAgent"})
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            chat_module_version = data.get("tag_name", "").lstrip("v")
        except:
            chat_module_version = "?"
    
    return {
        "configured": True,
        "valid": True,
        "user": "THEMiS-eng",
        "repos": REPOS,
        "service_repo": REPOS.get("service"),
        "dashboard_repo": REPOS.get("dashboard"),
        "chat_module_repo": REPOS.get("chat-module"),
        "service_version": get_service_version(),
        "dashboard_version": get_dashboard_version(),
        "chat_module_version": chat_module_version
    }

@app.get("/api/github/releases/{owner}/{repo}")
async def get_releases(owner: str, repo: str, limit: int = Query(10)):
    """Get releases from GitHub repo."""
    
    # Temporarily set repo for this request
    original = get_repo_config()
    try:
        set_repo_url(f"https://github.com/{owner}/{repo}")
        releases = list_releases(limit=limit)
        return {"releases": releases}
    finally:
        if original.get("owner_repo"):
            set_repo_url(f"https://github.com/{original['owner_repo']}")


@app.get("/api/github/version/{owner}/{repo}")
async def get_latest_version(owner: str, repo: str):
    """Get latest version from GitHub repo releases."""
    import urllib.request
    import urllib.error
    
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "LocalAgent"})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        return {
            "version": data.get("tag_name", "unknown"),
            "name": data.get("name", ""),
            "published_at": data.get("published_at", ""),
            "url": data.get("html_url", "")
        }
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"version": "v0.0.0", "error": "No releases found"}
        return {"version": "unknown", "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"version": "unknown", "error": str(e)}
        if original.get("url"):
            set_repo_url(original["url"])

@app.post("/api/github/sync")
async def github_sync_endpoint(data: Dict[str, Any]):
    """Sync project to GitHub via orchestrator."""
    
    project = data.get("project", DEFAULT_PROJECT)
    repo_name = data.get("repo_name")
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: github_sync(project, repo_name)
    )
    return result

# ============================================================
# SNAPSHOTS (ENV003, ENV014 - Snapshot before destructive)
# ============================================================

@app.post("/api/snapshots")
async def create_snapshot(data: Dict[str, Any]):
    """Create a snapshot before destructive operations."""
    
    project = data.get("project", DEFAULT_PROJECT)
    label = data.get("label", "manual")
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: _create_snapshot(project, label)
    )
    return {"success": True, "snapshot": result}

@app.get("/api/snapshots/verify")
async def verify_snapshot_exists(project: str = Query(DEFAULT_PROJECT)):
    """ENV014: Verify snapshot exists before allowing destructive action."""
    from datetime import datetime, timedelta
    
    snapshots = _list_snapshots(project, 1)
    
    if not snapshots:
        return {
            "exists": False,
            "can_proceed": False,
            "error": "ENV014: No snapshot exists. Create snapshot before destructive action."
        }
    
    # Check if snapshot is recent (within 1 hour)
    latest = snapshots[0]
    # Assuming snapshot has timestamp
    return {
        "exists": True,
        "can_proceed": True,
        "latest_snapshot": latest
    }

@app.post("/api/snapshots/validate-action")
async def validate_action_with_snapshot(data: Dict[str, Any]):
    """ENV003/ENV014: Validate action is allowed (requires snapshot for destructive ops)."""
    
    action = data.get("action", "")
    context = data.get("context", {})
    project = data.get("project", DEFAULT_PROJECT)
    
    destructive_actions = ["delete", "modify", "overwrite", "remove", "deploy"]
    
    # Check if destructive
    is_destructive = any(d in action.lower() for d in destructive_actions)
    
    if is_destructive:
        snapshots = _list_snapshots(project, 1)
        if not snapshots:
            return {
                "valid": False,
                "reason": "ENV014: Destructive action requires snapshot first",
                "action": action,
                "requires_snapshot": True
            }
    
    # Standard constraint validation
    is_valid, violations = validate_action(action, context)
    
    return {
        "valid": is_valid,
        "violations": violations,
        "action": action,
        "is_destructive": is_destructive
    }

# ============================================================
# VERSION CONTEXT INJECTION (ENV015)
# ============================================================

async def get_version_context_for_claude() -> str:
    """
    ENV012/ENV015: Get version context to inject into every Claude call.
    
    CRITICAL FLOW:
    1. Service Worker fetches CURRENT version from GitHub (localagent-service)
    2. Service Worker tells Claude: "BUILD: v{current}"
    3. Claude creates files for this version
    4. After Claude response, Service Worker bumps to v{current+1} and pushes
    
    This ensures Claude knows EXACTLY what version it is building for.
    """
    
    try:
        # Get CURRENT version from GitHub releases (ENV012)
        current_version = get_service_version()  # e.g., "3.0.34"
        
        # Parse version components
        parts = current_version.split(".")
        if len(parts) == 3:
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        else:
            major, minor, patch = 0, 0, 0
        
        next_patch = f"{major}.{minor}.{patch + 1}"
        next_minor = f"{major}.{minor + 1}.0"
        next_major = f"{major + 1}.0.0"
        
        lines = [
            "=" * 60,
            "BUILD VERSION INFO (ENV012/ENV015) - FROM GITHUB",
            "=" * 60,
            f"CURRENT VERSION: v{current_version}",
            f"NEXT PATCH: v{next_patch}",
            f"NEXT MINOR: v{next_minor}",
            f"NEXT MAJOR: v{next_major}",
            f"REPO: {REPOS['service']}",
            "=" * 60,
            "INSTRUCTION: When creating/modifying files, use CURRENT version.",
            "Service Worker will bump version AFTER your response.",
            "=" * 60
        ]
        
        return "\n".join(lines)
    except Exception as e:
        return f"BUILD VERSION INFO (ENV012/ENV015):\n- Error fetching from GitHub: {e}\n- Fallback: use v0.0.1"

# ============================================================
# KNOWN BUGFIXES TRACKING (requires git commit)
# ============================================================

_known_bugfixes: List[Dict] = []

@app.post("/api/bugfixes/register")
async def register_bugfix(data: Dict[str, Any]):
    """
    Register a known bugfix to prevent regression.
    
    REQUIRED: Must include git commit reference.
    Bugfixes without commits are rejected - ensures proper tracking.
    
    Flow:
    1. Error in backlog
    2. Snapshot BEFORE (ENV003)
    3. Fix applied
    4. Snapshot AFTER
    5. Git commit with version (ENV004)
    6. Register bugfix HERE with commit SHA
    """
    commit_sha = data.get("commit_sha")
    backlog_id = data.get("backlog_id")
    
    if not commit_sha:
        return {
            "success": False, 
            "error": "commit_sha required - bugfixes must be linked to git commits"
        }
    
    bugfix = {
        "id": f"BF{len(_known_bugfixes)+1:03d}",
        "description": data.get("description", ""),
        "version_fixed": data.get("version", ""),
        "commit_sha": commit_sha,
        "backlog_id": backlog_id,
        "timestamp": datetime.now().isoformat()
    }
    _known_bugfixes.append(bugfix)
    
    # Mark backlog item as done if provided
    if backlog_id:
        from ..engine.tracking import complete_backlog_item
        try:
            complete_backlog_item(DEFAULT_PROJECT, backlog_id)
        except:
            pass
    
    logger.info(f"Bugfix registered: {bugfix['id']} @ {commit_sha[:8]}")
    return {"success": True, "bugfix": bugfix}

@app.get("/api/bugfixes")
async def get_bugfixes():
    """Get known bugfixes."""
    return {"bugfixes": _known_bugfixes}

def get_bugfixes_context() -> str:
    """Get bugfixes context for Claude."""
    if not _known_bugfixes:
        return ""
    
    lines = ["KNOWN BUGFIXES (do not regress):"]
    for bf in _known_bugfixes[-10:]:
        commit = bf.get('commit_sha', 'N/A')[:8]
        lines.append(f"- [{bf['id']}] {bf['description']} (v{bf['version_fixed']} @ {commit})")
    return "\n".join(lines)

# ============================================================
# VERSION VALIDATION (ENV012 - No Version Guessing)
# ============================================================

def _parse_version(v: str) -> tuple:
    """Parse version string to tuple (major, minor, patch)."""
    import re
    match = re.match(r'v?(\d+)\.(\d+)\.(\d+)', v)
    if match:
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return (0, 0, 0)

def _version_to_str(v: tuple) -> str:
    """Convert version tuple to string."""
    return f"{v[0]}.{v[1]}.{v[2]}"

@app.get("/api/version/next")
async def get_next_version(repo: str = Query("THEMiS-eng/themis-qs")):
    """
    ENV012: Get next valid version from GitHub.
    Claude MUST call this before any release.
    """
    
    # Set repo
    original = get_repo_config()
    try:
        set_repo_url(f"https://github.com/{repo}")
        releases = list_releases(limit=20)
        
        if not releases:
            return {
                "current": None,
                "next_patch": "0.0.1",
                "next_minor": "0.1.0",
                "next_major": "1.0.0",
                "existing_tags": []
            }
        
        # Get all existing tags
        existing_tags = [r.get("tag", "") for r in releases]
        
        # Find highest version
        versions = [_parse_version(t) for t in existing_tags]
        current = max(versions) if versions else (0, 0, 0)
        
        return {
            "current": _version_to_str(current),
            "next_patch": _version_to_str((current[0], current[1], current[2] + 1)),
            "next_minor": _version_to_str((current[0], current[1] + 1, 0)),
            "next_major": _version_to_str((current[0] + 1, 0, 0)),
            "existing_tags": existing_tags[:10]
        }
    finally:
        if original.get("url"):
            set_repo_url(original["url"])

@app.post("/api/version/validate")
async def validate_version(data: Dict[str, Any]):
    """
    ENV012: Validate proposed version before release.
    Returns suggested version if invalid.
    """
    proposed = data.get("version", "")
    repo = data.get("repo", "THEMiS-eng/themis-qs")
    
    if not proposed:
        raise HTTPException(400, "version required")
    
    
    original = get_repo_config()
    try:
        set_repo_url(f"https://github.com/{repo}")
        releases = list_releases(limit=50)
        
        existing_tags = [r.get("tag", "") for r in releases]
        proposed_clean = proposed.lstrip("v")
        proposed_tag = f"v{proposed_clean}"
        
        # Check duplicate
        if proposed_tag in existing_tags or proposed_clean in [t.lstrip("v") for t in existing_tags]:
            versions = [_parse_version(t) for t in existing_tags]
            current = max(versions) if versions else (0, 0, 0)
            suggested = _version_to_str((current[0], current[1], current[2] + 1))
            
            return {
                "valid": False,
                "reason": f"Version {proposed_tag} already exists",
                "proposed": proposed,
                "suggested_version": suggested,
                "current_version": _version_to_str(current)
            }
        
        # Check regression
        proposed_tuple = _parse_version(proposed)
        versions = [_parse_version(t) for t in existing_tags]
        current = max(versions) if versions else (0, 0, 0)
        
        if proposed_tuple <= current:
            suggested = _version_to_str((current[0], current[1], current[2] + 1))
            return {
                "valid": False,
                "reason": f"Version {proposed} is not greater than current {_version_to_str(current)}",
                "proposed": proposed,
                "suggested_version": suggested,
                "current_version": _version_to_str(current)
            }
        
        return {
            "valid": True,
            "proposed": proposed,
            "current_version": _version_to_str(current)
        }
    finally:
        if original.get("url"):
            set_repo_url(original["url"])

# ============================================================
# DEPLOY (via release_publisher) - WITH ENV012 VALIDATION
# ============================================================

@app.post("/api/deploy/release")
async def deploy_release(data: Dict[str, Any]):
    """
    Create GitHub release with asset upload.
    
    ENV012: Validates version BEFORE creating release.
    Rejects duplicates and regressions with suggested_version.
    """
    
    tag = data.get("tag")
    name = data.get("name", tag)
    body = data.get("body", "")
    file_path = data.get("file_path")
    file_name = data.get("file_name")
    repo = data.get("repo", "THEMiS-eng/themis-qs")
    force = data.get("force", False)
    skip_validation = data.get("skip_validation", False)
    
    if not tag:
        raise HTTPException(400, "tag required")
    
    # Set repo
    if repo:
        set_repo_url(f"https://github.com/{repo}")
    
    # ENV012: VALIDATE VERSION FIRST (unless forced or skipped)
    if not force and not skip_validation:
        original = get_repo_config()
        try:
            releases = list_releases(limit=50)
            existing_tags = [r.get("tag", "") for r in releases]
            
            tag_clean = tag.lstrip("v")
            tag_full = f"v{tag_clean}"
            
            # Check duplicate
            if tag_full in existing_tags or tag_clean in [t.lstrip("v") for t in existing_tags]:
                versions = [_parse_version(t) for t in existing_tags]
                current = max(versions) if versions else (0, 0, 0)
                suggested = f"v{_version_to_str((current[0], current[1], current[2] + 1))}"
                
                return {
                    "success": False,
                    "error": f"Version {tag} already exists on GitHub",
                    "suggested_version": suggested,
                    "validation": {
                        "valid": False,
                        "reason": "duplicate_tag",
                        "existing_tags": existing_tags[:5]
                    }
                }
            
            # Check regression
            proposed_tuple = _parse_version(tag)
            versions = [_parse_version(t) for t in existing_tags]
            current = max(versions) if versions else (0, 0, 0)
            
            if proposed_tuple <= current and versions:
                suggested = f"v{_version_to_str((current[0], current[1], current[2] + 1))}"
                return {
                    "success": False,
                    "error": f"Version {tag} is not greater than current v{_version_to_str(current)}",
                    "suggested_version": suggested,
                    "validation": {
                        "valid": False,
                        "reason": "version_regression"
                    }
                }
        finally:
            pass  # Repo already set
    
    # Validate file if provided
    fp = None
    if file_path:
        fp = Path(file_path).expanduser()
        if not fp.exists():
            raise HTTPException(404, f"File not found: {file_path}")
    
    # Create release
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: create_release(
            version=tag.lstrip("v"),
            zip_path=str(fp) if fp else None,
            release_notes=body,
            force=force
        )
    )
    return result

# ============================================================
# LINT (using roadmap/prompt_optimizer)
# ============================================================

@app.post("/api/lint")
async def lint_endpoint(data: Dict[str, Any]):
    """
    Lint a prompt before sending to Claude.
    Uses existing prompt_optimizer module.
    """
    
    prompt = data.get("prompt", "")
    if not prompt:
        raise HTTPException(400, "prompt required")
    
    result = lint_prompt(prompt)
    return result

@app.post("/api/lint/optimize")
async def optimize_endpoint(data: Dict[str, Any]):
    """
    Optimize a prompt using linter.
    Returns both original and optimized versions.
    """
    
    prompt = data.get("prompt", "")
    if not prompt:
        raise HTTPException(400, "prompt required")
    
    report = lint_prompt(prompt)
    optimized = optimize_prompt(prompt)
    
    return {
        "original": prompt,
        "optimized": optimized,
        "was_modified": prompt != optimized,
        "report": report
    }

@app.get("/api/lint/summary")
async def lint_summary_endpoint(prompt: str = Query(...)):
    """Get human-readable lint summary."""
    
    summary = get_lint_summary(prompt)
    return {"summary": summary}

# ============================================================
# LEARNING (via core/learning)
# ============================================================

@app.get("/api/learning/report")
async def learning_report(project: str = Query(DEFAULT_PROJECT)):
    """Get learning report for project."""
    
    errors = load_learned_errors(project)
    context = get_error_context_for_retry(project)
    
    return {
        "project": project,
        "error_count": len(errors.get("errors", [])),
        "patterns": errors.get("patterns", {}),
        "dodges": errors.get("dodges", {}),
        "context_for_retry": context
    }

@app.get("/api/learning/patterns")
async def learning_patterns(project: str = Query(DEFAULT_PROJECT)):
    """Get learned error patterns."""
    
    errors = load_learned_errors(project)
    return {"patterns": errors.get("patterns", {})}

@app.post("/api/learning/error")
async def log_learning_error(data: Dict[str, Any]):
    """Log an error for learning."""
    
    project = data.get("project", DEFAULT_PROJECT)
    error_type = data.get("error_type", "unknown")
    message = data.get("message", "")
    context = data.get("context", {})
    
    learn_from_error(project, error_type, message, context)
    return {"success": True}

# ============================================================
# CONSTRAINTS (via core/constraints)
# ============================================================

@app.post("/api/constraints/validate")
async def validate_constraint(data: Dict[str, Any]):
    """Validate an action against constraints."""
    
    action = data.get("action", "")
    context = data.get("context", {})
    
    is_valid, violations = validate_action(action, context)
    return {"valid": is_valid, "violations": violations}

# ============================================================
# UPDATE (via core/release_listener)
# ============================================================

@app.get("/api/update/check")
async def check_update(app_id: str = Query("localagent")):
    """Check for updates from GitHub."""
    
    result = check_for_update()
    return result

@app.post("/api/update/install-from-github")
async def install_from_github_endpoint():
    """Install latest release from GitHub."""
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, install_from_github)
    return result

# ============================================================
# DEBUG - CONSOLE ERROR CAPTURE FOR SELF-CORRECTION
# ============================================================

# In-memory store for console errors (FE/BE)
_console_errors: List[Dict] = []
MAX_CONSOLE_ERRORS = 50

# Console errors now queued to backlog, not directly injected
# See /api/debug/console-error endpoint

def get_console_errors_for_claude() -> str:
    """
    DEPRECATED: Console errors now go through backlog.
    This function returns empty - errors are handled via proper flow:
    backlog -> snapshot -> fix -> snapshot -> git commit -> bugfix
    """
    return ""

@app.post("/api/debug/console-error")
async def capture_console_error(data: Dict[str, Any]):
    """
    Capture console error from FE or BE.
    
    Instead of direct injection to Claude, errors are queued
    to the dashboard backlog as high-priority TODO items.
    
    Flow:
    1. Error captured here
    2. Added to backlog as TODO
    3. User/orchestrator picks from backlog
    4. Snapshot BEFORE fix (ENV003)
    5. Claude proposes fix via negotiator
    6. Fix executed
    7. Snapshot AFTER fix
    8. Git commit with version increment (ENV004)
    9. Register bugfix (linked to commit)
    """
    
    error_entry = {
        "source": data.get("source", "unknown"),
        "message": data.get("message", ""),
        "file": data.get("file"),
        "line": data.get("line"),
        "column": data.get("col"),
        "stack": data.get("stack"),
        "timestamp": datetime.now().isoformat()
    }
    
    # Log to debugger for persistence
    log_error(error_entry, source=error_entry["source"])
    
    # Queue to backlog as high-priority TODO
    title = f"[{error_entry['source'].upper()}] {error_entry['message'][:80]}"
    if error_entry.get("file") and error_entry.get("line"):
        title += f" @ {error_entry['file']}:{error_entry['line']}"
    
    backlog_id = add_backlog_item(
        DEFAULT_PROJECT,
        title,
        priority="high",
        metadata={
            "type": "console_error",
            "error": error_entry
        }
    )
    
    logger.warning(f"Console error queued to backlog [{backlog_id}]: {error_entry['message'][:50]}")
    
    return {
        "success": True, 
        "queued": True,
        "backlog_id": backlog_id,
        "message": "Error queued to backlog for proper fix flow"
    }


@app.get("/api/debug/console-errors")
async def get_console_errors():
    """
    Get console errors from backlog.
    Errors are now queued as backlog items, not stored separately.
    """
    backlog = get_backlog(DEFAULT_PROJECT)
    
    # Filter console_error type items
    console_errors = [
        b for b in backlog 
        if b.get("metadata", {}).get("type") == "console_error"
    ]
    
    return {
        "errors": [b.get("metadata", {}).get("error", {}) for b in console_errors],
        "count": len(console_errors),
        "backlog_ids": [b.get("id") for b in console_errors]
    }

@app.post("/api/debug/console-errors/clear")
async def clear_console_errors():
    """Clear console errors after fix is applied."""
    global _console_errors
    count = len(_console_errors)
    _console_errors = []
    return {"success": True, "cleared": count}

@app.post("/api/debug/log")
async def debug_log(data: Dict[str, Any]):
    """Log debug info."""
    
    error_id = log_error(data, source=data.get("source", "api"))
    return {"success": True, "error_id": error_id}

@app.get("/api/debug/errors")
async def get_debug_errors():
    """Get pending debug errors."""
    return {"errors": get_errors()}

@app.post("/api/debug/error")
async def post_debug_error(data: Dict[str, Any]):
    """
    Receive error from dashboard/client.
    Auto-checks for learned fixes and triggers analysis if needed.
    """
    error_data = {
        "message": data.get("message", "Unknown error"),
        "source": data.get("source", "unknown"),
        "level": data.get("level", "error"),
        "timestamp": data.get("timestamp"),
        "line": data.get("line"),
        "file": data.get("file"),
        "stack": data.get("stack"),
    }
    
    # Log the error (also checks for known fixes)
    error_id = log_error(error_data, source=data.get("source", "js"))
    
    # Check if we have a learned fix
    from ..core.debugger import _load_debug_log
    debug_data = _load_debug_log()
    error_entry = None
    for e in debug_data["errors"]:
        if e["id"] == error_id:
            error_entry = e
            break
    
    known_fix = error_entry.get("known_fix") if error_entry else None
    
    # Broadcast to WebSocket clients
    await ws_manager.broadcast({
        "type": "error",
        "error": error_data,
        "error_id": error_id,
        "known_fix": known_fix,
        "auto_fixed": known_fix is not None
    })
    
    # If auto-fix is enabled and no known fix, trigger analysis in background
    auto_analyze = data.get("auto_analyze", False)
    if auto_analyze and not known_fix:
        asyncio.create_task(auto_fix_error(error_id))
    
    return {
        "success": True, 
        "error_id": error_id,
        "known_fix": known_fix,
        "auto_fixed": known_fix is not None
    }

@app.get("/api/debug/report")
async def debug_report():
    """Get formatted debug report for Claude."""
    from .debugger import auto_debug_check
    report = auto_debug_check()
    return {"has_errors": bool(report), "report": report or "No errors"}

@app.get("/api/debug/stats")
async def debug_stats():
    """Get debugging statistics."""
    return get_debug_stats()

@app.post("/api/debug/auto-fix/{error_id}")
async def auto_fix_endpoint(error_id: str):
    """
    Trigger auto-fix pipeline for an error.
    1. Check for learned fix
    2. Analyze with Claude
    3. Create GitHub issue
    """
    result = await auto_fix_error(error_id)
    
    # Broadcast result to dashboard
    await ws_manager.broadcast({
        "type": "auto_fix_result",
        "error_id": error_id,
        "result": result
    })
    
    return result

@app.post("/api/debug/analyze/{error_id}")
async def analyze_error_endpoint(error_id: str):
    """Send error to Claude for analysis."""
    result = await analyze_error_with_claude(error_id)
    return result

@app.post("/api/debug/github-issue/{error_id}")
async def create_issue_endpoint(error_id: str, repo_type: str = Query("service")):
    """Create GitHub issue for an error."""
    result = create_github_issue_for_error(error_id, repo_type)
    return result

@app.post("/api/debug/learn")
async def learn_fix_endpoint(data: Dict[str, Any]):
    """Learn from a successful fix."""
    error_id = data.get("error_id")
    fix_description = data.get("fix_description")
    fix_code = data.get("fix_code")
    
    if not error_id or not fix_description:
        raise HTTPException(status_code=400, detail="error_id and fix_description required")
    
    learn_from_fix(error_id, fix_description, fix_code)
    
    return {"success": True, "learned": True}

@app.get("/api/debug/context")
async def get_debug_context():
    """Get error context for Claude system prompt."""
    return {"context": get_error_context_for_claude()}

# ============================================================
# APPS
# ============================================================

def _get_app_dir(app_id: str) -> Path:
    p = APPS_DIR / app_id
    p.mkdir(parents=True, exist_ok=True)
    return p

@app.get("/api/app")
async def get_app(app_id: str = Query("themis")):
    """Get app info."""
    app_dir = _get_app_dir(app_id)
    registered = (app_dir / "registered").exists()
    return {
        "app_id": app_id,
        "registered": registered,
        "path": str(app_dir)
    }

@app.post("/api/apps/register")
async def register_app(data: Dict[str, Any]):
    """Register an app with the service worker."""
    app_id = data.get("app_id", "unknown")
    info = data.get("info", {})
    
    app_dir = _get_app_dir(app_id)
    (app_dir / "registered").write_text(datetime.now().isoformat())
    (app_dir / "info.json").write_text(json.dumps(info, indent=2))
    
    return {"success": True, "app_id": app_id}

@app.get("/api/apps")
async def list_apps():
    """List registered apps."""
    if not APPS_DIR.exists():
        return {"apps": []}
    return {"apps": [d.name for d in APPS_DIR.iterdir() if d.is_dir()]}

# ============================================================
# CONFIG
# ============================================================

@app.get("/api/config/api-key/status")
async def api_key_status():
    return {"configured": get_api_key() is not None}

@app.post("/api/config/api-key")
async def set_api_key_endpoint(data: Dict[str, str]):
    set_api_key(data.get("key", ""))
    return {"success": True}

# ============================================================
# RUN
# ============================================================

def _kill_existing_process():
    """Kill any process using our port before starting."""
    import subprocess
    import sys
    
    try:
        if sys.platform == "darwin":  # macOS
            result = subprocess.run(
                ["lsof", "-ti", f":{PORT}"],
                capture_output=True, text=True, timeout=5
            )
        else:  # Linux
            result = subprocess.run(
                ["fuser", f"{PORT}/tcp"],
                capture_output=True, text=True, timeout=5
            )
        
        pids = result.stdout.strip().split()
        for pid in pids:
            if pid.isdigit():
                logger.info(f"Killing existing process on port {PORT}: PID {pid}")
                subprocess.run(["kill", "-9", pid], timeout=5)
        
        if pids:
            import time
            time.sleep(0.5)
            
    except Exception as e:
        logger.debug(f"Port check: {e}")


# ============================================================
# GITHUB PUSH (via Service Worker API)
# ============================================================

@app.post("/api/github/push")
async def github_push_endpoint(data: Dict[str, Any]):
    """Push to GitHub via Service Worker with auto-generated release notes."""
    
    repo_type = data.get("repo_type") or data.get("target")  # Accept both "repo_type" and "target"
    version = data.get("version")
    message = data.get("message")
    create_release = data.get("release") or data.get("create_release", True)
    custom_notes = data.get("notes")  # Allow custom release notes
    todo_ids = data.get("todo_ids", [])  # TODO items to mark done when tests pass
    
    # Get version from VERSION file if not provided
    if not version:
        from pathlib import Path
        version_file = Path.home() / "localagent_v3" / "VERSION"
        if version_file.exists():
            version = version_file.read_text().strip()
        else:
            version = "3.0.0"
    
    # Generate release notes if not provided
    release_notes = custom_notes
    if not release_notes and create_release:
        from ..engine.tracking import generate_release_notes, add_changelog_entry
        release_notes = generate_release_notes(DEFAULT_PROJECT, version)
        # Save to changelog
        add_changelog_entry(DEFAULT_PROJECT, version, release_notes)
    
    loop = asyncio.get_event_loop()
    
    if repo_type == "all":
        from pathlib import Path
        from ..connectors.github import github_push_all
        service_dir = str(Path.home() / "localagent_v3")
        dashboard_dir = str(Path.home() / "localagent_v3" / "dashboard")
        result = await loop.run_in_executor(
            None,
            lambda: github_push_all(service_dir, dashboard_dir, version, message, create_release)
        )
    else:
        from pathlib import Path
        if repo_type == "dashboard":
            source_dir = str(Path.home() / "localagent_v3" / "dashboard")
        elif repo_type == "chat-module":
            source_dir = str(Path.home() / "localagent_v3" / "modules" / "ai-chat-module-pro")
        else:
            source_dir = str(Path.home() / "localagent_v3")
        result = await loop.run_in_executor(
            None,
            lambda: push_to_github(source_dir, repo_type or "service", message, version, create_release, release_notes)
        )
    
    # Track pending TODO completion (will be marked done when GitHub tests pass)
    if result.get("success") and todo_ids:
        from ..engine.tracking import track_pending_release
        track_pending_release(DEFAULT_PROJECT, version, todo_ids, result.get("commit_sha"))
    
    # Add release notes to result
    if release_notes:
        result["release_notes"] = release_notes
    
    return result


@app.get("/api/github/workflow-status")
async def check_workflow_status():
    """Check GitHub Actions workflow status and mark TODOs as done if tests passed."""
    from ..engine.tracking import get_pending_releases, complete_pending_release
    from ..connectors.github import get_workflow_status, REPOS
    
    pending = get_pending_releases(DEFAULT_PROJECT)
    completed = []
    
    for release in pending:
        version = release.get("version")
        todo_ids = release.get("todo_ids", [])
        
        # Check workflow status on GitHub
        status = get_workflow_status(REPOS.get("service", ""), release.get("commit_sha"))
        
        if status == "success":
            # Mark TODOs as done
            complete_pending_release(DEFAULT_PROJECT, version, todo_ids)
            completed.append({"version": version, "todos": todo_ids, "status": "completed"})
        elif status == "failure":
            # Mark as failed but don't complete TODOs
            complete_pending_release(DEFAULT_PROJECT, version, [], failed=True)
            completed.append({"version": version, "todos": todo_ids, "status": "failed"})
    
    return {"checked": len(pending), "completed": completed}


@app.post("/api/changelog/sync-from-github")
async def sync_changelog_from_github():
    """Sync changelog from GitHub releases."""
    from ..connectors.github import REPOS, _api_request, GITHUB_API
    from ..engine.tracking import add_changelog_entry, get_version_changelog
    
    repo = REPOS.get("service", "")
    if not repo:
        return {"success": False, "error": "No service repo configured"}
    
    # Get releases from GitHub
    url = f"{GITHUB_API}/repos/{repo}/releases"
    result = _api_request("GET", url)
    
    if "error" in result:
        return {"success": False, "error": result["error"]}
    
    releases = result if isinstance(result, list) else []
    existing = {c.get("version") for c in get_version_changelog(DEFAULT_PROJECT)}
    
    added = []
    for release in releases:
        version = release.get("tag_name", "").lstrip("v")
        if version and version not in existing:
            notes = release.get("body") or f"## v{version}\n\nReleased from GitHub"
            add_changelog_entry(DEFAULT_PROJECT, version, notes)
            added.append(version)
    
    return {"success": True, "added": added, "total": len(releases)}


# ============================================================
# MODULE MANAGEMENT (via Service Worker)
# ============================================================

@app.get("/api/modules")
async def list_modules():
    """List available modules."""
    from pathlib import Path
    
    modules_dir = Path.home() / "localagent_v3" / "modules"
    if not modules_dir.exists():
        return {"modules": [], "count": 0}
    
    modules = []
    for d in modules_dir.iterdir():
        if d.is_dir():
            pkg_file = d / "package.json"
            info = {"name": d.name, "path": str(d)}
            
            if pkg_file.exists():
                try:
                    pkg = json.loads(pkg_file.read_text())
                    info["version"] = pkg.get("version", "unknown")
                    info["description"] = pkg.get("description", "")
                except:
                    pass
            
            modules.append(info)
    
    return {"modules": modules, "count": len(modules)}


@app.post("/api/modules/init")
async def init_module_repo(data: Dict[str, Any]):
    """
    Initialize a module as a GitHub repository.
    
    This is the ORCHESTRATOR handling module creation:
    1. Validate module exists locally
    2. CREATE GitHub repo via API (if not exists)
    3. Initialize git repo locally
    4. Create initial commit
    5. Push to GitHub
    6. Create release
    """
    from pathlib import Path
    
    module_name = data.get("module")
    version = data.get("version", "1.0.0")
    description = data.get("description", "")
    private = data.get("private", False)
    
    if not module_name:
        return {"success": False, "error": "module name required"}
    
    modules_dir = Path.home() / "localagent_v3" / "modules"
    module_path = modules_dir / module_name
    
    if not module_path.exists():
        return {"success": False, "error": f"Module not found: {module_name}"}
    
    # Check if repo is configured in REPOS
    repo_key = None
    repo_full_name = None
    for key, repo in REPOS.items():
        if module_name in repo:
            repo_key = key
            repo_full_name = repo
            break
    
    if not repo_key:
        return {
            "success": False, 
            "error": f"No GitHub repo configured for {module_name}. Add to REPOS in github.py"
        }
    
    # Parse owner/repo
    parts = repo_full_name.split("/")
    if len(parts) != 2:
        return {"success": False, "error": f"Invalid repo format: {repo_full_name}"}
    
    owner, repo_name = parts
    
    logger.info(f"Initializing module repo: {module_name} -> {repo_full_name}")
    
    loop = asyncio.get_event_loop()
    
    # Step 1: Check if repo exists
    repo_exists = await loop.run_in_executor(None, lambda: github_repo_exists(owner, repo_name))
    
    actual_repo_full_name = repo_full_name
    
    if not repo_exists:
        logger.info(f"Creating GitHub repo: {repo_full_name}")
        
        # Get description from package.json if not provided
        if not description:
            pkg_file = module_path / "package.json"
            if pkg_file.exists():
                try:
                    pkg = json.loads(pkg_file.read_text())
                    description = pkg.get("description", f"{module_name} module")
                except:
                    description = f"{module_name} module"
        
        create_result = await loop.run_in_executor(
            None,
            lambda: github_create_repo(repo_name, description, private, owner)
        )
        
        if not create_result.get("success"):
            return {
                "success": False,
                "error": f"Failed to create repo: {create_result.get('error')}",
                "step": "create_repo"
            }
        
        # Check if repo was created under different owner (user fallback)
        if create_result.get("full_name"):
            actual_repo_full_name = create_result.get("full_name")
            logger.info(f"Repo created: {actual_repo_full_name}")
        
        logger.info(f"GitHub repo created: {create_result.get('url')}")
    else:
        logger.info(f"GitHub repo already exists: {repo_full_name}")
    
    # Step 2: Push to GitHub (use actual repo name which might differ if fallback to user)
    # We need to push directly since repo_key might point to wrong repo now
    token = _get_token()
    if not token:
        return {"success": False, "error": "No GitHub token", "step": "push"}
    
    import subprocess
    
    actions = []
    try:
        # Init git if needed
        git_dir = module_path / ".git"
        if not git_dir.exists():
            subprocess.run(["git", "init"], cwd=module_path, capture_output=True, check=True)
            actions.append("git init")
        
        # Set remote
        remote_url = f"https://{token}@github.com/{actual_repo_full_name}.git"
        result = subprocess.run(["git", "remote", "-v"], cwd=module_path, capture_output=True, text=True)
        
        if "origin" in result.stdout:
            subprocess.run(["git", "remote", "set-url", "origin", remote_url], cwd=module_path, capture_output=True)
            actions.append("updated remote")
        else:
            subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=module_path, capture_output=True)
            actions.append("added remote")
        
        # Add and commit
        subprocess.run(["git", "add", "-A"], cwd=module_path, capture_output=True, check=True)
        actions.append("git add")
        
        result = subprocess.run(
            ["git", "commit", "-m", f"Initial release v{version}", "--allow-empty"],
            cwd=module_path, capture_output=True, text=True
        )
        if result.returncode == 0:
            actions.append("committed")
        
        # Push
        subprocess.run(["git", "branch", "-M", "main"], cwd=module_path, capture_output=True)
        result = subprocess.run(
            ["git", "push", "-u", "origin", "main", "--force"],
            cwd=module_path, capture_output=True, text=True, timeout=120
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Push failed: {result.stderr}",
                "step": "push",
                "actions": actions
            }
        
        actions.append("pushed")
        
        # Tag and release
        tag = f"v{version}"
        subprocess.run(["git", "tag", "-f", tag], cwd=module_path, capture_output=True)
        subprocess.run(["git", "push", "origin", tag, "--force"], cwd=module_path, capture_output=True)
        actions.append(f"tagged {tag}")
        
        # Create release via API
        release_data = {
            "tag_name": tag,
            "name": f"{module_name} {tag}",
            "body": f"Initial release of {module_name}",
            "draft": False,
            "prerelease": False
        }
        release_url = f"{GITHUB_API}/repos/{actual_repo_full_name}/releases"
        release_result = _api_request("POST", release_url, release_data, token)
        
        if release_result.get("html_url"):
            actions.append(f"release: {release_result.get('html_url')}")
        
        # Log release
        from ..engine.tracking import add_release_item
        add_release_item(
            DEFAULT_PROJECT,
            f"MOD-{module_name}",
            "MODULE",
            f"Initial release of {module_name}",
            version
        )
        
        return {
            "success": True,
            "module": module_name,
            "version": version,
            "repo": actual_repo_full_name,
            "repo_created": not repo_exists,
            "actions": actions
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "step": "push",
            "actions": actions
        }


@app.post("/api/modules/push")
async def push_module(data: Dict[str, Any]):
    """
    Push module update to GitHub.
    
    Flow:
    1. Validate module
    2. Bump version in package.json
    3. Commit changes
    4. Push to GitHub
    5. Create release
    6. Log to release notes
    """
    from pathlib import Path
    
    module_name = data.get("module")
    version = data.get("version")
    message = data.get("message", f"Update {module_name}")
    create_release = data.get("release", True)
    
    if not module_name:
        return {"success": False, "error": "module name required"}
    if not version:
        return {"success": False, "error": "version required"}
    
    modules_dir = Path.home() / "localagent_v3" / "modules"
    module_path = modules_dir / module_name
    
    if not module_path.exists():
        return {"success": False, "error": f"Module not found: {module_name}"}
    
    # Find repo key
    repo_key = None
    for key, repo in REPOS.items():
        if module_name in repo:
            repo_key = key
            break
    
    if not repo_key:
        return {"success": False, "error": f"No repo configured for {module_name}"}
    
    # Update package.json version
    pkg_file = module_path / "package.json"
    if pkg_file.exists():
        try:
            pkg = json.loads(pkg_file.read_text())
            pkg["version"] = version
            pkg_file.write_text(json.dumps(pkg, indent=2))
            logger.info(f"Updated {module_name}/package.json to v{version}")
        except Exception as e:
            logger.warning(f"Could not update package.json: {e}")
    
    # Push to GitHub
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: github_push(
            str(module_path),
            repo_key,
            message=message,
            version=version,
            create_release=create_release
        )
    )
    
    if result.get("success"):
        # Log release
        add_release_item(
            DEFAULT_PROJECT,
            f"MOD-{module_name}-v{version}",
            "MODULE",
            message,
            version
        )
    
    return {
        "success": result.get("success", False),
        "module": module_name,
        "version": version,
        "repo": REPOS.get(repo_key),
        "actions": result.get("actions", []),
        "error": result.get("error")
    }


@app.post("/api/update/install")
async def install_update_endpoint(data: Dict[str, Any]):
    """Install specific version from GitHub."""
    
    version = data.get("version")
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: install_from_github(version))
    return result


def run():
    _kill_existing_process()
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")

if __name__ == "__main__":
    run()
