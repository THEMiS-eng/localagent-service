"""
LocalAgent v2.10.49 - CORE: Debugger
Auto-captures errors and negotiates fixes with Claude

Flow:
1. JS error captured in browser → /api/debug/error
2. Server stores in JS_ERRORS list
3. Agent periodically checks or user triggers debug
4. Agent formats errors and sends to Claude via chat
5. Claude analyzes and provides fix
6. Agent applies fix (or prompts user)
"""

import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from ..engine.project import CONFIG_DIR


# ============================================================
# ERROR STORAGE
# ============================================================

DEBUG_LOG = CONFIG_DIR / "debug_log.json"


def _load_debug_log() -> Dict:
    """Load debug log from disk."""
    if DEBUG_LOG.exists():
        try:
            return json.loads(DEBUG_LOG.read_text())
        except:
            pass
    return {"errors": [], "fixes": [], "sessions": []}


def _save_debug_log(data: Dict):
    """Save debug log to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_LOG.write_text(json.dumps(data, indent=2, default=str))


def log_error(error: Dict, source: str = "js") -> str:
    """
    Log an error for debugging.
    
    Args:
        error: Error details (message, stack, line, etc.)
        source: Where error came from (js, python, api, etc.)
        
    Returns:
        Error ID
    """
    data = _load_debug_log()
    
    error_id = f"ERR-{len(data['errors']) + 1:04d}"
    
    entry = {
        "id": error_id,
        "source": source,
        "timestamp": datetime.now().isoformat(),
        "error": error,
        "status": "new",  # new, analyzing, fixed, ignored
        "fix": None
    }
    
    data["errors"].append(entry)
    _save_debug_log(data)
    
    return error_id


def get_pending_errors() -> List[Dict]:
    """Get all unfixed errors."""
    data = _load_debug_log()
    return [e for e in data["errors"] if e["status"] in ("new", "analyzing")]


def mark_error_fixed(error_id: str, fix_description: str):
    """Mark an error as fixed."""
    data = _load_debug_log()
    
    for e in data["errors"]:
        if e["id"] == error_id:
            e["status"] = "fixed"
            e["fix"] = {
                "description": fix_description,
                "timestamp": datetime.now().isoformat()
            }
            break
    
    _save_debug_log(data)


def mark_error_ignored(error_id: str, reason: str = ""):
    """Mark an error as ignored."""
    data = _load_debug_log()
    
    for e in data["errors"]:
        if e["id"] == error_id:
            e["status"] = "ignored"
            e["ignore_reason"] = reason
            break
    
    _save_debug_log(data)


# ============================================================
# ERROR FORMATTING FOR CLAUDE
# ============================================================

def format_errors_for_claude(errors: List[Dict] = None) -> str:
    """
    Format errors for sending to Claude for analysis.
    
    Returns a message that can be sent via the chat interface.
    """
    if errors is None:
        errors = get_pending_errors()
    
    if not errors:
        return ""
    
    lines = [
        "🐛 **DEBUG REPORT** - Errors captured that need analysis:",
        ""
    ]
    
    for e in errors[:10]:  # Limit to 10 errors
        err = e.get("error", {})
        lines.append(f"### {e['id']} ({e['source']})")
        lines.append(f"- **Message**: {err.get('message', 'Unknown')}")
        
        if err.get("line"):
            lines.append(f"- **Location**: Line {err.get('line')}, Col {err.get('column', '?')}")
        
        if err.get("stack"):
            stack_preview = err["stack"][:300] + "..." if len(err.get("stack", "")) > 300 else err.get("stack", "")
            lines.append(f"- **Stack**: ```{stack_preview}```")
        
        lines.append("")
    
    lines.append("---")
    lines.append("Please analyze these errors and provide fixes.")
    
    return "\n".join(lines)


def format_js_errors_for_claude(js_errors: List[Dict]) -> str:
    """
    Format live JS errors for Claude analysis.
    
    Args:
        js_errors: List from dashboard.JS_ERRORS
    """
    if not js_errors:
        return ""
    
    lines = [
        "🐛 **LIVE JS ERRORS** from dashboard:",
        ""
    ]
    
    for i, err in enumerate(js_errors[-10:], 1):  # Last 10
        lines.append(f"**Error {i}:**")
        lines.append(f"- Message: `{err.get('message', 'Unknown')}`")
        
        if err.get("line"):
            lines.append(f"- Line: {err.get('line')}, Column: {err.get('column', '?')}")
        
        if err.get("url"):
            lines.append(f"- URL: {err.get('url')}")
        
        if err.get("stack"):
            stack = err["stack"][:200] + "..." if len(err.get("stack", "")) > 200 else err.get("stack", "")
            lines.append(f"- Stack: `{stack}`")
        
        lines.append("")
    
    return "\n".join(lines)


# ============================================================
# AUTO-DEBUG PROTOCOL
# ============================================================

def create_debug_request(context: str = "") -> Dict:
    """
    Create a debug request that can be sent to Claude.
    
    Returns a structured request for the negotiator to process.
    """
    from ..connectors.dashboard import JS_ERRORS
    
    pending = get_pending_errors()
    js_errors = JS_ERRORS.copy() if JS_ERRORS else []
    
    if not pending and not js_errors:
        return {"has_errors": False}
    
    return {
        "has_errors": True,
        "pending_count": len(pending),
        "js_error_count": len(js_errors),
        "message": format_errors_for_claude(pending) + "\n\n" + format_js_errors_for_claude(js_errors),
        "context": context,
        "timestamp": datetime.now().isoformat()
    }


def auto_debug_check() -> Optional[str]:
    """
    Check if there are errors to report.
    
    Called periodically or after operations.
    Returns formatted error message if errors exist, None otherwise.
    """
    try:
        from ..connectors.dashboard import JS_ERRORS
        js_errors = JS_ERRORS.copy() if JS_ERRORS else []
    except:
        js_errors = []
    
    pending = get_pending_errors()
    
    if not pending and not js_errors:
        return None
    
    total = len(pending) + len(js_errors)
    
    if total > 0:
        msg = format_errors_for_claude(pending)
        if js_errors:
            msg += "\n\n" + format_js_errors_for_claude(js_errors)
        return msg
    
    return None


# ============================================================
# CLI INTEGRATION
# ============================================================

def show_debug_status():
    """Show current debug status."""
    pending = get_pending_errors()
    
    try:
        from ..connectors.dashboard import JS_ERRORS
        js_count = len(JS_ERRORS) if JS_ERRORS else 0
    except:
        js_count = 0
    
    print(f"\n🐛 Debug Status:")
    print(f"   Pending errors: {len(pending)}")
    print(f"   JS errors (live): {js_count}")
    
    if pending:
        print(f"\n   Recent errors:")
        for e in pending[-5:]:
            msg = e.get("error", {}).get("message", "Unknown")[:50]
            print(f"   - {e['id']}: {msg}...")
