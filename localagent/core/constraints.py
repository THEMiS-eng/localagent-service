"""
LocalAgent v2.10.17 - CORE: Constraints
🔑 CLÉ DE VOÛTE - Tout passe par ici

Règles IMMUTABLES - Jamais modifiées à runtime
Chaque action doit être validée contre ces contraintes
"""

from typing import Dict, List, Tuple


# ============================================================
# ENV CONSTRAINTS - Système (IMMUTABLE)
# ============================================================

ENV_CONSTRAINTS = [
    {
        "id": "ENV001",
        "rule": "AGENT_DIR path is ~/.localagent-dev",
        "severity": "CRITICAL",
        "check": "path_immutable"
    },
    {
        "id": "ENV002", 
        "rule": "API_KEY_FILE is AGENT_DIR/api_key",
        "severity": "CRITICAL",
        "check": "path_immutable"
    },
    {
        "id": "ENV003",
        "rule": "NEVER delete source without snapshot BEFORE",
        "severity": "CRITICAL",
        "check": "snapshot_required"
    },
    {
        "id": "ENV004",
        "rule": "ALWAYS increment version on commit",
        "severity": "CRITICAL",
        "check": "version_increment"
    },
    {
        "id": "ENV005",
        "rule": "NEVER modify .min.js or .min.css files",
        "severity": "CRITICAL",
        "check": "file_protected"
    },
    {
        "id": "ENV006",
        "rule": "Python 3.9 compatible - no match/case",
        "severity": "HIGH",
        "check": "syntax_compatible"
    },
    {
        "id": "ENV007",
        "rule": "Port 5000 blocked by AirPlay - use 5001+",
        "severity": "MEDIUM",
        "check": "port_available"
    },
    {
        "id": "ENV008",
        "rule": "Use pip3 not pip",
        "severity": "MEDIUM",
        "check": "command_alias"
    },
    {
        "id": "ENV009",
        "rule": "GitHub is source of truth for history",
        "severity": "HIGH",
        "check": "git_sync"
    },
    {
        "id": "ENV010",
        "rule": "Errors must be learned - never repeat same mistake",
        "severity": "CRITICAL",
        "check": "error_learning"
    },
    {
        "id": "ENV011",
        "rule": "Console errors queued to backlog - not direct injection",
        "severity": "HIGH",
        "check": "error_to_backlog"
    },
    {
        "id": "ENV012",
        "rule": "Version ONLY from GitHub - no guessing",
        "severity": "CRITICAL",
        "check": "version_from_github"
    },
    {
        "id": "ENV013",
        "rule": "Verify asset uploaded after GitHub release",
        "severity": "HIGH",
        "check": "asset_verification"
    },
    {
        "id": "ENV014",
        "rule": "Snapshot MUST exist before destructive action",
        "severity": "CRITICAL",
        "check": "snapshot_before_destructive"
    },
    {
        "id": "ENV015",
        "rule": "Version info injected in every Claude conversation",
        "severity": "HIGH",
        "check": "version_in_context"
    },
]


# ============================================================
# CTX CONSTRAINTS - Comportementales (par contexte)
# ============================================================

CTX_CONSTRAINTS = [
    {
        "id": "CTX001",
        "rule": "Claude response must be valid JSON only - no markdown",
        "severity": "CRITICAL",
        "check": "json_valid"
    },
    {
        "id": "CTX002",
        "rule": "Strip ```json``` blocks from Claude response",
        "severity": "HIGH",
        "check": "strip_markdown"
    },
    {
        "id": "CTX003",
        "rule": "Max 3 tasks per Claude request",
        "severity": "HIGH",
        "check": "task_limit"
    },
    {
        "id": "CTX004",
        "rule": "Max 50 lines per task",
        "severity": "HIGH",
        "check": "line_limit"
    },
    {
        "id": "CTX005",
        "rule": "NEVER reference files not in context",
        "severity": "HIGH",
        "check": "file_in_context"
    },
    {
        "id": "CTX006",
        "rule": "Auto-split complex instructions (>3 parts)",
        "severity": "MEDIUM",
        "check": "instruction_complexity"
    },
    {
        "id": "CTX007",
        "rule": "Conversation history stored per project",
        "severity": "MEDIUM",
        "check": "conversation_scope"
    },
    {
        "id": "CTX008",
        "rule": "Learned errors stored per project",
        "severity": "HIGH",
        "check": "learning_scope"
    },
    {
        "id": "CTX009",
        "rule": "Negotiation max 3 retries per request",
        "severity": "HIGH",
        "check": "retry_limit"
    },
    {
        "id": "CTX010",
        "rule": "LocalAgent itself is a project (LOCALAGENT)",
        "severity": "MEDIUM",
        "check": "self_reference"
    },
    {
        "id": "CTX011",
        "rule": "MUST check /api/health version match BEFORE any work",
        "severity": "CRITICAL",
        "check": "version_check_before_work",
        "learned_from": "session_2026-01-23: Local 3.0.66 vs GitHub 3.0.68 caused confusion"
    },
    {
        "id": "CTX012",
        "rule": "MUST test locally in browser BEFORE any push/release",
        "severity": "CRITICAL",
        "check": "test_before_push",
        "learned_from": "session_2026-01-23: Module v1.2.0 pushed without test broke dashboard"
    },
    {
        "id": "CTX013",
        "rule": "MUST verify imports when adding code using new classes",
        "severity": "HIGH",
        "check": "import_verification",
        "learned_from": "session_2026-01-23: Response class used without import caused 500 error"
    },
]


