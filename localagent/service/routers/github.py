"""
LocalAgent - GitHub Router
Endpoints: /api/github/*, /api/changelog/sync-from-github
"""

import json
import asyncio
from typing import Dict, Any
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query

from ...connectors.github import (
    get_service_version, get_dashboard_version,
    REPOS, _get_token, _api_request, GITHUB_API,
    github_sync, github_push, github_push_all,
    get_workflow_status,
    _load_config as get_repo_config,
    _save_config as save_repo_config,
)
from ...engine.tracking import (
    generate_release_notes, add_changelog_entry, get_version_changelog,
    track_pending_release, set_todos_testing,
    get_pending_releases, complete_pending_release,
)

router = APIRouter(prefix="/api", tags=["github"])

DEFAULT_PROJECT = "LOCALAGENT"

# Cache and version helpers (set by main server)
_cache = None
_get_local_version = None

def set_cache(cache_instance):
    global _cache
    _cache = cache_instance

def set_version_helper(func):
    global _get_local_version
    _get_local_version = func

def invalidate_cache(category: str, project: str):
    if _cache:
        _cache.invalidate(f"{category}:{project}")


# ============================================================
# GITHUB STATUS
# ============================================================

@router.get("/github/status")
async def github_status():
    """Check GitHub configuration status."""
    
    token = _get_token()
    if not token:
        return {"configured": False, "error": "No GitHub token"}
    
    # Get chat-module version if exists
    chat_module_version = None
    if "chat-module" in REPOS:
        try:
            import urllib.request
            url = f"https://api.github.com/repos/{REPOS['chat-module']}/releases/latest"
            req = urllib.request.Request(url, headers={"User-Agent": "LocalAgent"})
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            chat_module_version = data.get("tag_name", "").lstrip("v")
        except:
            chat_module_version = "?"
    
    return {
        "configured": True,
        "valid": True,
        "user": "THEMiS-eng",
        "repos": REPOS,
        "service_repo": REPOS.get("service"),
        "dashboard_repo": REPOS.get("dashboard"),
        "chat_module_repo": REPOS.get("chat-module"),
        "service_version": get_service_version(),
        "dashboard_version": get_dashboard_version(),
        "chat_module_version": chat_module_version
    }


# ============================================================
# GITHUB RELEASES
# ============================================================

@router.get("/github/releases/{owner}/{repo}")
async def get_releases(owner: str, repo: str, limit: int = Query(10)):
    """Get releases from GitHub repo - formatted for Themis compatibility."""
    import urllib.request
    
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/releases?per_page={limit}"
        req = urllib.request.Request(url, headers={"User-Agent": "LocalAgent"})
        resp = urllib.request.urlopen(req, timeout=10)
        raw_releases = json.loads(resp.read())
        
        # Format for Themis compatibility: expects .tag, .body, .published_at
        releases = [{
            "tag": r.get("tag_name", ""),
            "name": r.get("name", ""),
            "body": r.get("body", ""),
            "published_at": r.get("published_at", ""),
            "url": r.get("html_url", ""),
            "prerelease": r.get("prerelease", False)
        } for r in raw_releases]
        
        return {"releases": releases}
    except Exception as e:
        # Return mock release for offline/missing repo
        return {
            "releases": [{
                "tag": "v10.1.9",
                "name": "THEMIS-QS v10.1.9",
                "body": "Current installed version",
                "published_at": "2026-01-21T00:00:00Z",
                "url": "",
                "prerelease": False
            }],
            "note": "Using local version (GitHub unavailable)"
        }

@router.get("/github/version/{owner}/{repo}")
async def get_latest_version(owner: str, repo: str):
    """Get latest version from GitHub repo releases."""
    import urllib.request
    import urllib.error
    
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "LocalAgent"})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        return {
            "version": data.get("tag_name", "unknown"),
            "name": data.get("name", ""),
            "published_at": data.get("published_at", ""),
            "url": data.get("html_url", "")
        }
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"version": "v0.0.0", "error": "No releases found"}
        return {"version": "unknown", "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"version": "unknown", "error": str(e)}


# ============================================================
# GITHUB SYNC & PUSH
# ============================================================

@router.post("/github/sync")
async def github_sync_endpoint(data: Dict[str, Any]):
    """Sync project to GitHub."""
    
    project = data.get("project", DEFAULT_PROJECT)
    repo_name = data.get("repo_name")
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: github_sync(project, repo_name)
    )
    return result

