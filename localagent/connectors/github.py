"""
LocalAgent v3.0.34 - CONNECTOR: GitHub (SKILL 7)
Clone, sync, list, remove, PUSH, RELEASE repositories
Supports two repos: localagent-service, localagent-dashboard
"""

import json
import shutil
import subprocess
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..engine.project import PROJECTS_DIR, CONFIG_DIR


# ============================================================
# CONFIG
# ============================================================

GITHUB_CONFIG_FILE = CONFIG_DIR / "github.json"
GITHUB_TOKEN_FILE = Path.home() / ".localagent-dev" / "github_token"
GITHUB_API = "https://api.github.com"

# Repository configuration - TWO SEPARATE REPOS
REPOS = {
    "service": "THEMiS-eng/localagent-service",
    "dashboard": "THEMiS-eng/localagent-dashboard"
}


def _get_token() -> Optional[str]:
    """Get GitHub token from file."""
    if GITHUB_TOKEN_FILE.exists():
        return GITHUB_TOKEN_FILE.read_text().strip()
    # Fallback to config
    config = _load_config()
    return config.get("token")


def _load_config() -> Dict:
    """Load GitHub config."""
    if GITHUB_CONFIG_FILE.exists():
        try:
            return json.loads(GITHUB_CONFIG_FILE.read_text())
        except:
            pass
    return {"repos": {}}


