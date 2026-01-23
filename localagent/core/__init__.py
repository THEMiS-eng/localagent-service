"""
LocalAgent v3.0.30 - CORE Module
🎯 Orchestrator + 🔑 Constraints + 🧠 Learning + 🧠 Negotiator + 🐛 Debugger + 🔐 Protocol

RULE: All TODO processing MUST go through protocol.py
Protocol enforces ENV012 (version from GitHub) and all other constraints.
"""

from .constraints import (
    ENV_CONSTRAINTS,
    CTX_CONSTRAINTS,
    get_all_constraints,
    get_constraint,
    validate_action,
    check_before_action,
    ConstraintViolation,
    build_system_prompt,
    get_constraints_for_context,
    show_constraints
)

from .learning import (
    load_learned_errors,
    save_learned_errors,
    learn_from_error,
    learn_dodge,
    get_similar_errors,
    get_error_pattern_count,
    has_learned_solution,
    get_error_context_for_retry,
    show_learned_errors,
    resolve_error_as_bugfix
)

from .negotiator import (
    NEGOTIATION_STRATEGIES,
    analyze_instruction_complexity,
    get_negotiation_feedback,
    should_retry,
    get_retry_action,
    detect_dodge,
    negotiate_request,
    validate_response
)

from .orchestrator import (
    orchestrate,
    call_llm,
    github_clone,
    github_sync,
    create_file,
    commit,
    execute_tasks,
    get_state,
    git_sync_to_remote,
    OrchestratorState
)

from .debugger import (
    log_error,
    get_pending_errors,
    mark_error_fixed,
    format_errors_for_claude,
    auto_debug_check,
    show_debug_status
)

from .protocol import (
    ProtocolStep,
    ProtocolExecution,
    ProtocolExecutor,
    PROTOCOL_STEPS,
    process_todo_with_protocol
)

__all__ = [
    # === ORCHESTRATOR (PRIMARY INTERFACE) ===
    "orchestrate",           # Main entry point for all operations
    "call_llm",              # LLM calls with error learning
    "github_clone",          # GitHub clone with snapshots
    "github_sync",           # GitHub sync with snapshots
    "create_file",           # File creation with constraints
    "commit",                # Commit with git integration
    "execute_tasks",         # Task execution
    "get_state",             # Orchestrator state
    "git_sync_to_remote",    # Full GitHub push (commit, branch, push, tag)
    "OrchestratorState",
    
    # === CONSTRAINTS ===
    "ENV_CONSTRAINTS", "CTX_CONSTRAINTS", "get_all_constraints", "get_constraint",
    "validate_action", "check_before_action", "ConstraintViolation", 
    "build_system_prompt", "get_constraints_for_context", "show_constraints",
    
    # === LEARNING ===
    "load_learned_errors", "save_learned_errors", "learn_from_error", "learn_dodge",
    "get_similar_errors", "get_error_pattern_count", "has_learned_solution",
    "get_error_context_for_retry", "show_learned_errors", "resolve_error_as_bugfix",
    
    # === NEGOTIATOR (used internally by orchestrator) ===
    "NEGOTIATION_STRATEGIES", "analyze_instruction_complexity", "get_negotiation_feedback",
    "should_retry", "get_retry_action", "detect_dodge", "negotiate_request", "validate_response",
    
    # === DEBUGGER ===
    "log_error", "get_pending_errors", "mark_error_fixed", 
    "format_errors_for_claude", "auto_debug_check", "show_debug_status"
]
