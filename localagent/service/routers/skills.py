"""
LocalAgent - SERVICE: Skills Router
API endpoints for skill management (Anthropic SKILL.md format)

Endpoints:
- GET  /api/skills           - List available skills
- GET  /api/skills/active    - Get active skills
- POST /api/skills/activate  - Activate a skill
- POST /api/skills/deactivate - Deactivate a skill
- GET  /api/skills/{name}    - Get skill details
- GET  /api/skills/{name}/references/{ref} - Get skill reference doc
- GET  /api/skills/status    - Get system status
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/skills", tags=["skills"])


# Request/Response Models

class ActivateRequest(BaseModel):
    skill_name: str


class DeactivateRequest(BaseModel):
    skill_name: str


# Endpoints

@router.get("")
async def list_skills():
    """
    List available skills in skills directory.
    
    Returns:
        List of available skills with metadata
    """
    from ...skills import get_manager
    
    manager = get_manager()
    manager.discover()
    
    skills = []
    for skill in manager.get_available():
        skills.append({
            "name": skill.name,
            "description": skill.description[:200] + "..." if len(skill.description) > 200 else skill.description,
            "active": skill.active,
            "path": str(skill.path),
            "has_scripts": skill.scripts_dir is not None,
            "has_references": skill.references_dir is not None,
            "has_assets": skill.assets_dir is not None
        })
    
    return {
        "skills": skills,
        "count": len(skills),
        "skills_directory": str(manager.skills_dir)
    }


@router.get("/active")
async def get_active_skills():
    """
    Get currently active skills.
    
    Returns:
        List of active skill names and details
    """
    from ...skills import get_manager
    
    manager = get_manager()
    
    return {
        "active": [
            {
                "name": s.name,
                "description": s.description[:100] + "..." if len(s.description) > 100 else s.description,
                "loaded_at": s.loaded_at.isoformat() if s.loaded_at else None,
            }
            for s in manager.get_active()
        ],
        "count": len(manager.get_active())
    }


@router.post("/activate")
async def activate_skill(request: ActivateRequest):
    """
    Activate a skill by name.
    
    Args:
        skill_name: Name of skill to activate
        
    Returns:
        Activation result with skill details
    """
    from ...skills import get_manager
    
    manager = get_manager()
    
    # Ensure skills are discovered
    if not manager.get_available():
        manager.discover()
    
    success = manager.activate(request.skill_name)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Skill not found: {request.skill_name}"
        )
    
    skill = manager.get_skill(request.skill_name)
    
    return {
        "success": True,
        "skill": {
            "name": skill.name,
            "description": skill.description,
            "scripts": [p.name for p in skill.get_scripts()],
            "references": [p.name for p in skill.get_references()]
        },
        "active_count": len(manager.get_active())
    }


@router.post("/deactivate")
async def deactivate_skill(request: DeactivateRequest):
    """
    Deactivate a skill by name.
    
    Args:
        skill_name: Name of skill to deactivate
        
    Returns:
        Deactivation result
    """
    from ...skills import get_manager
    
    manager = get_manager()
    success = manager.deactivate(request.skill_name)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Skill not active: {request.skill_name}"
        )
    
    return {
        "success": True,
        "deactivated": request.skill_name,
        "active_count": len(manager.get_active())
    }


@router.get("/status")
async def get_status():
    """
    Get skill system status.
    
    Returns:
        System status with available and active skill counts
    """
    from ...skills import get_manager
    
    manager = get_manager()
    
    return {
        "skills_directory": str(manager.skills_dir),
        "directory_exists": manager.skills_dir.exists(),
        "available_count": len(manager.get_available()),
        "active_count": len(manager.get_active()),
        "active_skills": [s.name for s in manager.get_active()]
    }


@router.get("/context")
async def get_context():
    """
    Get the skill context for LLM injection.
    
    Returns:
        Formatted context string from active skills
    """
    from ...skills import build_skill_context
    
    context = build_skill_context()
    
    return {
        "context": context,
        "length": len(context)
    }


@router.get("/{skill_name}")
async def get_skill_details(skill_name: str):
    """
    Get detailed information about a skill.
    
    Args:
        skill_name: Name of skill
        
    Returns:
        Full skill details including body content
    """
    from ...skills import get_manager
    
    manager = get_manager()
    skill = manager.get_skill(skill_name)
    
    if not skill:
        # Try to discover and load
        manager.discover()
        skill = manager.get_skill(skill_name)
    
    if not skill:
        raise HTTPException(
            status_code=404,
            detail=f"Skill not found: {skill_name}"
        )
    
    return {
        "name": skill.name,
        "description": skill.description,
        "active": skill.active,
        "path": str(skill.path),
        "body": skill.body,
        "scripts": [
            {"name": p.name, "path": str(p)}
            for p in skill.get_scripts()
        ],
        "references": [
            {"name": p.name, "path": str(p)}
            for p in skill.get_references()
        ],
        "assets": [
            {"name": p.name, "path": str(p)}
            for p in skill.get_assets()[:20]  # Limit to 20
        ]
    }


@router.get("/{skill_name}/references/{ref_name}")
async def get_skill_reference(skill_name: str, ref_name: str):
    """
    Get a reference document from a skill.
    
    Args:
        skill_name: Name of skill
        ref_name: Name of reference document
        
    Returns:
        Reference document content
    """
    from ...skills import get_manager
    
    manager = get_manager()
    skill = manager.get_skill(skill_name)
    
    if not skill:
        raise HTTPException(
            status_code=404,
            detail=f"Skill not found: {skill_name}"
        )
    
    content = skill.read_reference(ref_name)
    
    if content is None:
        raise HTTPException(
            status_code=404,
            detail=f"Reference not found: {ref_name}"
        )
    
    return {
        "skill": skill_name,
        "reference": ref_name,
        "content": content
    }


@router.post("/discover")
async def discover_skills():
    """
    Force re-discovery of skills.
    
    Returns:
        List of discovered skills
    """
    from ...skills import get_manager
    
    manager = get_manager()
    skills = manager.discover()
    
    return {
        "discovered": len(skills),
        "skills": [s.name for s in skills]
    }


# ============================================================
# CASE CONTEXT ENDPOINTS
# ============================================================

class CaseContextRequest(BaseModel):
    """Request model for setting case context."""
    case_id: Optional[str] = None
    case_name: Optional[str] = None
    framework: Optional[str] = None
    methodology: Optional[str] = None
    jurisdiction: Optional[str] = None
    contract_type: Optional[str] = None
    contract_ref: Optional[str] = None
    dispute_type: Optional[str] = None
    forum: Optional[str] = None
    client: Optional[str] = None
    opponent: Optional[str] = None
    special_skills: Optional[List[str]] = None


@router.get("/context")
async def get_case_context():
    """
    Get the active case context.
    
    Returns:
        Current case context that influences skill behavior
    """
    from ...core.case_context import get_case_context_manager
    
    manager = get_case_context_manager()
    context = manager.get_context()
    
    return {
        "context": context.to_dict(),
        "skill_context": manager.get_skill_context()
    }


@router.post("/context")
async def set_case_context(request: CaseContextRequest):
    """
    Set or update the active case context.
    
    This context is injected into all skills to adapt their behavior
    based on the case's framework, methodology, jurisdiction, etc.
    """
    from ...core.case_context import get_case_context_manager
    
    manager = get_case_context_manager()
    
    # Update only provided fields
    updates = {k: v for k, v in request.dict().items() if v is not None}
    if updates:
        manager.update_context(**updates)
    
    return {
        "status": "updated",
        "context": manager.get_context().to_dict()
    }


@router.post("/context/from-case")
async def set_context_from_case(case_data: Dict[str, Any]):
    """
    Set context from a THEMIS CASE object.
    
    This is called when switching cases in THEMIS to sync the context.
    """
    from ...core.case_context import get_case_context_manager
    
    manager = get_case_context_manager()
    manager.set_from_case(case_data)
    
    return {
        "status": "synced",
        "case_id": case_data.get("id"),
        "context": manager.get_context().to_dict()
    }


@router.delete("/context")
async def clear_case_context():
    """Clear the active case context."""
    from ...core.case_context import get_case_context_manager
    
    manager = get_case_context_manager()
    manager.clear()
    
    return {"status": "cleared"}

