"""
LocalAgent - SERVICE: LLM Providers Router
API endpoints for LLM provider management

Endpoints:
- GET  /api/llm/providers       - List all providers with status
- GET  /api/llm/active          - Get active provider
- POST /api/llm/provider        - Set active provider
- POST /api/llm/complete        - Send completion request
- POST /api/llm/improve-prompt  - Improve prompt via Anthropic API
- GET  /api/llm/status          - Get LLM system status
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import json
import urllib.request
import logging

logger = logging.getLogger(__name__)

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


class ImprovePromptRequest(BaseModel):
    prompt: str
    system: Optional[str] = ""
    feedback: Optional[str] = ""
    skill_name: Optional[str] = None
    tier: Optional[str] = "intermediate"  # beginner, intermediate, advanced
    issues: Optional[List[Dict[str, Any]]] = []


TIER_INSTRUCTIONS = {
    "beginner": "Simplify and clarify the prompt. Fix grammar, remove ambiguity, add basic structure. Keep it short and direct.",
    "intermediate": "Restructure with clear sections using XML tags. Add reasoning instructions, ensure specificity, and organize for optimal LLM processing.",
    "advanced": "Full expert rewrite. Use structured XML sections with <context>, <task>, <constraints>, <output_format> tags. Add chain-of-thought reasoning instructions, methodology references, case context variables, and expert-level formatting for maximum analytical depth."
}


@router.post("/improve-prompt")
async def improve_prompt(request: ImprovePromptRequest):
    """
    Improve a prompt using Anthropic's Prompt Improver API.
    Falls back to Claude completion with metaprompt if experimental API unavailable.

    Args:
        prompt: The prompt to improve
        system: Optional system prompt context
        feedback: Optional specific improvement guidance
        skill_name: Active skill for context injection
        tier: Optimization level (beginner, intermediate, advanced)
        issues: Linter-detected issues array

    Returns:
        Improved prompt with source info
    """
    from ...connectors.llm import get_api_key
    from ...connectors.llm_providers import get_llm_manager

    # Build feedback from linter issues + tier
    feedback_parts = []
    if request.feedback:
        feedback_parts.append(request.feedback)
    if request.issues:
        issue_text = "; ".join([
            f"[{i.get('severity', '')}] {i.get('message', '')}: {i.get('fix', '')}"
            for i in request.issues
        ])
        feedback_parts.append(f"Linter detected: {issue_text}")

    tier_instruction = TIER_INSTRUCTIONS.get(request.tier, TIER_INSTRUCTIONS["intermediate"])
    feedback_parts.append(tier_instruction)
    full_feedback = " | ".join(feedback_parts)

    # Get skill context
    skill_context = ""
    if request.skill_name:
        try:
            from ...skills import get_manager as get_skill_manager
            sm = get_skill_manager()
            skill = sm.get_skill(request.skill_name)
            if skill:
                skill_context = f"\n\nActive Skill: {skill.name}\nDomain: {skill.description}"
                if hasattr(skill, 'body') and skill.body:
                    # Include first 500 chars of skill body for context
                    skill_context += f"\nExpertise:\n{skill.body[:500]}"
        except Exception:
            pass

    # --- Attempt 1: Anthropic experimental Prompt Improver API ---
    api_key = get_api_key()
    if api_key:
        try:
            url = "https://api.anthropic.com/v1/experimental/improve_prompt"
            payload = {
                "messages": [{"role": "user", "content": request.prompt}],
                "feedback": full_feedback
            }
            if request.system or skill_context:
                payload["system"] = (request.system or "") + skill_context

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "anthropic-beta": "prompt-tools-2025-04-02",
                    "content-type": "application/json"
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            # Extract improved prompt from response
            improved = ""
            for msg in data.get("messages", []):
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        improved = " ".join([
                            c.get("text", "") for c in content
                            if c.get("type") == "text"
                        ])
                    else:
                        improved = str(content)
                    break

            if improved:
                return {
                    "success": True,
                    "improved": improved,
                    "source": "anthropic-api",
                    "tier": request.tier
                }
        except urllib.error.HTTPError as e:
            logger.info(f"Prompt Improver API returned {e.code}, falling back to metaprompt")
        except Exception as e:
            logger.info(f"Prompt Improver API unavailable ({e}), falling back to metaprompt")

    # --- Attempt 2: Fallback to Claude completion with metaprompt ---
    manager = get_llm_manager()

    metaprompt = f"""You are an expert prompt engineer specializing in optimizing prompts for AI language models.

TASK: Rewrite the user's prompt to be maximally effective.

TIER: {request.tier}
{tier_instruction}
{f"LINTER FEEDBACK: {full_feedback}" if request.issues else ""}
{skill_context}

RULES:
1. Return ONLY the improved prompt text — no explanations, no preamble, no commentary
2. Preserve the user's original intent exactly
3. Make it more specific, structured, and effective
4. Use positive framing (replace negations with affirmatives)
5. Replace vague quantities with specific numbers
6. Add output format specifications if missing
7. For intermediate/advanced: organize with XML tags (<context>, <task>, <constraints>, <output_format>)
8. For advanced: add chain-of-thought instructions and methodology references"""

    result = manager.complete(
        prompt=f"Improve this prompt:\n\n{request.prompt}",
        system=metaprompt,
        fallback=True
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to improve prompt")
        )

    return {
        "success": True,
        "improved": result.get("response", ""),
        "source": "claude-metaprompt",
        "tier": request.tier,
        "provider": result.get("provider")
    }


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
