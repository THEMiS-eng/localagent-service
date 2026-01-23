#!/usr/bin/env python3
"""
LocalAgent v3.0 - Service Worker Server
HTTP API on localhost:9999

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
from pydantic import BaseModel
import uvicorn

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("localagent")

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
VERSION = "3.0.22"

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
    from ..connectors.dashboard import set_project
    from ..engine.project import PROJECTS_DIR
    
    # Ensure project directory exists
    project_dir = PROJECTS_DIR / DEFAULT_PROJECT / "current"
    project_dir.mkdir(parents=True, exist_ok=True)
    
    set_project(DEFAULT_PROJECT)
    logger.info(f"LocalAgent v{VERSION} started on {HOST}:{PORT}")
    logger.info(f"Project: {DEFAULT_PROJECT}")
    logger.info(f"Outputs: {project_dir}")
    yield
    logger.info("LocalAgent shutting down")

app = FastAPI(title="LocalAgent Service Worker", version=VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ============================================================
# DASHBOARD (serves static HTML - decoupled from service worker)
# ============================================================

from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path

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

# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
async def health():
    from ..engine.project import PROJECTS_DIR, get_version as get_project_version
    from ..connectors.github import get_service_version, REPOS
    
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
    from ..engine.project import PROJECTS_DIR
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
    
    from ..engine.project import PROJECTS_DIR
    from ..connectors.dashboard import set_project
    
    project_dir = PROJECTS_DIR / project
    if not project_dir.exists():
        # Create it
        (project_dir / "current").mkdir(parents=True, exist_ok=True)
    
    DEFAULT_PROJECT = project
    set_project(project)
    logger.info(f"Project switched to: {project}")
    return {"success": True, "project": project}

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
    from ..connectors.dashboard import get_status as dash_status, set_project
    set_project(DEFAULT_PROJECT)
    return dash_status()

@app.get("/api/conversation")
async def get_conversation_endpoint(project: str = Query(default=None)):
    """Get conversation history."""
    from ..engine.tracking import get_conversation
    return get_conversation(project or DEFAULT_PROJECT)

@app.get("/api/backlog")
async def get_backlog_endpoint(project: str = Query(default=None)):
    """Get backlog items."""
    from ..engine.tracking import get_backlog
    return get_backlog(project or DEFAULT_PROJECT)

@app.get("/api/todo")
async def get_todo_endpoint(project: str = Query(default=None)):
    """Get TODO items."""
    from ..engine.tracking import get_todo
    return get_todo(project or DEFAULT_PROJECT)

@app.get("/api/changelog")
async def get_changelog_endpoint(project: str = Query(default=None)):
    """Get changelog."""
    from ..engine.tracking import get_changelog
    return get_changelog(project or DEFAULT_PROJECT)

@app.get("/api/errors")
async def get_errors_endpoint(project: str = Query(default=None)):
    """Get learned errors."""
    from ..core.learning import load_learned_errors
    return load_learned_errors(project or DEFAULT_PROJECT)

@app.get("/api/constraints")
async def get_constraints_endpoint():
    """Get all constraints."""
    from ..core.constraints import get_all_constraints
    return get_all_constraints()

@app.get("/api/snapshots")
async def get_snapshots_endpoint(project: str = Query(default=None)):
    """Get project snapshots."""
    from ..engine.project import list_snapshots
    snapshots = list_snapshots(project or DEFAULT_PROJECT)
    return {"snapshots": snapshots, "count": len(snapshots)}

@app.get("/api/outputs")
async def get_outputs_endpoint(project: str = Query(default=None)):
    """Get output files list."""
    from ..engine.tracking import get_output_files
    return get_output_files(project or DEFAULT_PROJECT)

from fastapi.responses import FileResponse

@app.get("/outputs/{filename:path}")
async def serve_output_file(filename: str, project: str = Query(default=None)):
    """Serve output file."""
    from ..engine.tracking import get_outputs_path
    filepath = get_outputs_path(project or DEFAULT_PROJECT) / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath)

@app.post("/api/chat")
async def chat_endpoint(data: Dict[str, Any]):
    """Handle chat message (dashboard compatible)."""
    from ..connectors.dashboard import handle_chat, set_project
    set_project(DEFAULT_PROJECT)
    return handle_chat(data.get("message", ""))

@app.post("/api/backlog/add")
async def add_backlog_endpoint(data: Dict[str, Any]):
    """Add backlog item."""
    from ..engine.tracking import add_backlog_item
    item_id = add_backlog_item(DEFAULT_PROJECT, data.get("title", ""), data.get("priority", "medium"))
    return {"id": item_id}

@app.post("/api/todo/add")
async def add_todo_endpoint(data: Dict[str, Any]):
    """Add TODO item."""
    from ..engine.tracking import add_todo_item
    item_id = add_todo_item(DEFAULT_PROJECT, data.get("title", ""), data.get("category", "todo"))
    return {"id": item_id}

@app.post("/api/todo/complete")
async def complete_todo_endpoint(data: Dict[str, Any]):
    """Mark TODO item as done."""
    from ..engine.tracking import toggle_todo
    item_id = data.get("id", "")
    success = toggle_todo(DEFAULT_PROJECT, item_id)
    return {"success": success, "id": item_id}

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
    from ..engine.tracking import get_todo
    from ..core.protocol import process_todo_with_protocol
    from ..connectors.llm import call_claude
    from ..connectors.github import REPOS
    
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
    from ..engine.tracking import get_todo
    
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
    from ..engine.tracking import get_todo
    
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
    from ..engine.tracking import clear_conversation
    clear_conversation(DEFAULT_PROJECT)
    return {"status": "cleared"}

@app.post("/api/outputs/delete")
async def delete_output_endpoint(data: Dict[str, Any]):
    """Delete output file."""
    from ..engine.tracking import delete_output_file
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
    from ..core.negotiator import negotiate_request
    from ..roadmap.prompt_optimizer import preprocess_for_negotiation, lint_prompt
    
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
    from ..core.constraints import get_all_constraints
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
    from ..core.release_publisher import get_github_token, verify_token, get_repo_config
    
    token = get_github_token()
    if not token:
        return {"configured": False, "error": "No GitHub token"}
    
    token_info = verify_token()
    repo_config = get_repo_config()
    
    return {
        "configured": True,
        "valid": token_info.get("valid", False),
        "user": token_info.get("user"),
        "repo": repo_config.get("owner_repo")
    }

@app.get("/api/github/releases/{owner}/{repo}")
async def get_releases(owner: str, repo: str, limit: int = Query(10)):
    """Get releases from GitHub repo."""
    from ..core.release_publisher import list_releases, set_repo_url, get_repo_config
    
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
    from ..core.orchestrator import github_sync
    
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
    from ..engine.project import create_snapshot as _create_snapshot
    
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
    from ..engine.project import list_snapshots as _list_snapshots
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
    from ..core.constraints import validate_action
    from ..engine.project import list_snapshots as _list_snapshots
    
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

async def get_version_context_for_claude(repo: str = "THEMiS-eng/themis-qs") -> str:
    """
    ENV015: Get version context to inject into every Claude call.
    Ensures Claude always knows current version state.
    """
    from ..core.release_publisher import list_releases, set_repo_url, get_repo_config
    
    try:
        original = get_repo_config()
        set_repo_url(f"https://github.com/{repo}")
        releases = list_releases(limit=10)
        
        if not releases:
            return "VALIDATED VERSION INFO (ENV012/ENV015):\n- No releases found\n- Start with v0.0.1"
        
        existing_tags = [r.get("tag", "") for r in releases]
        versions = [_parse_version(t) for t in existing_tags]
        current = max(versions) if versions else (0, 0, 0)
        
        lines = [
            "VALIDATED VERSION INFO (ENV012/ENV015):",
            f"- Current version: v{_version_to_str(current)}",
            f"- Next patch: v{_version_to_str((current[0], current[1], current[2] + 1))}",
            f"- Next minor: v{_version_to_str((current[0], current[1] + 1, 0))}",
            f"- Next major: v{_version_to_str((current[0] + 1, 0, 0))}",
            f"- Recent tags: {', '.join(existing_tags[:5])}"
        ]
        
        if original.get("url"):
            set_repo_url(original["url"])
        
        return "\n".join(lines)
    except Exception as e:
        return f"VALIDATED VERSION INFO (ENV012/ENV015):\n- Error fetching: {e}"

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
    from ..core.release_publisher import list_releases, set_repo_url, get_repo_config
    
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
    
    from ..core.release_publisher import list_releases, set_repo_url, get_repo_config
    
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
    from ..core.release_publisher import create_release, set_repo_url, list_releases, get_repo_config
    
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
    from ..roadmap.prompt_optimizer import lint_prompt, get_lint_summary
    
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
    from ..roadmap.prompt_optimizer import lint_prompt, optimize_prompt
    
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
    from ..roadmap.prompt_optimizer import get_lint_summary
    
    summary = get_lint_summary(prompt)
    return {"summary": summary}

# ============================================================
# LEARNING (via core/learning)
# ============================================================

@app.get("/api/learning/report")
async def learning_report(project: str = Query(DEFAULT_PROJECT)):
    """Get learning report for project."""
    from ..core.learning import load_learned_errors, get_error_context_for_retry
    
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
    from ..core.learning import load_learned_errors
    
    errors = load_learned_errors(project)
    return {"patterns": errors.get("patterns", {})}

@app.post("/api/learning/error")
async def log_learning_error(data: Dict[str, Any]):
    """Log an error for learning."""
    from ..core.learning import learn_from_error
    
    project = data.get("project", DEFAULT_PROJECT)
    error_type = data.get("error_type", "unknown")
    message = data.get("message", "")
    context = data.get("context", {})
    
    learn_from_error(project, error_type, message, context)
    return {"success": True}

# ============================================================
# CONSTRAINTS (via core/constraints)
# ============================================================

@app.get("/api/constraints")
async def get_constraints():
    """Get all constraints."""
    from ..core.constraints import get_all_constraints
    return {"constraints": get_all_constraints()}

@app.post("/api/constraints/validate")
async def validate_constraint(data: Dict[str, Any]):
    """Validate an action against constraints."""
    from ..core.constraints import validate_action
    
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
    from ..core.release_listener import check_for_update
    
    result = check_for_update()
    return result

@app.post("/api/update/install-from-github")
async def install_from_github_endpoint():
    """Install latest release from GitHub."""
    from ..core.release_listener import install_from_github
    
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
    backlog → snapshot → fix → snapshot → git commit → bugfix
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
    from ..engine.tracking import add_backlog_item
    
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
    from ..core.debugger import log_error
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
    from ..engine.tracking import get_backlog
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
async def get_console_errors():
    """Get captured console errors."""
    return {
        "errors": _console_errors,
        "count": len(_console_errors),
        "formatted": get_console_errors_for_claude()
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
    from ..core.debugger import log_error
    
    error_id = log_error(data, source=data.get("source", "api"))
    return {"success": True, "error_id": error_id}

@app.get("/api/debug/errors")
async def get_debug_errors():
    """Get pending debug errors."""
    from ..core.debugger import get_pending_errors
    return {"errors": get_pending_errors()}

@app.get("/api/debug/report")
async def debug_report():
    """Get formatted debug report for Claude."""
    from ..core.debugger import auto_debug_check
    
    report = auto_debug_check()
    return {"has_errors": bool(report), "report": report or "No errors"}

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

def run():
    _kill_existing_process()
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")

if __name__ == "__main__":
    run()
