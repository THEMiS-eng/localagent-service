"""
LocalAgent v3.0 - CORE: Debugger
Auto-captures errors, learns from fixes, creates GitHub issues

Flow:
1. Error captured → log_error()
2. Check learning for known solution → get_learned_fix()
3. If no solution → send to Claude for analysis
4. Claude provides fix → apply and learn
5. Create GitHub issue for tracking
6. Store solution in learning for future errors
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from ..engine.project import CONFIG_DIR


# ============================================================
# ERROR STORAGE
# ============================================================

DEBUG_LOG = CONFIG_DIR / "debug_log.json"
ERROR_PATTERNS = CONFIG_DIR / "error_patterns.json"


def _load_debug_log() -> Dict:
    """Load debug log from disk."""
    default = {"errors": [], "fixes": [], "sessions": [], "stats": {"total": 0, "auto_fixed": 0, "learned": 0}}
    if DEBUG_LOG.exists():
        try:
            data = json.loads(DEBUG_LOG.read_text())
            # Ensure stats exists
            if "stats" not in data:
                data["stats"] = {"total": 0, "auto_fixed": 0, "learned": 0}
            return data
        except:
            pass
    return default


def _save_debug_log(data: Dict):
    """Save debug log to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_LOG.write_text(json.dumps(data, indent=2, default=str))


def _load_error_patterns() -> Dict:
    """Load learned error patterns."""
    if ERROR_PATTERNS.exists():
        try:
            return json.loads(ERROR_PATTERNS.read_text())
        except:
            pass
    return {"patterns": {}}


def _save_error_patterns(data: Dict):
    """Save error patterns."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    ERROR_PATTERNS.write_text(json.dumps(data, indent=2, default=str))


def _extract_error_signature(error: Dict) -> str:
    """Extract a signature from error for pattern matching."""
    msg = error.get("message", "")
    # Remove line numbers, file paths, and variable values
    import re
    sig = re.sub(r':\d+:\d+', ':X:X', msg)
    sig = re.sub(r'line \d+', 'line X', sig)
    sig = re.sub(r"'[^']*'", "'X'", sig)
    sig = re.sub(r'"[^"]*"', '"X"', sig)
    return sig[:200]  # Limit length


# ============================================================
# ERROR LOGGING WITH AUTO-LEARNING
# ============================================================

def log_error(error: Dict, source: str = "js") -> str:
    """
    Log an error and check for known solutions.
    
    Args:
        error: Error details (message, stack, line, etc.)
        source: Where error came from (js, python, api, dashboard, chat-module)
        
    Returns:
        Error ID
    """
    data = _load_debug_log()
    
    error_id = f"ERR-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(data['errors']) + 1:04d}"
    
    # Extract signature for pattern matching
    signature = _extract_error_signature(error)
    
    # Check if we have a learned fix for this pattern
    known_fix = get_learned_fix(signature)
    
    entry = {
        "id": error_id,
        "source": source,
        "timestamp": datetime.now().isoformat(),
        "error": error,
        "signature": signature,
        "status": "auto_fixed" if known_fix else "new",
        "known_fix": known_fix,
        "fix": None,
        "github_issue": None,
        "claude_analysis": None
    }
    
    data["errors"].append(entry)
    data["stats"]["total"] += 1
    if known_fix:
        data["stats"]["auto_fixed"] += 1
    
    _save_debug_log(data)
    
    return error_id


def get_learned_fix(signature: str) -> Optional[Dict]:
    """Check if we have a learned fix for this error pattern."""
    patterns = _load_error_patterns()
    
    if signature in patterns["patterns"]:
        pattern = patterns["patterns"][signature]
        pattern["times_used"] = pattern.get("times_used", 0) + 1
        _save_error_patterns(patterns)
        return pattern
    
    return None


def learn_from_fix(error_id: str, fix_description: str, fix_code: str = None):
    """
    Learn from a successful fix to apply automatically next time.
    
    Args:
        error_id: The error that was fixed
        fix_description: Human-readable description
        fix_code: Optional code/commands to apply
    """
    data = _load_debug_log()
    patterns = _load_error_patterns()
    
    # Find the error
    for e in data["errors"]:
        if e["id"] == error_id:
            signature = e.get("signature", "")
            
            # Store the pattern
            patterns["patterns"][signature] = {
                "fix_description": fix_description,
                "fix_code": fix_code,
                "learned_from": error_id,
                "learned_at": datetime.now().isoformat(),
                "times_used": 0,
                "original_error": e["error"].get("message", "")[:200]
            }
            
            e["status"] = "fixed"
            e["fix"] = {
                "description": fix_description,
                "code": fix_code,
                "timestamp": datetime.now().isoformat()
            }
            
            data["stats"]["learned"] += 1
            break
    
    _save_debug_log(data)
    _save_error_patterns(patterns)


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


def set_github_issue(error_id: str, issue_url: str, issue_number: int):
    """Link error to GitHub issue."""
    data = _load_debug_log()
    
    for e in data["errors"]:
        if e["id"] == error_id:
            e["github_issue"] = {
                "url": issue_url,
                "number": issue_number,
                "created_at": datetime.now().isoformat()
            }
            break
    
    _save_debug_log(data)


def set_claude_analysis(error_id: str, analysis: str, suggested_fix: str = None):
    """Store Claude's analysis of an error."""
    data = _load_debug_log()
    
    for e in data["errors"]:
        if e["id"] == error_id:
            e["status"] = "analyzing"
            e["claude_analysis"] = {
                "analysis": analysis,
                "suggested_fix": suggested_fix,
                "timestamp": datetime.now().isoformat()
            }
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


