"""
Lint Router - handles prompt linting and optimization
"""
from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(prefix="/api", tags=["lint"])


@router.post("/lint")
async def lint_prompt_endpoint(data: Dict[str, Any]):
    """Lint a prompt."""
    from fastapi import HTTPException
    from ...roadmap.prompt_optimizer import lint_prompt as do_lint
    prompt = data.get("prompt", "")
    if not prompt or not prompt.strip():
        raise HTTPException(status_code=400, detail="Empty prompt")
    result = do_lint(prompt)
    return result


@router.post("/lint/optimize")
async def optimize_prompt(data: Dict[str, Any]):
    """Optimize a prompt."""
    from ...roadmap.prompt_optimizer import preprocess_for_negotiation
    prompt = data.get("prompt", "")
    project = data.get("project", "LOCALAGENT")
    optimized, report = preprocess_for_negotiation(prompt, project)
    return {"original": prompt, "optimized": optimized, "report": report}


@router.get("/lint/summary")
async def get_lint_summary():
    """Get linting statistics summary."""
    return {
        "total_linted": 0,
        "average_score": 0,
        "common_issues": []
    }