# ============================================================
# CONSTRAINT VALIDATION
# ============================================================

def get_all_constraints() -> List[Dict]:
    """Get all constraints (ENV + CTX)."""
    return ENV_CONSTRAINTS + CTX_CONSTRAINTS


def get_constraint(constraint_id: str) -> Dict:
    """Get specific constraint by ID."""
    for c in get_all_constraints():
        if c["id"] == constraint_id:
            return c
    return None


def validate_action(action: str, context: Dict) -> Tuple[bool, List[str]]:
    """
    Validate action against all applicable constraints.
    
    Args:
        action: Type of action (modify_file, delete, commit, call_claude, etc.)
        context: Action context (file path, content, etc.)
    
    Returns:
        (is_valid, list of violations)
    """
    violations = []
    
    # ENV005: Protected files
    file_path = context.get("file", "")
    if file_path:
        if ".min.js" in file_path or ".min.css" in file_path:
            violations.append("ENV005: Cannot modify minified files")
    
    # ENV006: Python 3.9 syntax
    content = context.get("content", "")
    if content:
        if "match " in content and "case " in content:
            violations.append("ENV006: match/case not compatible with Python 3.9")
    
    # ENV003: Snapshot required before delete
    if action == "delete" and not context.get("snapshot_created"):
        violations.append("ENV003: Snapshot required before delete")
    
    # ENV004: Version increment on commit
    if action == "commit" and not context.get("version_incremented"):
        violations.append("ENV004: Version must be incremented on commit")
    
    # CTX003: Task limit
    tasks = context.get("tasks", [])
    if len(tasks) > 3:
        violations.append("CTX003: Max 3 tasks per request")
    
    # CTX004: Line limit per task
    for task in tasks:
        lines = task.get("content", "").count("\n") + 1
        if lines > 50:
            violations.append(f"CTX004: Task {task.get('id', '?')} exceeds 50 lines")
    
    # CTX009: Retry limit
    retry_count = context.get("retry_count", 0)
    if retry_count > 3:
        violations.append("CTX009: Max 3 retries exceeded")
    
    # ENV012: Version from GitHub only
    if action == "set_version" and not context.get("version_from_github"):
        violations.append("ENV012: Version must come from GitHub - no guessing")
    
    # ENV014: Snapshot before destructive action
    if action in ["delete", "rollback", "overwrite"] and not context.get("snapshot_exists"):
        violations.append("ENV014: Snapshot must exist before destructive action")
    
    # ENV013: Asset verification after release
    if action == "release" and context.get("asset_uploaded") and not context.get("asset_verified"):
        violations.append("ENV013: Asset upload must be verified")
    
    # ENV011: Console errors through backlog
    if action == "inject_error" and context.get("direct_injection"):
        violations.append("ENV011: Console errors must go through backlog, not direct injection")
    
    return len(violations) == 0, violations


def check_before_action(action: str, context: Dict) -> bool:
    """
    Check constraints before executing action.
    Raises exception if critical violation.
    
    Returns True if action can proceed.
    """
    is_valid, violations = validate_action(action, context)
    
    if not is_valid:
        critical = [v for v in violations if v.startswith("ENV00") or "CRITICAL" in v]
        if critical:
            raise ConstraintViolation(critical)
        # Non-critical: warn but allow
        for v in violations:
            print(f"⚠️ Constraint warning: {v}")
    
    return True


class ConstraintViolation(Exception):
    """Exception raised when critical constraint is violated."""
    def __init__(self, violations: List[str]):
        self.violations = violations
        super().__init__(f"Constraint violations: {', '.join(violations)}")


# ============================================================
# SYSTEM PROMPT GENERATION (from constraints + learned errors)
# ============================================================

