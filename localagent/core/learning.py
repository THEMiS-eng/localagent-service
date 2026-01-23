"""
LocalAgent v2.10.17 - CORE: Learning
🧠 SMART - Apprend des erreurs, ne répète jamais

Stockage par projet: ~/.localagent-dev/projects/PROJECT/errors.json
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


# ============================================================
# PATHS
# ============================================================

def _get_errors_file(project: str) -> Path:
    """Get path to project errors file."""
    from ..engine.project import PROJECTS_DIR
    return PROJECTS_DIR / project / "errors.json"


# ============================================================
# LOAD / SAVE
# ============================================================

def load_learned_errors(project: str) -> Dict:
    """
    Load learned errors for project.
    
    Structure:
    {
        "errors": [
            {
                "key": "error_type: message",
                "type": "truncation|parse_error|empty|validation|...",
                "message": "...",
                "count": 5,
                "first_seen": "2025-01-19T...",
                "last_seen": "2025-01-19T...",
                "context": {...},
                "solution": "what fixed it"
            }
        ],
        "patterns": {
            "markdown_in_response": 12,
            "json_truncation": 5,
            ...
        },
        "dodges": [
            {"key": "...", "type": "...", "count": 3}
        ]
    }
    """
    errors_file = _get_errors_file(project)
    if errors_file.exists():
        try:
            return json.loads(errors_file.read_text())
        except:
            pass
    return {"errors": [], "patterns": {}, "dodges": []}


def save_learned_errors(project: str, errors: Dict):
    """Save learned errors for project."""
    errors_file = _get_errors_file(project)
    errors_file.parent.mkdir(parents=True, exist_ok=True)
    errors_file.write_text(json.dumps(errors, indent=2))


# ============================================================
# LEARN FROM ERROR
# ============================================================

def learn_from_error(
    project: str,
    error_type: str,
    error_msg: str,
    context: Dict = None,
    solution: str = None
):
    """
    Record an error to learn from it.
    
    Args:
        project: Project name
        error_type: Category (truncation, parse_error, empty, validation, etc.)
        error_msg: Error message
        context: Additional context (instruction, file, etc.)
        solution: What fixed it (if known)
    """
    errors = load_learned_errors(project)
    error_key = f"{error_type}: {error_msg[:100]}"
    
    # Find existing or create new
    existing = next((e for e in errors["errors"] if e["key"] == error_key), None)
    
    if existing:
        existing["count"] += 1
        existing["last_seen"] = datetime.now().isoformat()
        if solution and not existing.get("solution"):
            existing["solution"] = solution
        if context:
            existing["context"] = context
    else:
        errors["errors"].append({
            "key": error_key,
            "type": error_type,
            "message": error_msg[:500],
            "count": 1,
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "context": context or {},
            "solution": solution
        })
    
    # Update pattern count
    if error_type not in errors["patterns"]:
        errors["patterns"][error_type] = 0
    errors["patterns"][error_type] += 1
    
    # Keep last 100 errors
    errors["errors"] = errors["errors"][-100:]
    
    save_learned_errors(project, errors)


def resolve_error_as_bugfix(
    project: str,
    error_type: str,
    error_msg: str,
    solution: str,
    version_fixed: str
) -> Dict:
    """
    Mark an error as resolved and register as bugfix.
    
    This is called when an error is successfully fixed.
    The bugfix is then injected into future Claude calls to prevent regression.
    
    Args:
        project: Project name
        error_type: Error type that was fixed
        error_msg: Original error message
        solution: What fixed it
        version_fixed: Version where fix was applied
    
    Returns:
        Bugfix dict with id
    """
    # Update the error with solution
    errors = load_learned_errors(project)
    error_key = f"{error_type}: {error_msg[:100]}"
    
    for e in errors["errors"]:
        if e["key"] == error_key:
            e["solution"] = solution
            e["resolved"] = True
            e["version_fixed"] = version_fixed
            break
    
    save_learned_errors(project, errors)
    
    # Register as bugfix via HTTP (if server running)
    bugfix = {
        "error_type": error_type,
        "description": f"{error_type}: {error_msg[:50]}",
        "solution": solution,
        "version_fixed": version_fixed
    }
    
    # Try to register with server
    try:
        import urllib.request
        import json as json_module
        req = urllib.request.Request(
            "http://localhost:9998/api/bugfixes/register",
            data=json_module.dumps(bugfix).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=2)
    except:
        pass  # Server may not be running
    
    return bugfix


def learn_dodge(project: str, dodge_type: str, dodge_msg: str):
    """
    Record when Claude tries to dodge/avoid a task.
    
    Args:
        project: Project name
        dodge_type: Type of dodge (refuses, deflects, asks_clarification, etc.)
        dodge_msg: The dodge message
    """
    errors = load_learned_errors(project)
    dodge_key = f"{dodge_type}: {dodge_msg[:50]}"
    
    if "dodges" not in errors:
        errors["dodges"] = []
    
    existing = next((d for d in errors["dodges"] if d["key"] == dodge_key), None)
    
    if existing:
        existing["count"] += 1
        existing["last_seen"] = datetime.now().isoformat()
    else:
        errors["dodges"].append({
            "key": dodge_key,
            "type": dodge_type,
            "message": dodge_msg[:200],
            "count": 1,
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat()
        })
    
    # Keep last 50 dodges
    errors["dodges"] = errors["dodges"][-50:]
    
    save_learned_errors(project, errors)


# ============================================================
# QUERY LEARNED ERRORS
# ============================================================

def get_similar_errors(project: str, error_type: str) -> List[Dict]:
    """Get errors of same type to inform retry strategy."""
    errors = load_learned_errors(project)
    return [e for e in errors["errors"] if e["type"] == error_type]


def get_error_pattern_count(project: str, pattern: str) -> int:
    """Get count of specific error pattern."""
    errors = load_learned_errors(project)
    return errors.get("patterns", {}).get(pattern, 0)


def has_learned_solution(project: str, error_type: str) -> Optional[str]:
    """Check if we have a learned solution for this error type."""
    errors = load_learned_errors(project)
    for e in reversed(errors["errors"]):
        if e["type"] == error_type and e.get("solution"):
            return e["solution"]
    return None


def get_error_context_for_retry(project: str) -> str:
    """
    Build context string from learned errors to include in retry prompt.
    This helps Claude avoid repeating mistakes.
    """
    errors = load_learned_errors(project)
    
    if not errors["errors"]:
        return ""
    
    # Get recent high-count errors
    recent = sorted(errors["errors"], key=lambda x: x["count"], reverse=True)[:5]
    
    lines = ["LEARNED ERRORS (do not repeat):"]
    for e in recent:
        solution = f" → Fix: {e['solution']}" if e.get("solution") else ""
        lines.append(f"- {e['type']}: {e['message'][:80]}{solution}")
    
    return "\n".join(lines)


# ============================================================
# DISPLAY
# ============================================================

def show_learned_errors(project: str):
    """Display learned errors for project."""
    errors = load_learned_errors(project)
    
    print(f"\n🧠 Learned Errors for {project}:")
    print("-" * 60)
    
    if not errors["errors"]:
        print("  (no errors recorded)")
        return
    
    # Show patterns
    print("\n📊 Error Patterns:")
    for pattern, count in sorted(errors.get("patterns", {}).items(), key=lambda x: -x[1]):
        print(f"   {pattern}: {count} occurrences")
    
    # Show recent errors
    print("\n📋 Recent Errors:")
    for e in errors["errors"][-10:]:
        solution = f" ✅ {e['solution']}" if e.get("solution") else ""
        print(f"   [{e['count']}x] {e['type']}: {e['message'][:50]}...{solution}")
    
    # Show dodges
    if errors.get("dodges"):
        print("\n🚫 Dodges Detected:")
        for d in errors["dodges"][-5:]:
            print(f"   [{d['count']}x] {d['type']}: {d['message'][:50]}...")
    
    print()
