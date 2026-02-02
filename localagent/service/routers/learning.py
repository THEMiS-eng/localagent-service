"""
Learning Router - handles error learning and constraints
"""
from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(prefix="/api", tags=["learning"])

DEFAULT_PROJECT = "LOCALAGENT"


@router.get("/constraints")
async def get_constraints():
    """Get all constraints."""
    from ...core.constraints import get_all_constraints
    return {"constraints": get_all_constraints()}


@router.post("/constraints/validate")
async def validate_constraints(data: Dict[str, Any]):
    """Validate an action against constraints."""
    from ...core.constraints import validate_action
    action = data.get("action", "")
    context = data.get("context", {})
    valid, violations = validate_action(action, context)
    return {"valid": valid, "violations": violations}


@router.get("/learning/report")
async def get_learning_report():
    """Get learning report."""
    from ...core.learning import load_learned_errors
    errors = load_learned_errors(DEFAULT_PROJECT)
    return {
        "total_learned": len(errors),
        "errors": list(errors.values())[:10] if isinstance(errors, dict) else errors[:10]
    }


@router.get("/learning/patterns")
async def get_learning_patterns():
    """Get learned patterns."""
    from ...core.learning import load_learned_errors
    errors = load_learned_errors(DEFAULT_PROJECT)
    patterns = {}
    error_list = list(errors.values()) if isinstance(errors, dict) else errors
    for e in error_list:
        cat = e.get("category", "unknown") if isinstance(e, dict) else "unknown"
        patterns[cat] = patterns.get(cat, 0) + 1
    return {"patterns": patterns}


@router.post("/learning/error")
async def learn_error(data: Dict[str, Any]):
    """Learn from an error."""
    from ...core.learning import learn_from_error
    project = data.get("project", "LOCALAGENT")
    error_type = data.get("error_type", "unknown")
    error_msg = data.get("error_msg", data.get("error", ""))
    context = data.get("context", {})
    solution = data.get("solution", "")
    result = learn_from_error(project, error_type, error_msg, context, solution)
    return {"learned": result}
