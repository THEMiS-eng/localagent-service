"""
LocalAgent - Debug Router
Endpoints: /api/debug/*
"""

import asyncio
from typing import Dict, Any, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query

from ...core.debugger import (
    log_error, get_pending_errors as get_errors,
    get_debug_stats, learn_from_fix,
    create_github_issue_for_error,
)
from ...engine.tracking import get_backlog, add_backlog_item

router = APIRouter(prefix="/api/debug", tags=["debug"])

DEFAULT_PROJECT = "LOCALAGENT"

# WebSocket manager reference (set by main server)
_ws_manager = None
_logger = None

# In-memory store for console errors
_console_errors: List[Dict] = []
MAX_CONSOLE_ERRORS = 50

def set_ws_manager(manager):
    global _ws_manager
    _ws_manager = manager

def set_logger(logger):
    global _logger
    _logger = logger


# ============================================================
# CONSOLE ERROR CAPTURE
# ============================================================

@router.post("/console-error")
async def capture_console_error(data: Dict[str, Any]):
    """
    Capture console error from FE or BE.
    Errors are queued to backlog as high-priority TODO items.
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
    
    # Log to debugger
    log_error(error_entry, source=error_entry["source"])
    
    # Queue to backlog
    title = f"[{error_entry['source'].upper()}] {error_entry['message'][:80]}"
    if error_entry.get("file") and error_entry.get("line"):
        title += f" @ {error_entry['file']}:{error_entry['line']}"
    
    backlog_id = add_backlog_item(
        DEFAULT_PROJECT,
        title,
        priority="high",
        metadata={"type": "console_error", "error": error_entry}
    )
    
    if _logger:
        _logger.warning(f"Console error queued [{backlog_id}]: {error_entry['message'][:50]}")
    
    return {
        "success": True, 
        "queued": True,
        "backlog_id": backlog_id,
        "message": "Error queued to backlog"
    }

@router.get("/console-errors")
async def get_console_errors():
    """Get console errors from backlog."""
    backlog = get_backlog(DEFAULT_PROJECT)
    
    console_errors = [
        b for b in backlog 
        if b.get("metadata", {}).get("type") == "console_error"
    ]
    
    return {
        "errors": [b.get("metadata", {}).get("error", {}) for b in console_errors],
        "count": len(console_errors),
        "backlog_ids": [b.get("id") for b in console_errors]
    }

@router.post("/console-errors/clear")
async def clear_console_errors():
    """Clear console errors."""
    global _console_errors
    count = len(_console_errors)
    _console_errors = []
    return {"success": True, "cleared": count}


# ============================================================
# DEBUG ERRORS
# ============================================================

@router.post("/log")
async def debug_log(data: Dict[str, Any]):
    """Log debug info."""
    error_id = log_error(data, source=data.get("source", "api"))
    return {"success": True, "error_id": error_id}

@router.get("/errors")
async def get_debug_errors():
    """Get pending debug errors."""
    return {"errors": get_errors()}

@router.post("/error")
async def post_debug_error(data: Dict[str, Any]):
    """Receive error from dashboard/client."""
    from ...core.debugger import _load_debug_log
    
    error_data = {
        "message": data.get("message", "Unknown error"),
        "source": data.get("source", "unknown"),
        "level": data.get("level", "error"),
        "timestamp": data.get("timestamp"),
        "line": data.get("line"),
        "file": data.get("file"),
        "stack": data.get("stack"),
    }
    
    error_id = log_error(error_data, source=data.get("source", "js"))
    
    # Check for learned fix
    debug_data = _load_debug_log()
    error_entry = next((e for e in debug_data["errors"] if e["id"] == error_id), None)
    known_fix = error_entry.get("known_fix") if error_entry else None
    
    # Broadcast to WebSocket
    if _ws_manager:
        await _ws_manager.broadcast({
            "type": "error",
            "error": error_data,
            "error_id": error_id,
            "known_fix": known_fix,
            "auto_fixed": known_fix is not None
        })
    
    return {
        "success": True, 
        "error_id": error_id,
        "known_fix": known_fix,
        "auto_fixed": known_fix is not None
    }


# ============================================================
# DEBUG STATS & REPORTS
# ============================================================

@router.get("/report")
async def debug_report():
    """Get formatted debug report for Claude."""
    # Import here to avoid circular
    try:
        from ..debugger import auto_debug_check
        report = auto_debug_check()
    except:
        report = None
    return {"has_errors": bool(report), "report": report or "No errors"}

@router.get("/stats")
async def debug_stats_endpoint():
    """Get debugging statistics."""
    return get_debug_stats()


# ============================================================
# AUTO-FIX & LEARNING
# ============================================================

@router.post("/auto-fix/{error_id}")
async def auto_fix_endpoint(error_id: str):
    """Trigger auto-fix pipeline for an error."""
    # Import here to avoid circular
    from ..server import auto_fix_error
    
    result = await auto_fix_error(error_id)
    
    if _ws_manager:
        await _ws_manager.broadcast({
            "type": "auto_fix_result",
            "error_id": error_id,
            "result": result
        })
    
    return result

@router.post("/analyze/{error_id}")
async def analyze_error_endpoint(error_id: str):
    """Send error to Claude for analysis."""
    from ..server import analyze_error_with_claude
    result = await analyze_error_with_claude(error_id)
    return result

@router.post("/github-issue/{error_id}")
async def create_issue_endpoint(error_id: str, repo_type: str = Query("service")):
    """Create GitHub issue for an error."""
    result = create_github_issue_for_error(error_id, repo_type)
    return result

@router.post("/learn")
async def learn_fix_endpoint(data: Dict[str, Any]):
    """Learn from a successful fix."""
    error_id = data.get("error_id")
    fix_description = data.get("fix_description")
    fix_code = data.get("fix_code")
    
    if not error_id or not fix_description:
        raise HTTPException(status_code=400, detail="error_id and fix_description required")
    
    learn_from_fix(error_id, fix_description, fix_code)
    return {"success": True, "learned": True}

@router.get("/context")
async def get_debug_context():
    """Get debug context for current session."""
    return {
        "pending_errors": len(get_errors()),
        "console_errors": len(_console_errors),
    }