@router.post("/github/push")
async def github_push_endpoint(data: Dict[str, Any]):
    """Push to GitHub with auto-generated release notes."""
    from ...engine.tracking import get_todo, save_todo, get_bugfixes, save_bugfixes
    
    repo_type = data.get("repo_type") or data.get("target")
    version = data.get("version")
    message = data.get("message")
    create_release = data.get("release") or data.get("create_release", True)
    custom_notes = data.get("notes")
    todo_ids = data.get("todo_ids", [])
    
    # Get version from VERSION file if not provided
    if not version and _get_local_version:
        version = _get_local_version()
    
    # Assign version to completed items without version (done since last release)
    todos = get_todo(DEFAULT_PROJECT)
    todos_updated = False
    for item in todos:
        if item.get("done") and not item.get("version"):
            item["version"] = version
            todos_updated = True
    if todos_updated:
        save_todo(DEFAULT_PROJECT, todos)
        invalidate_cache("todo", DEFAULT_PROJECT)
    
    bugfixes = get_bugfixes(DEFAULT_PROJECT)
    bfs_updated = False
    for bf in bugfixes:
        if bf.get("status") == "applied" and not bf.get("version"):
            bf["version"] = version
            bfs_updated = True
    if bfs_updated:
        save_bugfixes(DEFAULT_PROJECT, bugfixes)
        invalidate_cache("bugfixes", DEFAULT_PROJECT)
    
    # Generate release notes if not provided
    release_notes = custom_notes
    if not release_notes and create_release:
        release_notes = generate_release_notes(DEFAULT_PROJECT, version)
        add_changelog_entry(DEFAULT_PROJECT, version, release_notes)
    
    loop = asyncio.get_event_loop()
    
    if repo_type == "all":
        service_dir = str(Path.home() / "localagent_v3")
        dashboard_dir = str(Path.home() / "localagent_v3" / "dashboard")
        result = await loop.run_in_executor(
            None,
            lambda: github_push_all(service_dir, dashboard_dir, version, message, create_release)
        )
    else:
        if repo_type == "dashboard":
            source_dir = str(Path.home() / "localagent_v3" / "dashboard")
        elif repo_type == "chat-module":
            source_dir = str(Path.home() / "localagent_v3" / "modules" / "ai-chat-module-pro")
        else:
            source_dir = str(Path.home() / "localagent_v3")
        result = await loop.run_in_executor(
            None,
            lambda: github_push(source_dir, repo_type or "service", message, version, create_release, release_notes)
        )
    
    # Track pending TODO completion
    if result.get("success") and todo_ids:
        set_todos_testing(DEFAULT_PROJECT, todo_ids, version)
        track_pending_release(DEFAULT_PROJECT, version, todo_ids, result.get("commit_sha"))
        invalidate_cache("todo", DEFAULT_PROJECT)
    
    if release_notes:
        result["release_notes"] = release_notes
    
    return result


# ============================================================
# WORKFLOW STATUS
# ============================================================

@router.get("/github/workflow-status")
async def check_workflow_status_endpoint():
    """Check GitHub Actions workflow status and mark TODOs as done if tests passed."""
    
    pending = get_pending_releases(DEFAULT_PROJECT)
    completed = []
    
    for release in pending:
        version = release.get("version")
        todo_ids = release.get("todo_ids", [])
        
        status = get_workflow_status(REPOS.get("service", ""), release.get("commit_sha"))
        
        if status == "success":
            complete_pending_release(DEFAULT_PROJECT, version, todo_ids)
            completed.append({"version": version, "todos": todo_ids, "status": "completed"})
            invalidate_cache("todo", DEFAULT_PROJECT)
        elif status == "failure":
            complete_pending_release(DEFAULT_PROJECT, version, [], failed=True)
            completed.append({"version": version, "todos": todo_ids, "status": "failed"})
            invalidate_cache("todo", DEFAULT_PROJECT)
    
    return {"checked": len(pending), "completed": completed}


# ============================================================
# CHANGELOG SYNC
# ============================================================

@router.post("/changelog/sync-from-github")
async def sync_changelog_from_github():
    """Sync changelog from GitHub releases."""
    
    repo = REPOS.get("service", "")
    if not repo:
        return {"success": False, "error": "No service repo configured"}
    
    # Get releases from GitHub
    url = f"{GITHUB_API}/repos/{repo}/releases"
    result = _api_request("GET", url)
    
    if "error" in result:
        return {"success": False, "error": result["error"]}
    
    releases = result if isinstance(result, list) else []
    existing = {c.get("version") for c in get_version_changelog(DEFAULT_PROJECT)}
    
    added = []
    for release in releases:
        version = release.get("tag_name", "").lstrip("v")
        if version and version not in existing:
            notes = release.get("body") or f"## v{version}\n\nReleased from GitHub"
            add_changelog_entry(DEFAULT_PROJECT, version, notes)
            added.append(version)
    
    return {"success": True, "added": added, "total": len(releases)}


# ============================================================
# CREATE GITHUB REPO
# ============================================================

@router.post("/github/create-repo")
async def create_github_repo(data: Dict[str, Any]):
    """Create a new GitHub repository."""
    from ...connectors.github import github_create_repo as create_repo
    
    name = data.get("name")
    description = data.get("description", "")
    private = data.get("private", False)
    
    if not name:
        raise HTTPException(status_code=400, detail="Repository name required")
    
    # Create repo under THEMiS-eng
    result = create_repo(name, description, private, org="THEMiS-eng")
    
    return result
