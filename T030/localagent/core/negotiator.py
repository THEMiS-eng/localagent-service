"""
LocalAgent v2.10.17 - CORE: Negotiator
🧠 SMART - Négocie avec Claude, retry intelligent, auto-split

Stratégies de négociation basées sur le type d'erreur
Utilise le learning pour améliorer les prompts
"""

import re
from typing import Dict, List, Tuple, Optional

from .constraints import validate_action, CTX_CONSTRAINTS, build_system_prompt
from .learning import (
    learn_from_error,
    learn_dodge,
    get_error_context_for_retry,
    has_learned_solution
)


# ============================================================
# NEGOTIATION STRATEGIES
# ============================================================

NEGOTIATION_STRATEGIES = {
    "truncation": {
        "action": "reduce_complexity",
        "feedback": "Response truncated. Use fewer, simpler tasks. Max 2 tasks, max 20 lines each.",
        "max_retries": 3
    },
    "parse_error": {
        "action": "simplify_json",
        "feedback": "JSON parse error. Return ONLY valid JSON. Start with { end with }. No markdown.",
        "max_retries": 3
    },
    "empty_response": {
        "action": "retry_simple",
        "feedback": "Empty response received. Please provide tasks in JSON format.",
        "max_retries": 2
    },
    "no_tasks": {
        "action": "clarify_format",
        "feedback": "No tasks found. Return: {\"tasks\": [{\"id\": \"T001\", \"type\": \"...\", ...}]}",
        "max_retries": 2
    },
    "invalid_task": {
        "action": "fix_schema",
        "feedback": "Task missing required fields. Each task needs: id, type, description",
        "max_retries": 2
    },
    "file_not_found": {
        "action": "list_available",
        "feedback": "File not found. Only reference files explicitly listed in context.",
        "max_retries": 1
    },
    "too_complex": {
        "action": "split_instruction",
        "feedback": "Instruction too complex. Will be split into smaller parts.",
        "max_retries": 0
    },
    "dodge_detected": {
        "action": "insist",
        "feedback": "Do not refuse or ask for clarification. Execute the task as specified.",
        "max_retries": 2
    },
    "file_modification_violation": {
        "action": "enforce_target_file",
        "feedback": "You must modify the specified target file only. Do not create new files or test files.",
        "max_retries": 2
    }
}