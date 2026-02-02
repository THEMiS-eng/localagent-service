"""
LocalAgent - SERVICE: LLM Providers Router
API endpoints for LLM provider management

Endpoints:
- GET  /api/llm/providers       - List all providers with status
- GET  /api/llm/active          - Get active provider
- POST /api/llm/provider        - Set active provider
- POST /api/llm/complete        - Send completion request
- GET  /api/llm/status          - Get LLM system status
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/llm", tags=["llm"])


# Request/Response Models

class SetProviderRequest(BaseModel):
    provider: str


class CompleteRequest(BaseModel):
    prompt: str
    system: Optional[str] = ""
    context: Optional[str] = ""
    skill_name: Optional[str] = None
    provider: Optional[str] = None
    fallback: bool = True


# Endpoints

@router.get("/providers")
async def list_providers():
    """
    List all LLM providers with availability status.
    
    Returns:
        Dict with provider names and availability
    """
    from ...connectors.llm_providers import get_llm_manager
    
    manager = get_llm_manager()
    
    return {
        "providers": manager.get_all_providers(),
        "available": manager.get_available_providers(),
        "active": manager.get_active_provider()
    }


@router.get("/active")
async def get_active_provider():
    """
    Get the currently active LLM provider.
    
    Returns:
        Active provider name or null
    """
    from ...connectors.llm_providers import get_llm_manager
    
    manager = get_llm_manager()
    active = manager.get_active_provider()
    
    return {
        "active": active,
        "available": manager.get_available_providers()
    }


@router.post("/provider")
async def set_active_provider(request: SetProviderRequest):
    """
    Set the active LLM provider.
    
    Args:
        provider: Name of provider to activate (mlx, claude, openai, ollama)
    
    Returns:
        Success status
    """
    from ...connectors.llm_providers import get_llm_manager
    
    manager = get_llm_manager()
    
    if request.provider not in manager.get_all_providers():
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider: {request.provider}. Available: {list(manager.get_all_providers().keys())}"
        )
    
    success = manager.set_provider(request.provider)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{request.provider}' is not available"
        )
    
    return {
        "success": True,
        "active": request.provider
    }


@router.post("/complete")
async def complete_request(request: CompleteRequest):
    """
    Send a completion request to the LLM.
    
    Args:
        prompt: User prompt
        system: System prompt (optional)
        context: Additional context (optional)
        skill_name: Skill to inject (optional)
        provider: Specific provider to use (optional)
        fallback: Enable fallback on failure (default: true)
    
    Returns:
        Completion response with provider info
    """
    from ...connectors.llm_providers import get_llm_manager
    
    manager = get_llm_manager()
    
    result = manager.complete(
        prompt=request.prompt,
        system=request.system,
        context=request.context,
        skill_name=request.skill_name,
        provider=request.provider,
        fallback=request.fallback
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Completion failed")
        )
    
    return result


@router.get("/status")
async def get_llm_status():
    """
    Get LLM system status.
    
    Returns:
        Full status including providers, active skills, etc.
    """
    from ...connectors.llm_providers import get_llm_manager
    from ...skills import get_manager as get_skill_manager
    
    llm_manager = get_llm_manager()
    skill_manager = get_skill_manager()
    
    return {
        "llm": {
            "providers": llm_manager.get_all_providers(),
            "available": llm_manager.get_available_providers(),
            "active": llm_manager.get_active_provider()
        },
        "skills": {
            "available": [s.name for s in skill_manager.get_available()],
            "active": [s.name for s in skill_manager.get_active()]
        }
    }


@router.post("/test")
async def test_provider(request: SetProviderRequest):
    """
    Test a specific provider with a simple request.
    
    Args:
        provider: Provider name to test
    
    Returns:
        Test result with response time
    """
    from ...connectors.llm_providers import get_llm_manager
    import time
    
    manager = get_llm_manager()
    
    start = time.time()
    result = manager.complete(
        prompt="Say 'Hello' and nothing else.",
        provider=request.provider,
        fallback=False
    )
    elapsed = time.time() - start
    
    return {
        "provider": request.provider,
        "success": result.get("success", False),
        "response": result.get("response", "")[:100],
        "error": result.get("error"),
        "response_time_ms": int(elapsed * 1000)
    }
