"""
LocalAgent - Bugfix Router
Endpoints: /api/bugfix/*
"""

import asyncio
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Query

from ...engine.tracking import (
    get_bugfixes, get_pending_bugfixes, add_bugfix, apply_bugfix,
    generate_release_notes,
)
from ...connectors.github import get_service_version, github_push

router = APIRouter(prefix="/api/bugfix", tags=["bugfix"])

DEFAULT_PROJECT = "LOCALAGENT"

# Cache reference (set by main server)
_cache = None

def set_cache(cache_instance):
    global _cache
    _cache = cache_instance

def cached_get_bugfixes(project: str):
    if _cache:
        key = f"bugfixes:{project}"
        cached = _cache.get(key)
        if cached is not None:
            return cached
    result = get_bugfixes(project)
    if _cache:
        _cache.set(f"bugfixes:{project}", result)
    return result

def invalidate_cache(category: str, project: str):
    if _cache:
        _cache.invalidate(f"{category}:{project}")


# ============================================================
# GET ENDPOINTS
# ============================================================

@router.get("")
async def get_bugfixes_endpoint(project: str = Query(default=None)):
    """Get all bugfixes."""
    return {"bugfixes": cached_get_bugfixes(project or DEFAULT_PROJECT)}

@router.get("/pending")
async def get_pending_bugfixes_endpoint(project: str = Query(default=None)):
    """Get pending bugfixes."""
    return {"bugfixes": get_pending_bugfixes(project or DEFAULT_PROJECT)}


# ============================================================
# POST ENDPOINTS
# ============================================================

@router.post("/add")
async def add_bugfix_endpoint(data: Dict[str, Any]):
    """Add a bugfix entry (records it, doesn't apply yet)."""
    item_id = add_bugfix(
        DEFAULT_PROJECT,
        data.get("title", ""),
        data.get("description", ""),
        data.get("source", "manual")
    )
    invalidate_cache("bugfixes", DEFAULT_PROJECT)
    return {"id": item_id, "status": "pending", "triggers_release": False}

@router.post("/apply")
async def apply_bugfix_endpoint(data: Dict[str, Any]):
    """
    Apply a bugfix - this TRIGGERS a release.
    
    Required:
        - bugfix_id: The bugfix ID (BF001)
        - commit_sha: Git commit SHA (REQUIRED)
        
    Optional:
        - version: Version to release (auto-incremented if not provided)
        - files_changed: List of modified files
        - push: Whether to push to GitHub (default: true)
    """
    from pathlib import Path
    from ...engine.project import increment_version
    
    bugfix_id = data.get("bugfix_id")
    commit_sha = data.get("commit_sha")
    
    if not bugfix_id:
        raise HTTPException(400, "bugfix_id required")
    if not commit_sha:
        raise HTTPException(400, "commit_sha required")
    
    # Get or calculate version
    version = data.get("version")
    if not version:
        github_version = get_service_version()
        parts = github_version.split(".")
        if len(parts) == 3:
            version = f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"
        else:
            version = increment_version(DEFAULT_PROJECT)
    
    # Apply bugfix
    success = apply_bugfix(
        DEFAULT_PROJECT,
        bugfix_id,
        version,
        commit_sha,
        data.get("files_changed", [])
    )
    
    if not success:
        raise HTTPException(404, f"Bugfix {bugfix_id} not found")
    
    invalidate_cache("bugfixes", DEFAULT_PROJECT)
    
    result = {
        "success": True,
        "bugfix_id": bugfix_id,
        "version": version,
        "commit_sha": commit_sha,
        "triggers_release": True,
    }
    
    # Push to GitHub if requested
    if data.get("push", True):
        service_dir = Path.home() / "localagent_v3"
        
        # Update VERSION file
        version_file = service_dir / "VERSION"
        if version_file.exists():
            old_version = version_file.read_text().strip()
            version_file.write_text(version)
        
        # Generate release notes
        release_notes = generate_release_notes(DEFAULT_PROJECT, version)
        
        # Push and create release
        loop = asyncio.get_event_loop()
        push_result = await loop.run_in_executor(
            None,
            lambda: github_push(str(service_dir), "service", version=version, create_release=True)
        )
        
        result["push"] = push_result
        result["release_notes"] = release_notes
    
    return result
