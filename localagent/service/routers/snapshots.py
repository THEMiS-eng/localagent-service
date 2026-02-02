"""
Snapshots Router - handles project snapshots and validation
"""
from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(prefix="/api", tags=["snapshots"])

DEFAULT_PROJECT = "LOCALAGENT"


@router.get("/snapshots")
async def get_snapshots():
    """Get project snapshots."""
    from ...engine.project import list_snapshots
    snapshots = list_snapshots(DEFAULT_PROJECT)
    return {"snapshots": snapshots, "count": len(snapshots)}


@router.post("/snapshots")
async def create_snapshot(data: Dict[str, Any]):
    """Create a snapshot."""
    from ...engine.project import create_snapshot
    label = data.get("label", "manual")
    snapshot_id = create_snapshot(DEFAULT_PROJECT, label)
    return {"id": snapshot_id, "label": label}


@router.get("/snapshots/verify")
async def verify_snapshots():
    """Verify snapshot integrity."""
    from ...engine.project import list_snapshots
    from pathlib import Path
    
    snapshots = list_snapshots(DEFAULT_PROJECT)
    results = []
    for s in snapshots:
        snapshot_dir = Path.home() / ".localagent" / "projects" / DEFAULT_PROJECT / "snapshots" / s.get("id", "")
        exists = snapshot_dir.exists() if s.get("id") else False
        results.append({"id": s.get("id"), "valid": exists})
    
    return {"snapshots": results, "total": len(results)}


@router.post("/snapshots/validate-action")
async def validate_action(data: Dict[str, Any]):
    """Validate an action against constraints."""
    from ...core.constraints import validate_action
    action = data.get("action", "")
    context = data.get("context", {})
    valid, violations = validate_action(action, context)
    return {"valid": valid, "violations": violations}
