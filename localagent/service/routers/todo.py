"""
LocalAgent - TODO & Backlog Router
Endpoints: /api/todo/*, /api/backlog/*, /api/nth/*
"""

from typing import Dict, Any
from fastapi import APIRouter, Query

from ...engine.tracking import (
    get_todo, get_backlog, get_changelog,
    add_todo_item, add_backlog_item,
    toggle_todo, save_todo, save_backlog,
)

router = APIRouter(prefix="/api", tags=["todo"])

# Default project - imported from parent
DEFAULT_PROJECT = "LOCALAGENT"

# ============================================================
# CACHE FUNCTIONS (imported from server)
# ============================================================

_cache = None

def set_cache(cache_instance):
    """Set cache instance from main server."""
    global _cache
    _cache = cache_instance

def cached_get_todo(project: str):
    if _cache:
        key = f"todo:{project}"
        cached = _cache.get(key)
        if cached is not None:
            return cached
    result = get_todo(project)
    if _cache:
        _cache.set(f"todo:{project}", result)
    return result

def cached_get_backlog(project: str):
    if _cache:
        key = f"backlog:{project}"
        cached = _cache.get(key)
        if cached is not None:
            return cached
    result = get_backlog(project)
    if _cache:
        _cache.set(f"backlog:{project}", result)
    return result

def invalidate_cache(category: str, project: str):
    if _cache:
        _cache.invalidate(f"{category}:{project}")


# ============================================================
# GET ENDPOINTS
# ============================================================

@router.get("/todo")
async def get_todo_endpoint(project: str = Query(default=None)):
    """Get TODO items."""
    return cached_get_todo(project or DEFAULT_PROJECT)

@router.get("/backlog")
async def get_backlog_endpoint(project: str = Query(default=None)):
    """Get backlog items."""
    return cached_get_backlog(project or DEFAULT_PROJECT)

@router.get("/changelog")
async def get_changelog_endpoint(project: str = Query(default=None)):
    """Get changelog."""
    return get_changelog(project or DEFAULT_PROJECT)


# ============================================================
# POST ENDPOINTS - ADD
# ============================================================

@router.post("/backlog/add")
async def add_backlog_endpoint(data: Dict[str, Any]):
    """Add backlog item."""
    item_id = add_backlog_item(DEFAULT_PROJECT, data.get("title", ""), data.get("priority", "medium"))
    invalidate_cache("backlog", DEFAULT_PROJECT)
    return {"id": item_id}

@router.post("/todo/add")
async def add_todo_endpoint(data: Dict[str, Any]):
    """Add TODO item (roadmap only, no release)."""
    item_id = add_todo_item(DEFAULT_PROJECT, data.get("title", ""), data.get("category", "todo"))
    invalidate_cache("todo", DEFAULT_PROJECT)
    return {"id": item_id, "triggers_release": False}

@router.post("/nth/add")
async def add_nth_endpoint(data: Dict[str, Any]):
    """Add NTH item (roadmap only, no release)."""
    item_id = add_todo_item(DEFAULT_PROJECT, data.get("title", ""), "nth")
    invalidate_cache("todo", DEFAULT_PROJECT)
    return {"id": item_id, "triggers_release": False}


# ============================================================
# POST ENDPOINTS - COMPLETE/RESTORE
# ============================================================

@router.post("/todo/complete")
async def complete_todo_endpoint(data: Dict[str, Any]):
    """Mark TODO item as done (manual toggle, no release)."""
    item_id = data.get("id", "")
    success = toggle_todo(DEFAULT_PROJECT, item_id)
    invalidate_cache("todo", DEFAULT_PROJECT)
    return {"success": success, "id": item_id}

@router.post("/todo/restore")
async def restore_todo_endpoint(data: Dict[str, Any]):
    """Restore a completed TODO back to pending."""
    item_id = data.get("id", "")
    
    todo = get_todo(DEFAULT_PROJECT)
    for item in todo:
        if item["id"] == item_id:
            item["done"] = False
            item["status"] = "pending"
            item.pop("completed", None)
            item.pop("version", None)
            item.pop("commit_sha", None)
            item.pop("release_url", None)
            save_todo(DEFAULT_PROJECT, todo)
            invalidate_cache("todo", DEFAULT_PROJECT)
            return {"success": True, "id": item_id, "status": "pending"}
    
    return {"success": False, "error": f"TODO {item_id} not found"}

@router.post("/todo/restore-all")
async def restore_all_todos_endpoint():
    """Restore ALL completed TODOs back to pending."""
    
    todo = get_todo(DEFAULT_PROJECT)
    restored = []
    for item in todo:
        if item.get("done") or item.get("status") == "done":
            item["done"] = False
            item["status"] = "pending"
            item.pop("completed", None)
            item.pop("version", None)
            item.pop("commit_sha", None)
            item.pop("release_url", None)
            restored.append(item["id"])
    
    save_todo(DEFAULT_PROJECT, todo)
    invalidate_cache("todo", DEFAULT_PROJECT)
    return {"success": True, "restored": restored, "count": len(restored)}