# ============================================================
# CLAUDE INTEGRATION - Auto-analyze errors
# ============================================================

async def analyze_error_with_claude(error_id: str) -> Dict:
    """
    Send error to Claude for analysis.
    
    Returns:
        Dict with analysis and suggested fix
    """
    from ..connectors.llm import call_claude
    
    data = _load_debug_log()
    error_entry = None
    
    for e in data["errors"]:
        if e["id"] == error_id:
            error_entry = e
            break
    
    if not error_entry:
        return {"success": False, "error": "Error not found"}
    
    # Check if we have learned patterns that might help
    patterns = _load_error_patterns()
    similar_fixes = []
    for sig, pattern in patterns["patterns"].items():
        if _similarity(sig, error_entry.get("signature", "")) > 0.7:
            similar_fixes.append(pattern)
    
    # Build prompt for Claude
    prompt = f"""Analyze this error and provide a fix:

**Error ID:** {error_id}
**Source:** {error_entry.get('source', 'unknown')}
**Message:** {error_entry.get('error', {}).get('message', 'Unknown')}
**Timestamp:** {error_entry.get('timestamp')}

"""
    
    if error_entry.get('error', {}).get('stack'):
        prompt += f"**Stack trace:**\n```\n{error_entry['error']['stack'][:500]}\n```\n\n"
    
    if similar_fixes:
        prompt += "**Similar errors we've fixed before:**\n"
        for fix in similar_fixes[:3]:
            prompt += f"- {fix.get('original_error', '')[:100]}\n  Fix: {fix.get('fix_description', '')}\n"
        prompt += "\n"
    
    prompt += """Please provide:
1. Root cause analysis
2. Suggested fix (code if applicable)
3. Prevention tips

Format your response as JSON:
{"analysis": "...", "fix": "...", "code": "...", "prevention": "..."}"""
    
    try:
        claude_result = call_claude(prompt)

        if not claude_result.get("success"):
            return {"success": False, "error": claude_result.get("error", "Claude API call failed")}

        response_text = claude_result.get("response", "")

        # Try to parse JSON response
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = {"analysis": response_text, "fix": None}
        
        # Store Claude's analysis
        set_claude_analysis(error_id, result.get("analysis", ""), result.get("fix"))
        
        return {"success": True, "result": result}
        
    except Exception as ex:
        return {"success": False, "error": str(ex)}


