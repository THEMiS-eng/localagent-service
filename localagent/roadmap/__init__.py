"""
LocalAgent - ROADMAP Module
Advanced Prompt Linter & Optimizer
"""

from .prompt_optimizer import (
    lint_prompt,
    optimize_prompt,
    preprocess_for_negotiation,
    get_lint_summary,
    detect_language,
    infer_task_type,
    calculate_specificity,
    estimate_tokens,
    LINT_RULES
)

__all__ = [
    "lint_prompt",
    "optimize_prompt",
    "preprocess_for_negotiation",
    "get_lint_summary",
    "detect_language",
    "infer_task_type",
    "calculate_specificity",
    "estimate_tokens",
    "LINT_RULES"
]
