"""
LocalAgent v2.10.39 - CORE: Release Publisher
Pushes releases to GitHub (create release, upload ZIP, write notes)
"""

import json
import subprocess
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List

from ..engine.project import CONFIG_DIR


# ============================================================
# GITHUB TOKEN
# ============================================================

GITHUB_TOKEN_FILE = CONFIG_DIR / "github_token.json"


def get_github_token() -> Optional[str]:
    """Get GitHub personal access token."""
    if GITHUB_TOKEN_FILE.exists():
        try:
            data = json.loads(GITHUB_TOKEN_FILE.read_text())
            return data.get("token")
        except:
            pass
    return None


def set_github_token(token: str) -> bool:
    """Set GitHub personal access token."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        GITHUB_TOKEN_FILE.write_text(json.dumps({
            "token": token,
            "created": datetime.now().isoformat()
        }, indent=2))
        # Secure the file
        GITHUB_TOKEN_FILE.chmod(0o600)
        print("✅ GitHub token saved")
        return True
    except Exception as e:
        print(f"❌ Failed to save token: {e}")
        return False


def verify_token() -> Dict:
    """Verify GitHub token and return user info."""
    token = get_github_token()
    if not token:
        return {"valid": False, "error": "No token configured"}
    
    try:
        result = subprocess.run(
            ["curl", "-s", "-H", f"Authorization: token {token}", 
             "https://api.github.com/user"],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(result.stdout)
        
        if "login" in data:
            return {
                "valid": True,
                "user": data.get("login"),
                "name": data.get("name"),
                "scopes": result.stderr  # Headers contain scopes
            }
        else:
            return {"valid": False, "error": data.get("message", "Invalid token")}
    except Exception as e:
        return {"valid": False, "error": str(e)}


def verify_repo(owner_repo: str = None) -> Dict:
    """
    Verify repository exists and we have access.
    
    Returns:
        {
            "exists": bool,
            "can_push": bool,
            "owner": str,
            "repo": str,
            "private": bool,
            "error": str (if any)
        }
    """
    token = get_github_token()
    if not token:
        return {"exists": False, "error": "No token configured"}
    
    if not owner_repo:
        repo_config = get_repo_config()
        owner_repo = repo_config.get("owner_repo")
    
    if not owner_repo:
        return {"exists": False, "error": "No repository configured"}
    
    try:
        result = subprocess.run(
            ["curl", "-s", "-H", f"Authorization: token {token}",
             f"https://api.github.com/repos/{owner_repo}"],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(result.stdout)
        
        if "id" in data:
            # Check permissions
            permissions = data.get("permissions", {})
            return {
                "exists": True,
                "can_push": permissions.get("push", False),
                "owner": data.get("owner", {}).get("login"),
                "repo": data.get("name"),
                "private": data.get("private", False),
                "full_name": data.get("full_name"),
                "default_branch": data.get("default_branch", "main")
            }
        else:
            return {
                "exists": False, 
                "error": data.get("message", "Repository not found"),
                "owner_repo": owner_repo
            }
    except Exception as e:
        return {"exists": False, "error": str(e)}


def create_repo(name: str, org: str = None, private: bool = True) -> Dict:
    """
    Create a new GitHub repository.
    
    Args:
        name: Repository name
        org: Organization name (None for personal repo)
        private: Make repo private
        
    Returns:
        {"success": bool, "url": str, "error": str}
    """
    token = get_github_token()
    if not token:
        return {"success": False, "error": "No token configured"}
    
    # Determine endpoint
    if org:
        endpoint = f"https://api.github.com/orgs/{org}/repos"
        print(f"📦 Creating repo in organization: {org}")
    else:
        endpoint = "https://api.github.com/user/repos"
        print(f"📦 Creating personal repo")
    
    repo_data = {
        "name": name,
        "private": private,
        "auto_init": True,  # Initialize with README so it's not empty
        "description": "LocalAgent - Smart Agent Orchestrator"
    }
    
    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST",
             "-H", f"Authorization: token {token}",
             "-H", "Accept: application/vnd.github.v3+json",
             "-H", "Content-Type: application/json",
             "-d", json.dumps(repo_data),
             endpoint],
            capture_output=True, text=True, timeout=30
        )
        
        print(f"   API Response: {result.stdout[:500]}")
        
        data = json.loads(result.stdout)
        
        if "id" in data:
            url = data.get("html_url")
            print(f"✅ Repository created: {url}")
            return {
                "success": True,
                "url": url,
                "full_name": data.get("full_name"),
                "clone_url": data.get("clone_url")
            }
        else:
            error_msg = data.get("message", "Failed to create repository")
            errors = data.get("errors", [])
            if errors:
                error_msg += f" - {errors}"
            return {
                "success": False,
                "error": error_msg
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def has_github_token() -> bool:
    """Check if GitHub token is configured."""
    return get_github_token() is not None


# ============================================================
# GITHUB API
# ============================================================

def _github_api(method: str, endpoint: str, data: Dict = None, is_upload: bool = False) -> Dict:
    """
    Make GitHub API request.
    
    Args:
        method: GET, POST, PATCH, DELETE
        endpoint: API endpoint (e.g., /repos/user/repo/releases)
        data: JSON data for POST/PATCH
        is_upload: If True, use uploads.github.com
        
    Returns:
        Response JSON or {"error": "..."}
    """
    token = get_github_token()
    if not token:
        return {"error": "GitHub token not configured. Run: localagent-dev set-github-token <token>"}
    
    if is_upload:
        base_url = "https://uploads.github.com"
    else:
        base_url = "https://api.github.com"
    
    url = f"{base_url}{endpoint}"
    
    headers = [
        "-H", "Accept: application/vnd.github.v3+json",
        "-H", f"Authorization: token {token}",
        "-H", "User-Agent: LocalAgent"
    ]
    
    cmd = ["curl", "-s", "-X", method] + headers
    
    if data and not is_upload:
        cmd.extend(["-H", "Content-Type: application/json"])
        cmd.extend(["-d", json.dumps(data)])
    
    cmd.append(url)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.stdout:
            return json.loads(result.stdout)
        return {"error": "Empty response"}
    except json.JSONDecodeError:
        return {"error": f"Invalid JSON: {result.stdout[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def _upload_asset(upload_url: str, file_path: Path, content_type: str = "application/zip") -> Dict:
    """Upload a release asset."""
    token = get_github_token()
    if not token:
        return {"error": "No token"}
    
    # upload_url comes with {?name,label} - we need to replace it
    upload_url = upload_url.replace("{?name,label}", f"?name={file_path.name}")
    
    cmd = [
        "curl", "-s", "-X", "POST",
        "-H", "Accept: application/vnd.github.v3+json",
        "-H", f"Authorization: token {token}",
        "-H", f"Content-Type: {content_type}",
        "--data-binary", f"@{file_path}",
        upload_url
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.stdout:
            return json.loads(result.stdout)
        return {"error": "Empty response"}
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# REPO CONFIG
# ============================================================

def get_repo_config() -> Dict:
    """Get configured repository info."""
    from ..connectors.github import _load_config
    config = _load_config()
    
    repos = config.get("repos", {})
    if "localagent" in repos:
        url = repos["localagent"].get("url", "")
        # Extract owner/repo from URL
        # https://github.com/owner/repo -> owner/repo
        if "github.com" in url:
            parts = url.rstrip("/").split("github.com/")[-1]
            return {"owner_repo": parts, "url": url}
    
    return {}


def set_repo_url(url: str) -> bool:
    """Set the LocalAgent repository URL."""
    from ..connectors.github import _load_config, _save_config
    
    config = _load_config()
    if "repos" not in config:
        config["repos"] = {}
    
    config["repos"]["localagent"] = {
        "url": url,
        "configured": datetime.now().isoformat()
    }
    
    _save_config(config)
    print(f"✅ Repository URL set: {url}")
    return True


# ============================================================
# CREATE RELEASE
# ============================================================

def release_exists(version: str) -> Dict:
    """Check if a release already exists for this version."""
    releases = list_releases(limit=50)
    for r in releases:
        if r.get("version") == version:
            return {"exists": True, "release": r}
    return {"exists": False}


def delete_release(tag_name: str) -> Dict:
    """Delete a release by tag name."""
    repo = get_repo_config()
    if not repo.get("owner_repo"):
        return {"success": False, "error": "Repository not configured"}
    
    owner_repo = repo["owner_repo"]
    
    # First get release ID by tag
    response = _github_api("GET", f"/repos/{owner_repo}/releases/tags/{tag_name}")
    
    if "error" in response or "id" not in response:
        return {"success": False, "error": f"Release not found: {tag_name}"}
    
    release_id = response["id"]
    
    # Delete the release
    _github_api("DELETE", f"/repos/{owner_repo}/releases/{release_id}")
    
    # Also delete the tag
    _github_api("DELETE", f"/repos/{owner_repo}/git/refs/tags/{tag_name}")
    
    print(f"✅ Deleted release: {tag_name}")
    return {"success": True, "deleted": tag_name}


def create_release(
    version: str,
    zip_path: str,
    release_notes: str = None,
    prerelease: bool = False,
    auto_create_repo: bool = True,
    force: bool = False
) -> Dict:
    """
    Create a GitHub release with ZIP asset.
    
    Args:
        version: Version string (e.g., "2.10.39")
        zip_path: Path to the ZIP file to upload
        release_notes: Markdown release notes (auto-generated if None)
        prerelease: Mark as pre-release
        auto_create_repo: Create repo if it doesn't exist
        force: If True, delete existing release and recreate
        
    Returns:
        {
            "success": bool,
            "release_url": str,
            "download_url": str,
            "error": str (if failed)
            "needs_confirmation": bool (if release exists and force=False)
        }
    """
    # Step 0: Verify token
    token_info = verify_token()
    if not token_info.get("valid"):
        return {"success": False, "error": f"GitHub token invalid: {token_info.get('error')}"}
    print(f"🔑 Token valid for user: {token_info.get('user')}")
    
    # Step 0a: Check if release already exists
    existing = release_exists(version)
    if existing.get("exists"):
        if not force:
            print(f"\n⚠️  Release v{version} already exists on GitHub!")
            print(f"   URL: {existing['release'].get('url', 'N/A')}")
            print(f"\n   Options:")
            print(f"   1. Delete existing and upload new: localagent-dev release {version} <zip> --force")
            print(f"   2. Bump version and try again")
            response = input(f"\n   Delete existing v{version} and upload new? [y/N]: ").strip().lower()
            if response == 'y':
                force = True
            else:
                return {"success": False, "error": f"Release v{version} already exists. Use --force to overwrite."}
        
        if force:
            print(f"🗑️  Deleting existing release v{version}...")
            delete_result = delete_release(f"v{version}")
            if not delete_result.get("success"):
                return {"success": False, "error": f"Failed to delete existing release: {delete_result.get('error')}"}
    
    repo = get_repo_config()
    if not repo.get("owner_repo"):
        return {"success": False, "error": "Repository not configured. Run: localagent-dev set-repo <url>"}
    
    owner_repo = repo["owner_repo"]
    
    # Step 0b: Verify repo exists
    repo_info = verify_repo(owner_repo)
    if not repo_info.get("exists"):
        if auto_create_repo:
            print(f"📦 Repository {owner_repo} not found. Creating...")
            parts = owner_repo.split("/")
            if len(parts) == 2:
                owner, name = parts
                # Check if it's an org or user
                user = token_info.get("user")
                if owner == user:
                    create_result = create_repo(name, org=None, private=False)
                else:
                    create_result = create_repo(name, org=owner, private=False)
                
                if not create_result.get("success"):
                    return {"success": False, "error": f"Could not create repo: {create_result.get('error')}"}
                
                # Update repo URL
                set_repo_url(create_result.get("url"))
            else:
                return {"success": False, "error": f"Invalid repo format: {owner_repo}"}
        else:
            return {"success": False, "error": f"Repository not found: {owner_repo}. {repo_info.get('error')}"}
    else:
        if not repo_info.get("can_push"):
            return {"success": False, "error": f"No push access to {owner_repo}"}
        print(f"✅ Repository verified: {repo_info.get('full_name')} (push: {'yes' if repo_info.get('can_push') else 'no'})")
    
    zip_file = Path(zip_path)
    if not zip_file.exists():
        return {"success": False, "error": f"ZIP file not found: {zip_path}"}
    
    tag_name = f"v{version}"
    
    # Auto-generate release notes if not provided
    if not release_notes:
        release_notes = _generate_release_notes(version)
    
    print(f"📤 Creating release {tag_name} on {owner_repo}...")
    
    # Step 1: Create the release
    release_data = {
        "tag_name": tag_name,
        "name": f"LocalAgent {tag_name}",
        "body": release_notes,
        "draft": False,
        "prerelease": prerelease
    }
    
    response = _github_api("POST", f"/repos/{owner_repo}/releases", release_data)
    
    if "error" in response:
        return {"success": False, "error": response["error"]}
    
    if "id" not in response:
        return {"success": False, "error": f"Failed to create release: {response.get('message', 'Unknown error')}"}
    
    release_id = response["id"]
    release_url = response.get("html_url", "")
    upload_url = response.get("upload_url", "")
    
    print(f"✅ Release created: {release_url}")
    
    # Step 2: Upload the ZIP asset
    print(f"📦 Uploading {zip_file.name}...")
    
    upload_response = _upload_asset(upload_url, zip_file)
    
    if "error" in upload_response:
        return {
            "success": False,
            "error": f"Release created but asset upload failed: {upload_response['error']}",
            "release_url": release_url
        }
    
    download_url = upload_response.get("browser_download_url", "")
    
    print(f"✅ Asset uploaded: {download_url}")
    
    # Step 3: Update local version history
    from ..connectors.github import update_version_history
    update_version_history(version, [f"Released to GitHub: {release_url}"])
    
    return {
        "success": True,
        "version": version,
        "tag": tag_name,
        "release_url": release_url,
        "download_url": download_url,
        "release_id": release_id
    }


def _generate_release_notes(version: str) -> str:
    """Generate release notes from changelog."""
    try:
        from ..engine.tracking import get_changelog
        
        # Try to get changelog for this version
        changelog = get_changelog("localagent")
        
        notes = [f"## LocalAgent v{version}\n"]
        
        # Find changes for this version
        for entry in changelog:
            if entry.get("version") == version:
                notes.append("### Changes\n")
                for change in entry.get("changes", []):
                    notes.append(f"- {change}")
                break
        else:
            notes.append("### Changes\n")
            notes.append("- See CHANGELOG for details")
        
        notes.append("\n---")
        notes.append(f"\n*Released: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
        
        return "\n".join(notes)
        
    except Exception as e:
        return f"## LocalAgent v{version}\n\nRelease {version}\n\n*Released: {datetime.now().isoformat()}*"


# ============================================================
# LIST RELEASES
# ============================================================

def list_releases(limit: int = 10) -> List[Dict]:
    """List recent releases from GitHub."""
    repo = get_repo_config()
    if not repo.get("owner_repo"):
        return []
    
    owner_repo = repo["owner_repo"]
    response = _github_api("GET", f"/repos/{owner_repo}/releases?per_page={limit}")
    
    if "error" in response or not isinstance(response, list):
        return []
    
    releases = []
    for r in response:
        releases.append({
            "version": r.get("tag_name", "").lstrip("v"),
            "tag": r.get("tag_name"),
            "name": r.get("name"),
            "published_at": r.get("published_at"),
            "prerelease": r.get("prerelease"),
            "url": r.get("html_url"),
            "download_url": next(
                (a.get("browser_download_url") for a in r.get("assets", []) if a.get("name", "").endswith(".zip")),
                None
            )
        })
    
    return releases
