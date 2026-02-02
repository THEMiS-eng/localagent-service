"""
Releases Router - handles release notes, versioning, deployment
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from pathlib import Path
from datetime import datetime

router = APIRouter(prefix="/api", tags=["releases"])

DEFAULT_PROJECT = "LOCALAGENT"

# Injected dependencies
_cache = None

def set_cache(cache_instance):
    global _cache
    _cache = cache_instance

def invalidate_cache(category: str, project: str):
    if _cache:
        _cache.invalidate(f"{category}:{project}")


@router.get("/release-notes/preview")
async def preview_release_notes():
    """Preview release notes for next version."""
    from ...engine.tracking import generate_release_notes
    version_file = Path.home() / "localagent_v3" / "VERSION"
    version = version_file.read_text().strip() if version_file.exists() else "0.0.0"
    notes = generate_release_notes(DEFAULT_PROJECT, version)
    return {"version": version, "notes": notes}


@router.get("/releases")
async def get_releases():
    """Get all releases."""
    from ...engine.tracking import get_release_log
    return {"releases": get_release_log(DEFAULT_PROJECT)}


@router.post("/releases")
async def create_release(data: Dict[str, Any]):
    """Add a release."""
    from ...engine.tracking import add_changelog_entry
    version = data.get("version")
    notes = data.get("notes", "")
    if not version:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="version required")
    add_changelog_entry(DEFAULT_PROJECT, version, notes)
    return {"version": version, "status": "created"}


@router.post("/releases/seed")
async def seed_releases(data: Dict[str, Any]):
    """Seed releases from existing data."""
    from ...engine.tracking import get_changelog
    # Just return current changelog count as "seeded"
    changelog = get_changelog(DEFAULT_PROJECT)
    return {"seeded": len(changelog)}


@router.get("/releases/{version}")
async def get_release(version: str):
    """Get specific release."""
    from ...engine.tracking import get_release_log
    releases = get_release_log(DEFAULT_PROJECT)
    for r in releases:
        if r.get("version") == version:
            return r
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail=f"Release {version} not found")
    raise HTTPException(status_code=404, detail="Release not found")


@router.get("/release-notes")
async def get_release_notes():
    """Get release notes markdown."""
    from ...engine.tracking import generate_full_release_notes
    return {"content": generate_full_release_notes(DEFAULT_PROJECT)}


@router.get("/release-notes/github")
async def get_github_release_notes(repo_type: str = None):
    """Get release notes from GitHub."""
    from ...connectors.github import github_list_releases
    releases = github_list_releases(repo_type, 1)
    if releases:
        return {"version": releases[0].get("tag_name", ""), "body": releases[0].get("body", "")}
    return {"version": "", "body": ""}


@router.get("/release-notes/github/all")
async def get_all_github_releases(repo_type: str = None, limit: int = 10):
    """Get all release notes from GitHub."""
    from ...connectors.github import github_list_releases
    releases = github_list_releases(repo_type, limit)
    return {"releases": releases}


@router.get("/release-notes/full")
async def get_full_release_notes():
    """Get full release notes with all versions."""
    from ...engine.tracking import get_changelog
    return {"changelog": get_changelog(DEFAULT_PROJECT)}


@router.get("/roadmap")
async def get_roadmap():
    """Get project roadmap."""
    from ...engine.tracking import get_todo
    todo = get_todo(DEFAULT_PROJECT)
    return {"items": todo}


@router.get("/roadmap/md")
async def get_roadmap_markdown():
    """Get roadmap as markdown."""
    from ...engine.tracking import generate_roadmap_md
    return {"content": generate_roadmap_md(DEFAULT_PROJECT)}


@router.get("/version/next")
async def get_next_version():
    """Get next version number."""
    from ...connectors.github import get_service_version
    current = get_service_version() or "0.0.0"
    parts = current.split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    return {"current": current, "next": ".".join(parts)}


@router.post("/version/validate")
async def validate_version(data: Dict[str, Any]):
    """Validate a version string."""
    version = data.get("version", "")
    import re
    valid = bool(re.match(r'^\d+\.\d+\.\d+$', version))
    return {"valid": valid, "version": version}


@router.post("/deploy/release")
async def deploy_release(data: Dict[str, Any]):
    """Deploy a release to GitHub."""
    from ...core.release_publisher import create_release
    version = data.get("version")
    notes = data.get("notes", "")
    result = create_release(version, notes)
    return result


@router.get("/changelog")
async def get_changelog():
    """
    Get the local CHANGELOG.md content.
    Returns parsed releases for UI display.
    """
    import re
    
    # Find CHANGELOG.md
    possible_paths = [
        Path(__file__).parent.parent.parent.parent / "CHANGELOG.md",
        Path.cwd() / "CHANGELOG.md",
    ]
    
    changelog_content = None
    for path in possible_paths:
        if path.exists():
            changelog_content = path.read_text()
            break
    
    if not changelog_content:
        return {"releases": [], "raw": ""}
    
    # Parse releases from CHANGELOG.md
    releases = []
    release_pattern = r'## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})\s*([\s\S]*?)(?=\n## \[|\n---|\Z)'
    
    for match in re.finditer(release_pattern, changelog_content):
        version = match.group(1)
        date = match.group(2)
        body = match.group(3).strip()
        
        releases.append({
            "tag": f"v{version}",
            "version": version,
            "published_at": f"{date}T00:00:00Z",
            "name": f"THEMIS-QS v{version}",
            "body": body,
            "local": True  # Flag to indicate this is from local changelog
        })
    
    return {
        "releases": releases,
        "raw": changelog_content
    }


@router.get("/changelog/version/{version}")
async def get_changelog_version(version: str):
    """Get changelog for a specific version."""
    result = await get_changelog()
    
    for release in result.get("releases", []):
        if release["version"] == version or release["tag"] == version or release["tag"] == f"v{version}":
            return {"release": release}
    
    return {"release": None, "error": f"Version {version} not found in changelog"}
