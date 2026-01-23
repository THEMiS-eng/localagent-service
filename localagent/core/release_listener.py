"""
LocalAgent v2.10.38 - CORE: Release Listener
Monitors GitHub repository for new releases
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List

from ..engine.project import AGENT_DIR, CONFIG_DIR


# ============================================================
# PATHS
# ============================================================

RELEASES_DIR = AGENT_DIR / "releases"
RELEASE_CACHE = RELEASES_DIR / "latest_release.json"


def _ensure_dirs():
    """Create directories if needed."""
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# GITHUB RELEASE API
# ============================================================

def fetch_latest_release(repo_url: str = None) -> Optional[Dict]:
    """
    Fetch latest release info from GitHub.
    
    Args:
        repo_url: GitHub repo URL (e.g., https://github.com/user/localagent)
        
    Returns:
        {
            "version": "2.10.39",
            "tag": "v2.10.39",
            "name": "Release 2.10.39",
            "body": "Release notes markdown...",
            "published_at": "2025-01-20T...",
            "download_url": "https://github.com/.../localagent_v2.10.39.zip",
            "assets": [...]
        }
    """
    _ensure_dirs()
    
    # Get repo URL from config if not provided
    if not repo_url:
        from ..connectors.github import _load_config
        config = _load_config()
        repos = config.get("repos", {})
        if "localagent" in repos:
            repo_url = repos["localagent"].get("url")
    
    if not repo_url:
        return None
    
    # Convert to API URL
    # https://github.com/user/repo -> https://api.github.com/repos/user/repo/releases/latest
    if "github.com" in repo_url:
        parts = repo_url.rstrip("/").split("github.com/")[-1]
        api_url = f"https://api.github.com/repos/{parts}/releases/latest"
    else:
        return None
    
    try:
        # Use curl to fetch (available on Mac/Linux)
        # Include auth token for private repos
        from .release_publisher import get_github_token
        token = get_github_token()
        
        cmd = ["curl", "-s", "-H", "Accept: application/vnd.github.v3+json"]
        if token:
            cmd.extend(["-H", f"Authorization: token {token}"])
        cmd.append(api_url)
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return None
        
        data = json.loads(result.stdout)
        
        if "tag_name" not in data:
            return None
        
        # Parse version from tag
        tag = data.get("tag_name", "")
        version = tag.lstrip("v")
        
        # Find zip asset
        download_url = None
        for asset in data.get("assets", []):
            if asset.get("name", "").endswith(".zip"):
                download_url = asset.get("browser_download_url")
                break
        
        release_info = {
            "version": version,
            "tag": tag,
            "name": data.get("name", f"Release {version}"),
            "body": data.get("body", ""),
            "published_at": data.get("published_at"),
            "download_url": download_url,
            "html_url": data.get("html_url"),
            "assets": data.get("assets", [])
        }
        
        # Cache it
        RELEASE_CACHE.write_text(json.dumps(release_info, indent=2))
        
        return release_info
        
    except Exception as e:
        print(f"⚠️ Could not fetch release: {e}")
        return None


def get_cached_release() -> Optional[Dict]:
    """Get cached release info."""
    if RELEASE_CACHE.exists():
        try:
            return json.loads(RELEASE_CACHE.read_text())
        except:
            pass
    return None


# ============================================================
# UPDATE CHECK
# ============================================================

def check_for_update() -> Dict:
    """
    Check if update is available.
    
    Returns:
        {
            "update_available": bool,
            "current_version": str,
            "latest_version": str,
            "release_notes": str,
            "download_url": str
        }
    """
    from ..main import VERSION as current_version
    
    # Try to fetch latest, fall back to cache
    latest = fetch_latest_release()
    if not latest:
        latest = get_cached_release()
    
    if not latest:
        return {
            "update_available": False,
            "current_version": current_version,
            "latest_version": None,
            "error": "Could not check for updates"
        }
    
    latest_version = latest.get("version", "0.0.0")
    
    # Compare versions
    def version_tuple(v):
        try:
            return tuple(int(x) for x in v.split("."))
        except:
            return (0, 0, 0)
    
    update_available = version_tuple(latest_version) > version_tuple(current_version)
    
    return {
        "update_available": update_available,
        "current_version": current_version,
        "latest_version": latest_version,
        "release_name": latest.get("name"),
        "release_notes": latest.get("body", ""),
        "download_url": latest.get("download_url"),
        "html_url": latest.get("html_url"),
        "published_at": latest.get("published_at")
    }


# ============================================================
# DOWNLOAD & INSTALL
# ============================================================

def download_release(download_url: str) -> Optional[Path]:
    """
    Download release zip from GitHub.
    
    Returns path to downloaded file.
    """
    _ensure_dirs()
    
    if not download_url:
        return None
    
    # Extract filename
    filename = download_url.split("/")[-1]
    download_path = RELEASES_DIR / filename
    
    try:
        print(f"📥 Downloading {filename}...")
        
        # Include auth token for private repos
        from .release_publisher import get_github_token
        token = get_github_token()
        
        cmd = ["curl", "-L", "-o", str(download_path)]
        if token:
            cmd.extend(["-H", f"Authorization: token {token}"])
            cmd.extend(["-H", "Accept: application/octet-stream"])
        cmd.append(download_url)
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0 and download_path.exists() and download_path.stat().st_size > 1000:
            print(f"✅ Downloaded: {download_path}")
            return download_path
        
        print(f"❌ Download failed or file too small")
        return None
        
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return None


def install_from_github() -> Dict:
    """
    Download and install latest release from GitHub.
    
    Returns:
        {
            "success": bool,
            "old_version": str,
            "new_version": str,
            "error": str (if failed)
        }
    """
    from .updater import upload_release, install_update
    
    # Check for update first
    update_info = check_for_update()
    
    if not update_info.get("update_available"):
        return {
            "success": False,
            "error": "No update available",
            "current_version": update_info.get("current_version")
        }
    
    download_url = update_info.get("download_url")
    if not download_url:
        return {
            "success": False,
            "error": "No download URL in release"
        }
    
    # Download
    zip_path = download_release(download_url)
    if not zip_path:
        return {
            "success": False,
            "error": "Download failed"
        }
    
    # Upload to updater (extracts and validates)
    upload_result = upload_release(str(zip_path))
    if not upload_result.get("success"):
        return upload_result
    
    # Install
    install_result = install_update()
    
    # Clean up download
    try:
        zip_path.unlink()
    except:
        pass
    
    return install_result