def _similarity(s1: str, s2: str) -> float:
    """Simple similarity score between two strings."""
    if not s1 or not s2:
        return 0.0
    
    words1 = set(s1.lower().split())
    words2 = set(s2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1 & words2
    union = words1 | words2
    
    return len(intersection) / len(union)


# ============================================================
# GITHUB INTEGRATION - Create issues for errors
# ============================================================

def create_github_issue_for_error(error_id: str, repo_type: str = "service") -> Dict:
    """
    Create a GitHub issue for an error.
    
    Args:
        error_id: The error to create issue for
        repo_type: 'service' or 'dashboard'
        
    Returns:
        Dict with issue URL and number
    """
    from ..connectors.github import _get_token, _api_request, REPOS
    
    data = _load_debug_log()
    error_entry = None
    
    for e in data["errors"]:
        if e["id"] == error_id:
            error_entry = e
            break
    
    if not error_entry:
        return {"success": False, "error": "Error not found"}
    
    if error_entry.get("github_issue"):
        return {"success": True, "already_exists": True, "issue": error_entry["github_issue"]}
    
    token = _get_token()
    if not token:
        return {"success": False, "error": "No GitHub token configured"}
    
    repo = REPOS.get(repo_type)
    if not repo:
        return {"success": False, "error": f"Unknown repo type: {repo_type}"}
    
    # Build issue body
    err = error_entry.get("error", {})
    body = f"""## Error Report

**Error ID:** `{error_id}`
**Source:** {error_entry.get('source', 'unknown')}
**Timestamp:** {error_entry.get('timestamp')}

### Error Message
```
{err.get('message', 'Unknown error')}
```

### Stack Trace
```
{err.get('stack', 'No stack trace')[:1000]}
```

### Context
- **File:** {err.get('file', 'Unknown')}
- **Line:** {err.get('line', 'Unknown')}

---
*Auto-generated by LocalAgent Debugger*
"""
    
    # Add Claude analysis if available
    if error_entry.get("claude_analysis"):
        analysis = error_entry["claude_analysis"]
        body += f"""

### Claude Analysis
{analysis.get('analysis', '')}

### Suggested Fix
{analysis.get('suggested_fix', 'None')}
"""
    
    # Create issue
    title = f"[BUG] {err.get('message', 'Unknown error')[:80]}"
    
    try:
        result = _api_request(
            "POST",
            f"https://api.github.com/repos/{repo}/issues",
            data={"title": title, "body": body, "labels": ["bug", "auto-generated"]},
            token=token
        )
        
        if result.get("number"):
            issue_url = result.get("html_url", f"https://github.com/{repo}/issues/{result['number']}")
            set_github_issue(error_id, issue_url, result["number"])
            
            return {
                "success": True,
                "issue_url": issue_url,
                "issue_number": result["number"]
            }
        else:
            return {"success": False, "error": result.get("message", "Unknown error")}
            
    except Exception as ex:
        return {"success": False, "error": str(ex)}


# ============================================================
# AUTO-FIX PIPELINE
# ============================================================

async def auto_fix_error(error_id: str) -> Dict:
    """
    Full auto-fix pipeline:
    1. Check for learned fix
    2. If none, analyze with Claude
    3. Create GitHub issue
    4. Apply fix if possible
    5. Learn from fix
    
    Returns:
        Dict with status and actions taken
    """
    data = _load_debug_log()
    error_entry = None
    
    for e in data["errors"]:
        if e["id"] == error_id:
            error_entry = e
            break
    
    if not error_entry:
        return {"success": False, "error": "Error not found"}
    
    actions = []
    
    # Step 1: Check for known fix
    if error_entry.get("known_fix"):
        actions.append({
            "step": "known_fix_found",
            "fix": error_entry["known_fix"]["fix_description"]
        })
        return {
            "success": True,
            "auto_fixed": True,
            "fix": error_entry["known_fix"],
            "actions": actions
        }
    
    # Step 2: Analyze with Claude
    actions.append({"step": "analyzing_with_claude"})
    analysis_result = await analyze_error_with_claude(error_id)
    
    if analysis_result.get("success"):
        actions.append({
            "step": "claude_analysis_complete",
            "analysis": analysis_result.get("result", {}).get("analysis", "")[:200]
        })
    
    # Step 3: Create GitHub issue
    actions.append({"step": "creating_github_issue"})
    issue_result = create_github_issue_for_error(error_id)
    
    if issue_result.get("success"):
        actions.append({
            "step": "github_issue_created",
            "issue_url": issue_result.get("issue_url")
        })
    
    return {
        "success": True,
        "auto_fixed": False,
        "needs_manual_fix": True,
        "analysis": analysis_result.get("result") if analysis_result.get("success") else None,
        "github_issue": issue_result.get("issue_url") if issue_result.get("success") else None,
        "actions": actions
    }


def get_error_context_for_claude() -> str:
    """
    Get full error context to inject into Claude's system prompt.
    
    Returns context about:
    - Pending errors
    - Learned patterns
    - Recent fixes
    """
    data = _load_debug_log()
    patterns = _load_error_patterns()
    
    lines = []
    
    # Pending errors
    pending = [e for e in data["errors"] if e["status"] in ("new", "analyzing")]
    if pending:
        lines.append(f"⚠️ {len(pending)} pending errors need attention:")
        for e in pending[:5]:
            lines.append(f"  - {e['id']}: {e.get('error', {}).get('message', '')[:60]}")
    
    # Learned patterns
    if patterns["patterns"]:
        lines.append(f"\n📚 {len(patterns['patterns'])} learned error patterns available")
    
    # Stats
    stats = data.get("stats", {})
    if stats.get("total", 0) > 0:
        auto_rate = (stats.get("auto_fixed", 0) / stats["total"]) * 100
        lines.append(f"\n📊 Error stats: {stats['total']} total, {auto_rate:.0f}% auto-fixed")
    
    return "\n".join(lines) if lines else ""


def get_debug_stats() -> Dict:
    """Get debugging statistics."""
    data = _load_debug_log()
    patterns = _load_error_patterns()
    
    return {
        "total_errors": data.get("stats", {}).get("total", 0),
        "auto_fixed": data.get("stats", {}).get("auto_fixed", 0),
        "learned_patterns": len(patterns.get("patterns", {})),
        "pending": len([e for e in data["errors"] if e["status"] == "new"]),
        "analyzing": len([e for e in data["errors"] if e["status"] == "analyzing"]),
        "fixed": len([e for e in data["errors"] if e["status"] == "fixed"])
    }
