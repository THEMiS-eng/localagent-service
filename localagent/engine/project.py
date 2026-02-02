"""
LocalAgent - ENGINE: Project
Gestion projets, snapshots, versioning

Paths IMMUTABLES (ENV001, ENV002):
- AGENT_DIR = ~/.localagent-dev
- API_KEY_FILE = AGENT_DIR/api_key
"""

import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


# ============================================================
# PATHS (IMMUTABLE - ENV001, ENV002)
# ============================================================

AGENT_DIR = Path.home() / ".localagent-dev"
PROJECTS_DIR = Path.home() / "Desktop" / "localagent-projects"
CONFIG_DIR = AGENT_DIR / "config"
API_KEY_FILE = AGENT_DIR / "api_key"


def get_project_path(project: str) -> Path:
    """Get project root path."""
    return PROJECTS_DIR / project


def get_current_path(project: str) -> Path:
    """Get project current (working) directory."""
    return PROJECTS_DIR / project / "current"


def get_snapshots_path(project: str) -> Path:
    """Get project snapshots directory."""
    return PROJECTS_DIR / project / "snapshots"


# ============================================================
# VERSIONING
# ============================================================

def get_version(project: str) -> str:
    """Get project version."""
    version_file = PROJECTS_DIR / project / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "0.00.000"


def set_version(project: str, version: str):
    """Set project version."""
    (PROJECTS_DIR / project / "VERSION").write_text(version)


def increment_version(project: str, increment_type: str = "patch") -> str:
    """
    Increment version.
    Types: patch (0.00.XXX), minor (0.XX.000), major (X.00.000)
    """
    current = get_version(project)
    parts = current.split(".")
    if len(parts) != 3:
        parts = ["0", "00", "000"]
    
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    
    if increment_type == "patch":
        patch += 1
    elif increment_type == "minor":
        minor += 1
        patch = 0
    elif increment_type == "major":
        major += 1
        minor = 0
        patch = 0
    
    new_version = f"{major}.{minor:02d}.{patch:03d}"
    set_version(project, new_version)
    return new_version


# ============================================================
# SNAPSHOTS
# ============================================================

def create_snapshot(project: str, label: str = "") -> Optional[str]:
    """
    Create snapshot of project current state.
    Returns snapshot_id or None if failed.
    """
    current = get_current_path(project)
    snapshots = get_snapshots_path(project)
    
    if not current.exists():
        return None
    
    snapshots.mkdir(parents=True, exist_ok=True)
    
    # Use local timezone explicitly
    from datetime import timezone
    import time
    local_tz = timezone(timedelta(seconds=-time.timezone))
    local_now = datetime.now(local_tz)
    timestamp = local_now.strftime("%Y%m%d_%H%M%S")
    version = get_version(project)
    snapshot_id = f"{timestamp}_v{version}"
    if label:
        snapshot_id = f"{snapshot_id}_{label}"
    
    snapshot_path = snapshots / snapshot_id
    shutil.copytree(current, snapshot_path)
    
    # Write metadata
    (snapshot_path / ".snapshot.json").write_text(json.dumps({
        "id": snapshot_id,
        "version": version,
        "label": label,
        "created": datetime.now().isoformat()
    }, indent=2))
    
    return snapshot_id


def list_snapshots(project: str) -> List[Dict]:
    """List all snapshots for project."""
    snapshots_path = get_snapshots_path(project)
    if not snapshots_path.exists():
        return []
    
    result = []
    for d in sorted(snapshots_path.iterdir(), reverse=True):
        if d.is_dir():
            meta_file = d / ".snapshot.json"
            if meta_file.exists():
                try:
                    result.append(json.loads(meta_file.read_text()))
                except:
                    result.append({"id": d.name, "version": "?", "created": ""})
            else:
                result.append({"id": d.name, "version": "?", "created": ""})
    return result


def rollback(project: str, snapshot_id: str = None) -> bool:
    """
    Rollback to snapshot.
    If no snapshot_id, rollback to previous snapshot.
    """
    snapshots_path = get_snapshots_path(project)
    current = get_current_path(project)
    
    if not snapshots_path.exists():
        return False
    
    # Get snapshot to restore
    if not snapshot_id:
        snapshots = list_snapshots(project)
        if len(snapshots) < 2:
            return False
        snapshot_id = snapshots[1]["id"]
    
    snapshot_path = snapshots_path / snapshot_id
    if not snapshot_path.exists():
        return False
    
    # Replace current with snapshot
    if current.exists():
        shutil.rmtree(current)
    shutil.copytree(snapshot_path, current)
    
    # Remove snapshot metadata from current
    meta = current / ".snapshot.json"
    if meta.exists():
        meta.unlink()
    
    # Restore version
    meta_file = snapshot_path / ".snapshot.json"
    if meta_file.exists():
        try:
            data = json.loads(meta_file.read_text())
            if data.get("version"):
                set_version(project, data["version"])
        except:
            pass
    
    return True


# ============================================================
# PROJECT LIFECYCLE
# ============================================================

def init_project(name: str, source_dir: str = None) -> bool:
    """Initialize new project."""
    project_path = get_project_path(name)
    current = get_current_path(name)
    
    # Clean if exists
    if project_path.exists():
        shutil.rmtree(project_path)
    
    current.mkdir(parents=True, exist_ok=True)
    
    # Copy source if provided
    if source_dir:
        source = Path(source_dir).expanduser()
        if source.exists():
            shutil.copytree(source, current, dirs_exist_ok=True)
    
    # Initialize files
    set_version(name, "0.00.001")
    
    # Initialize tracking files
    (project_path / "BACKLOG.json").write_text("[]")
    (project_path / "TODO.json").write_text("[]")
    (project_path / "CHANGELOG.json").write_text(json.dumps([{
        "version": "0.00.001",
        "date": datetime.now().isoformat(),
        "changes": ["Project initialized"]
    }], indent=2))
    (project_path / "conversation.json").write_text("[]")
    (project_path / "errors.json").write_text(json.dumps({
        "errors": [], "patterns": {}, "dodges": []
    }, indent=2))
    
    # Create initial snapshot
    create_snapshot(name, "initial")
    
    return True


def commit_project(project: str, message: str) -> bool:
    """
    Commit project changes.
    - Increment version
    - Create snapshot
    - Update changelog
    """
    from .tracking import add_changelog_entry
    
    current = get_current_path(project)
    if not current.exists():
        return False
    
    # Increment version (ENV004)
    old_version = get_version(project)
    new_version = increment_version(project, "patch")
    
    # Create snapshot (ENV003)
    create_snapshot(project, f"commit_{new_version}")
    
    # Update changelog
    add_changelog_entry(project, new_version, [message])
    
    print(f"✅ Committed: {project} v{old_version} → v{new_version}")
    return True


def list_projects() -> List[Dict]:
    """List all projects."""
    if not PROJECTS_DIR.exists():
        return []
    
    projects = []
    for p in PROJECTS_DIR.iterdir():
        if p.is_dir() and (p / "current").exists():
            projects.append({
                "name": p.name,
                "version": get_version(p.name),
                "path": str(p)
            })
    return projects


def project_exists(project: str) -> bool:
    """Check if project exists."""
    return get_current_path(project).exists()