def build_system_prompt(project: str = None) -> str:
    """
    Build system prompt from CTX constraints and learned errors.
    
    This is the SINGLE SOURCE OF TRUTH for Claude's behavior rules.
    The prompt is derived from:
    1. CTX constraints (behavioral rules)
    2. Learned errors from past failures (auto-learning)
    3. Console errors from debugger (runtime issues)
    
    Args:
        project: Project name for loading learned errors
    
    Returns:
        Complete system prompt for Claude
    """
    lines = [
        "You are a code generation assistant. You MUST follow these rules STRICTLY.",
        "",
        "=== RESPONSE FORMAT (MANDATORY) ===",
        "Respond ONLY with valid JSON. No markdown, no explanations.",
        "",
        "{",
        '  "tasks": [',
        "    {",
        '      "id": "T001",',
        '      "type": "create_file",',
        '      "description": "Brief description",',
        '      "filename": "example.html",',
        '      "content": "COMPLETE file content - never truncated"',
        "    }",
        "  ]",
        "}",
        "",
        "=== CONSTRAINTS (from system) ===",
    ]
    
    # Add CTX constraints
    for c in CTX_CONSTRAINTS:
        if c["severity"] in ("CRITICAL", "HIGH"):
            lines.append(f"- [{c['id']}] {c['rule']}")
    
    # Add learned errors if project provided
    if project:
        from .learning import load_learned_errors
        
        errors = load_learned_errors(project)
        error_list = errors.get("errors", [])
        
        if error_list:
            lines.append("")
            lines.append("=== LEARNED ERRORS (do not repeat) ===")
            
            # Get most frequent/recent errors
            sorted_errors = sorted(error_list, key=lambda e: e.get("count", 0), reverse=True)
            for err in sorted_errors[:5]:
                err_type = err.get("type", "unknown")
                err_msg = err.get("message", "")[:80]
                solution = err.get("solution", "")
                
                if solution:
                    lines.append(f"- {err_type}: {err_msg} → FIX: {solution}")
                else:
                    lines.append(f"- {err_type}: {err_msg} → AVOID THIS")
    
    # Add console errors from debugger (runtime issues)
    from .debugger import get_pending_errors
    console_errors = get_pending_errors()
    
    if console_errors:
        lines.append("")
        lines.append("=== CONSOLE ERRORS (fix these in generated code) ===")
        
        for err in console_errors[:5]:  # Last 5 pending errors
            source = err.get("source", "unknown")
            error_data = err.get("error", {})
            msg = error_data.get("message", "Unknown error")[:100]
            file_info = ""
            if error_data.get("file") and error_data.get("line"):
                file_info = f" @ {error_data['file']}:{error_data['line']}"
            
            lines.append(f"- [{source.upper()}] {msg}{file_info}")
            
            # Add stack trace hint if available
            stack = error_data.get("stack", "")
            if stack:
                first_line = stack.split("\n")[0][:80] if stack else ""
                if first_line:
                    lines.append(f"    Stack: {first_line}")
    
    lines.append("")
    lines.append("=== CRITICAL RULES ===")
    lines.append("1. Response MUST start with { and end with }")
    lines.append("2. For create_file: include COMPLETE content (NEVER truncate)")
    lines.append("3. Max 3 tasks per response")
    lines.append("4. Each task MUST have: id, type, description, filename, content")
    
    return "\n".join(lines)


def get_constraints_for_context() -> str:
    """Get constraints formatted for injection into Claude context."""
    lines = ["ACTIVE CONSTRAINTS:"]
    
    for c in get_all_constraints():
        if c["severity"] in ("CRITICAL", "HIGH"):
            lines.append(f"- [{c['id']}] {c['rule']}")
    
    return "\n".join(lines)


# ============================================================
# DISPLAY
# ============================================================

def show_constraints():
    """Display all constraints."""
    print("\n🔒 ENV CONSTRAINTS (System - IMMUTABLE):")
    print("-" * 60)
    for c in ENV_CONSTRAINTS:
        sev_icon = "🔴" if c["severity"] == "CRITICAL" else "🟠" if c["severity"] == "HIGH" else "🟡"
        print(f"  {sev_icon} [{c['id']}] {c['rule']}")
    
    print("\n📋 CTX CONSTRAINTS (Behavioral):")
    print("-" * 60)
    for c in CTX_CONSTRAINTS:
        sev_icon = "🔴" if c["severity"] == "CRITICAL" else "🟠" if c["severity"] == "HIGH" else "🟡"
        print(f"  {sev_icon} [{c['id']}] {c['rule']}")
    print()