def _save_config(config: Dict):
    """Save GitHub config."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    GITHUB_CONFIG_FILE.write_text(json.dumps(config, indent=2))


# ============================================================
# GITHUB API HELPERS
# ============================================================

def _api_request(method: str, url: str, data: Dict = None, token: str = None) -> Dict:
    """Make GitHub API request."""
    token = token or _get_token()
    if not token:
        return {"error": "No GitHub token configured"}
    
    headers = {
        "User-Agent": "LocalAgent",
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    if data:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode()
    else:
        body = None
    
    try:
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode())
            return {"error": err_body.get("message", str(e)), "status": e.code}
        except:
            return {"error": str(e), "status": e.code}
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# VERSION FROM RELEASES (ENV012)
# ============================================================

def fetch_github_version(repo: str) -> Optional[str]:
    """Fetch latest version from GitHub releases (with auth)."""
    try:
        url = f"{GITHUB_API}/repos/{repo}/releases/latest"
        headers = {"User-Agent": "LocalAgent"}
        token = _get_token()
        if token:
            headers["Authorization"] = f"token {token}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            tag = data.get("tag_name", "")
            return tag.lstrip("v") if tag else None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        return None
    except:
        return None


def get_service_version() -> str:
    """Get service worker version from GitHub."""
    return fetch_github_version(REPOS["service"]) or "0.0.0"


def get_dashboard_version() -> str:
    """Get dashboard version from GitHub."""
    return fetch_github_version(REPOS["dashboard"]) or "0.0.0"


# ============================================================
# PUSH TO GITHUB
# ============================================================

def github_push(source_dir: str, repo_type: str = "service", message: str = None, 
                version: str = None, create_release: bool = False) -> Dict:
    """
    Push local directory to GitHub repository.
    
    Args:
        source_dir: Local directory to push
        repo_type: "service" or "dashboard"
        message: Commit message
        version: Version tag (e.g., "3.0.31")
        create_release: Create GitHub release after push
        
    Returns:
        {"success": bool, "actions": [...], "error": str}
    """
    token = _get_token()
    if not token:
        return {"success": False, "error": "No GitHub token. Save to ~/.localagent-dev/github_token"}
    
    if repo_type not in REPOS:
        return {"success": False, "error": f"Unknown repo type: {repo_type}. Use 'service' or 'dashboard'"}
    
    repo = REPOS[repo_type]
    source = Path(source_dir)
    
    if not source.exists():
        return {"success": False, "error": f"Source directory not found: {source_dir}"}
    
    actions = []
    
    try:
        # Check if git repo exists
        git_dir = source / ".git"
        
        if not git_dir.exists():
            # Initialize git
            subprocess.run(["git", "init"], cwd=source, capture_output=True, check=True)
            actions.append("git init")
        
        # Configure remote
        remote_url = f"https://{token}@github.com/{repo}.git"
        
        # Check existing remote
        result = subprocess.run(["git", "remote", "-v"], cwd=source, capture_output=True, text=True)
        
        if "origin" in result.stdout:
            subprocess.run(["git", "remote", "set-url", "origin", remote_url], cwd=source, capture_output=True)
            actions.append("updated remote")
        else:
            subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=source, capture_output=True)
            actions.append("added remote")
        
        # Add all files
        subprocess.run(["git", "add", "-A"], cwd=source, capture_output=True, check=True)
        actions.append("git add")
        
        # Commit
        commit_msg = message or f"Update {repo_type} v{version}" if version else f"Update {repo_type}"
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg, "--allow-empty"],
            cwd=source, capture_output=True, text=True
        )
        if result.returncode == 0:
            actions.append("committed")
        
        # Push
        result = subprocess.run(
            ["git", "push", "-u", "origin", "main", "--force"],
            cwd=source, capture_output=True, text=True, timeout=120
        )
        
        if result.returncode != 0:
            # Try creating main branch first
            subprocess.run(["git", "branch", "-M", "main"], cwd=source, capture_output=True)
            result = subprocess.run(
                ["git", "push", "-u", "origin", "main", "--force"],
                cwd=source, capture_output=True, text=True, timeout=120
            )
        
        if result.returncode != 0:
            return {"success": False, "error": f"Push failed: {result.stderr}", "actions": actions}
        
        actions.append("pushed to origin/main")
        
        # Create tag if version specified
        if version:
            tag = f"v{version}"
            subprocess.run(["git", "tag", "-f", tag], cwd=source, capture_output=True)
            subprocess.run(["git", "push", "origin", tag, "--force"], cwd=source, capture_output=True)
            actions.append(f"tagged {tag}")
        
        # Create release if requested
        if create_release and version:
            release_result = github_create_release(repo_type, version)
            if release_result.get("success"):
                actions.append(f"release created: {release_result.get('url')}")
            else:
                actions.append(f"release failed: {release_result.get('error')}")
        
        return {"success": True, "actions": actions, "repo": repo}
        
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Git operation timed out", "actions": actions}
    except Exception as e:
        return {"success": False, "error": str(e), "actions": actions}


# ============================================================
# CREATE RELEASE
# ============================================================

def github_create_release(repo_type: str, version: str, notes: str = None) -> Dict:
    """
    Create a GitHub release.
    
    Args:
        repo_type: "service" or "dashboard"
        version: Version string (e.g., "3.0.31")
        notes: Release notes markdown
        
    Returns:
        {"success": bool, "url": str, "error": str}
    """
    if repo_type not in REPOS:
        return {"success": False, "error": f"Unknown repo type: {repo_type}"}
    
    repo = REPOS[repo_type]
    tag = f"v{version}"
    
    # Default release notes
    if not notes:
        notes = f"## {repo_type.title()} {tag}\n\nReleased: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    data = {
        "tag_name": tag,
        "name": f"LocalAgent {repo_type.title()} {tag}",
        "body": notes,
        "draft": False,
        "prerelease": False
    }
    
    url = f"{GITHUB_API}/repos/{repo}/releases"
    result = _api_request("POST", url, data)
    
    if "error" in result:
        # If release exists, try to get it
        if result.get("status") == 422:
            return {"success": False, "error": f"Release {tag} already exists"}
        return {"success": False, "error": result["error"]}
    
    return {
        "success": True,
        "url": result.get("html_url"),
        "tag": tag,
        "id": result.get("id")
    }


def github_delete_release(repo_type: str, version: str) -> Dict:
    """Delete a release."""
    if repo_type not in REPOS:
        return {"success": False, "error": f"Unknown repo type: {repo_type}"}
    
    repo = REPOS[repo_type]
    tag = f"v{version}"
    
    # Get release by tag
    url = f"{GITHUB_API}/repos/{repo}/releases/tags/{tag}"
    result = _api_request("GET", url)
    
    if "error" in result:
        return {"success": False, "error": f"Release not found: {tag}"}
    
    release_id = result.get("id")
    
    # Delete release
    _api_request("DELETE", f"{GITHUB_API}/repos/{repo}/releases/{release_id}")
    
    # Delete tag
    _api_request("DELETE", f"{GITHUB_API}/repos/{repo}/git/refs/tags/{tag}")
    
    return {"success": True, "deleted": tag}


# ============================================================
# PUSH BOTH REPOS (CONVENIENCE)
# ============================================================

def github_push_all(service_dir: str, dashboard_dir: str, version: str, 
                    message: str = None, create_releases: bool = True) -> Dict:
    """
    Push both service and dashboard to their respective repos.
    
    Args:
        service_dir: Path to service worker directory
        dashboard_dir: Path to dashboard directory  
        version: Version for both (e.g., "3.0.31")
        message: Commit message
        create_releases: Create GitHub releases
        
    Returns:
        {"success": bool, "service": {...}, "dashboard": {...}}
    """
    results = {"success": True}
    
    # Push service
    print(f"📤 Pushing localagent-service v{version}...")
    service_result = github_push(
        service_dir, "service", message, version, create_releases
    )
    results["service"] = service_result
    
    if not service_result.get("success"):
        results["success"] = False
        print(f"❌ Service push failed: {service_result.get('error')}")
    else:
        print(f"✅ Service pushed: {', '.join(service_result.get('actions', []))}")
    
    # Push dashboard
    print(f"📤 Pushing localagent-dashboard v{version}...")
    dashboard_result = github_push(
        dashboard_dir, "dashboard", message, version, create_releases
    )
    results["dashboard"] = dashboard_result
    
    if not dashboard_result.get("success"):
        results["success"] = False
        print(f"❌ Dashboard push failed: {dashboard_result.get('error')}")
    else:
        print(f"✅ Dashboard pushed: {', '.join(dashboard_result.get('actions', []))}")
    
    return results


# ============================================================
# LIST RELEASES
# ============================================================

def github_list_releases(repo_type: str = None, limit: int = 10) -> List[Dict]:
    """List releases for one or both repos."""
    releases = []
    
    repos_to_check = [repo_type] if repo_type else ["service", "dashboard"]
    
    for rtype in repos_to_check:
        if rtype not in REPOS:
            continue
        repo = REPOS[rtype]
        url = f"{GITHUB_API}/repos/{repo}/releases?per_page={limit}"
        result = _api_request("GET", url)
        
        if isinstance(result, list):
            for r in result:
                releases.append({
                    "repo_type": rtype,
                    "repo": repo,
                    "version": r.get("tag_name", "").lstrip("v"),
                    "tag": r.get("tag_name"),
                    "name": r.get("name"),
                    "published_at": r.get("published_at"),
                    "url": r.get("html_url")
                })
    
    return releases


# ============================================================
# ORIGINAL CLONE/SYNC OPERATIONS (preserved)
# ============================================================

def github_clone(project: str, repo_url: str, branch: str = "main") -> bool:
    """Clone repository into project."""
    current = PROJECTS_DIR / project / "current"
    if not current.exists():
        print(f"❌ Project not found: {project}")
        return False
    
    if repo_url.endswith(".git"):
        repo_url = repo_url[:-4]
    repo_name = repo_url.split("/")[-1]
    
    target = current / "github" / repo_name
    target.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        if target.exists():
            result = subprocess.run(
                ["git", "-C", str(target), "pull"],
                capture_output=True, text=True, timeout=120
            )
            print(f"📥 Git pull: {repo_name}")
        else:
            result = subprocess.run(
                ["git", "clone", "--branch", branch, "--depth", "1", repo_url, str(target)],
                capture_output=True, text=True, timeout=300
            )
            print(f"📥 Git clone: {repo_name}")
        
        if result.returncode != 0:
            print(f"❌ Git error: {result.stderr}")
            return False
        
        config = _load_config()
        config["repos"][repo_name] = {
            "url": repo_url,
            "branch": branch,
            "project": project,
            "path": str(target),
            "last_sync": datetime.now().isoformat()
        }
        _save_config(config)
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Git operation timed out")
        return False
    except Exception as e:
        print(f"❌ Clone failed: {e}")
        return False


def github_sync(project: str, repo_name: str = None) -> bool:
    """Sync (pull) repositories."""
    config = _load_config()
    
    if repo_name:
        if repo_name not in config["repos"]:
            print(f"❌ Repository not found: {repo_name}")
            return False
        repos = {repo_name: config["repos"][repo_name]}
    else:
        repos = {k: v for k, v in config["repos"].items() if v.get("project") == project}
    
    if not repos:
        print(f"No repositories for project: {project}")
        return False
    
    success = True
    for name, info in repos.items():
        target = Path(info.get("path", ""))
        if not target.exists():
            print(f"⚠️ Not found: {name}")
            continue
        
        try:
            result = subprocess.run(
                ["git", "-C", str(target), "pull"],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                print(f"✅ Synced: {name}")
                info["last_sync"] = datetime.now().isoformat()
            else:
                print(f"❌ Sync failed: {name}")
                success = False
        except Exception as e:
            print(f"❌ Error: {name} - {e}")
            success = False
    
    _save_config(config)
    return success


def github_list(project: str = None):
    """List repositories."""
    config = _load_config()
    repos = config.get("repos", {})
    
    print("\n📦 GitHub Repositories:")
    print("-" * 60)
    
    # Show configured repos
    print(f"\n  Configured Repos:")
    print(f"    service:   {REPOS['service']}")
    print(f"    dashboard: {REPOS['dashboard']}")
    
    # Show cloned repos
    count = 0
    print(f"\n  Cloned Repos:")
    for name, info in repos.items():
        if project and info.get("project") != project:
            continue
        count += 1
        print(f"    📁 {name}")
        print(f"       URL: {info.get('url', '')}")
        print(f"       Last sync: {info.get('last_sync', 'Never')[:19]}")
    
    if count == 0:
        print("    (none)")
    print()


def github_remove(project: str, repo_name: str) -> bool:
    """Remove repository."""
    config = _load_config()
    
    if repo_name not in config["repos"]:
        print(f"❌ Not found: {repo_name}")
        return False
    
    info = config["repos"][repo_name]
    target = Path(info.get("path", ""))
    
    if target.exists():
        shutil.rmtree(target)
        print(f"🗑️ Removed: {target}")
    
    del config["repos"][repo_name]
    _save_config(config)
    return True


# ============================================================
# UTILITY FUNCTIONS (preserved)
# ============================================================

def get_repos(project: str = None) -> List[Dict]:
    """Get repos list for API."""
    config = _load_config()
    repos = []
    for name, info in config.get("repos", {}).items():
        if project and info.get("project") != project:
            continue
        repos.append({
            "name": name,
            "url": info.get("url"),
            "branch": info.get("branch", "main"),
            "project": info.get("project"),
            "last_sync": info.get("last_sync")
        })
    return repos


def fetch_github_tags(repo: str, limit: int = 10) -> List[str]:
    """Fetch tags from GitHub."""
    try:
        url = f"{GITHUB_API}/repos/{repo}/tags?per_page={limit}"
        req = urllib.request.Request(url, headers={"User-Agent": "LocalAgent"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return [t.get("name", "").lstrip("v") for t in data]
    except:
        return []


def get_version_history() -> List[Dict]:
    """Get version history from GitHub config."""
    config = _load_config()
    return config.get("version_history", [])


def get_branches() -> Dict:
    """Get all tracked branches."""
    config = _load_config()
    return config.get("branches", {})


def get_current_branch_info() -> Dict:
    """Get info about current version branch."""
    config = _load_config()
    branches = config.get("branches", {})
    history = config.get("version_history", [])
    
    current = next((v for v in history if v.get("status") == "current"), None)
    if current:
        branch_name = current.get("branch", "")
        return {
            "version": current.get("version"),
            "branch": branch_name,
            "date": current.get("date"),
            "info": branches.get(branch_name, {})
        }
    return {}


def update_version_history(version: str, changes: List[str] = None):
    """Update version history when a new version is created."""
    config = _load_config()
    
    if "version_history" not in config:
        config["version_history"] = []
    if "branches" not in config:
        config["branches"] = {}
    
    for v in config["version_history"]:
        if v.get("status") == "current":
            v["status"] = "released"
    
    branch_name = f"v{version}"
    now = datetime.now().isoformat()
    
    config["version_history"].append({
        "version": version,
        "branch": branch_name,
        "date": now,
        "status": "current"
    })
    
    config["branches"][branch_name] = {
        "version": version,
        "created": now,
        "status": "current",
        "changes": changes or []
    }
    
    _save_config(config)
    return branch_name


def sync_app_version():
    """Sync current app version to GitHub config."""
    try:
        from ..main import VERSION
        config = _load_config()
        current_info = get_current_branch_info()
        
        if not current_info or current_info.get("version") != VERSION:
            print(f"📤 Syncing app version {VERSION} to GitHub config...")
            update_version_history(VERSION, ["App startup sync"])
            return True
        return False
    except Exception as e:
        print(f"⚠️ Could not sync app version: {e}")
        return False


def get_app_info() -> Dict:
    """Get complete app info from GitHub config."""
    config = _load_config()
    current = get_current_branch_info()
    
    return {
        "version": current.get("version") if current else None,
        "branch": current.get("branch") if current else None,
        "date": current.get("date") if current else None,
        "total_versions": len(config.get("version_history", [])),
        "repos": list(config.get("repos", {}).keys())
    }
