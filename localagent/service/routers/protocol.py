"""
Protocol Router - handles protocol execution history
"""
from fastapi import APIRouter
from typing import Dict, Any, List
from datetime import datetime

router = APIRouter(prefix="/api/protocol", tags=["protocol"])

# In-memory execution history
_execution_history: List[Dict] = []


def record_execution(execution: Dict):
    """Record a protocol execution."""
    _execution_history.append({
        **execution,
        "timestamp": datetime.now().isoformat()
    })
    # Keep last 100
    if len(_execution_history) > 100:
        _execution_history.pop(0)


@router.get("/history")
async def get_protocol_history():
    """Get protocol execution history."""
    return {"executions": _execution_history[-20:], "total": len(_execution_history)}


@router.get("/steps")
async def get_protocol_steps():
    """Get available protocol steps."""
    from ...core.protocol import PROTOCOL_STEPS
    return {"steps": PROTOCOL_STEPS}


@router.post("/notify")
async def notify_protocol_event(data: Dict[str, Any]):
    """Notify protocol event."""
    event = {
        "type": data.get("type", "unknown"),
        "step": data.get("step"),
        "status": data.get("status"),
        "data": data.get("data")
    }
    record_execution(event)
    return {"recorded": True, "event": event}


@router.post("/build-context")
async def build_context_preview(data: Dict[str, Any]):
    """
    Preview the context that would be built for a TODO.
    
    This allows testing skill matching and context injection without
    actually executing the protocol.
    
    Args:
        todo_title: The TODO title/description
        project: Project name (optional, default: LOCALAGENT)
        github_repo: GitHub repo (optional)
    
    Returns:
        - matched_skills: Skills that match the TODO
        - case_context: Active case context
        - system_prompt_preview: First 2000 chars of system prompt
    """
    from ...core.protocol import ProtocolExecutor
    from ...core.case_context import get_case_context_manager
    
    todo_title = data.get("todo_title", "")
    project = data.get("project", "LOCALAGENT")
    github_repo = data.get("github_repo", "THEMiS-eng/localagent")
    
    if not todo_title:
        return {"error": "todo_title required"}
    
    # Create executor just to use its methods
    executor = ProtocolExecutor(project, github_repo)
    
    # Match skills
    matched_skills = executor._match_skills_for_todo(todo_title)
    
    # Get case context
    case_ctx = None
    skill_ctx = None
    try:
        ctx_manager = get_case_context_manager()
        ctx = ctx_manager.get_context()
        case_ctx = ctx.to_dict()
        skill_ctx = ctx_manager.get_skill_context()
    except:
        pass
    
    # Get templates for top skills
    templates = []
    for match in matched_skills[:3]:
        template = executor._get_skill_template(match["skill"], todo_title)
        if template:
            templates.append({
                "skill": match["skill"],
                "template_preview": template[:500] + "..." if len(template) > 500 else template
            })
    
    return {
        "todo_title": todo_title,
        "matched_skills": matched_skills[:5],
        "case_context": case_ctx,
        "skill_context": skill_ctx,
        "templates": templates,
        "total_skills_matched": len(matched_skills)
    }


@router.post("/execute")
async def execute_protocol(data: Dict[str, Any]):
    """
    Execute the full 13-step protocol for a TODO.
    
    Steps: fetch_github_version → calculate_next_version → create_snapshot_before →
           build_claude_context → call_claude → validate_response → execute_tasks →
           create_snapshot_after → git_commit → git_push → create_github_release →
           verify_release → mark_todo_done
    """
    from ...core.protocol import ProtocolExecutor
    from ...connectors.llm import call_claude
    
    todo_id = data.get("todo_id")
    todo_title = data.get("todo_title")
    instruction = data.get("instruction", "")  # Explicit instruction for task matching
    project = data.get("project", "LOCALAGENT")
    github_repo = data.get("github_repo", "THEMiS-eng/localagent-service")
    
    if not todo_id or not todo_title:
        return {"error": "todo_id and todo_title required"}
    
    # Create executor and set Claude function
    executor = ProtocolExecutor(project, github_repo)
    executor.set_claude_function(call_claude)
    executor.set_instruction(instruction or todo_title)  # Use instruction or fallback to title
    
    # Execute full 13-step protocol
    execution = executor.execute_todo(todo_id, todo_title)
    
    return {
        "status": execution.status,
        "execution_id": execution.execution_id,
        "todo_id": todo_id,
        "steps": [
            {
                "id": s.step_id,
                "name": s.name,
                "status": s.status,
                "error": s.error
            } for s in execution.steps
        ],
        "violations": execution.violations,
        "files_created": execution.files_created
    }


@router.post("/validate-output")
async def validate_output(data: Dict[str, Any]):
    """
    Validate an LLM output against skill constraints.
    
    This is the Negotiator's skill constraint validation.
    
    Args:
        output: The LLM response text to validate
        skill_name: Name of the skill to validate against
        strict: If True, fail on medium severity violations too
    
    Returns:
        {
            "valid": bool,
            "violations": [...],
            "warnings": [...],
            "score": int,
            "feedback": str
        }
    """
    from ...core.negotiator import validate_output_against_skill
    from ...skills import get_manager
    
    output = data.get("output", "")
    skill_name = data.get("skill_name")
    strict = data.get("strict", False)
    
    if not output:
        return {"error": "output is required"}
    
    if not skill_name:
        return {"error": "skill_name is required"}
    
    # Get skill body
    manager = get_manager()
    manager.discover()
    skill = manager.get_skill(skill_name)
    
    if not skill:
        return {"error": f"Skill '{skill_name}' not found"}
    
    skill_body = skill.body or ""
    
    # Validate
    result = validate_output_against_skill(
        output=output,
        skill_name=skill_name,
        skill_body=skill_body,
        strict=strict
    )
    
    return result


@router.post("/negotiate")
async def negotiate_response(data: Dict[str, Any]):
    """
    Full negotiation cycle: validate output and get retry prompt if needed.
    
    Args:
        output: The LLM response
        skill_name: Active skill
        original_prompt: The original prompt (for building retry)
        strict: Strict validation mode
    
    Returns:
        {
            "needs_retry": bool,
            "validation": {...},
            "retry_prompt": str (if needs_retry)
        }
    """
    from ...core.negotiator import (
        validate_output_against_skill,
        build_retry_prompt_with_skill_feedback
    )
    from ...skills import get_manager
    
    output = data.get("output", "")
    skill_name = data.get("skill_name")
    original_prompt = data.get("original_prompt", "")
    strict = data.get("strict", False)
    
    if not output or not skill_name:
        return {"error": "output and skill_name are required"}
    
    # Get skill
    manager = get_manager()
    manager.discover()
    skill = manager.get_skill(skill_name)
    
    if not skill:
        return {"error": f"Skill '{skill_name}' not found"}
    
    skill_body = skill.body or ""
    
    # Validate
    validation = validate_output_against_skill(
        output=output,
        skill_name=skill_name,
        skill_body=skill_body,
        strict=strict
    )
    
    needs_retry = not validation["valid"]
    retry_prompt = ""
    
    if needs_retry and original_prompt:
        retry_prompt = build_retry_prompt_with_skill_feedback(
            original_prompt=original_prompt,
            output=output,
            validation_result=validation,
            skill_name=skill_name
        )
    
    return {
        "needs_retry": needs_retry,
        "validation": validation,
        "retry_prompt": retry_prompt
    }
