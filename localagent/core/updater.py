"""
LocalAgent v2.10.37 - CORE: Updater
Local update system - upload zip via dashboard to update
"""

import json
import shutil
import zipfile
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from ..engine.project import AGENT_DIR


# ============================================================
# PATHS
# ============================================================

RELEASES_DIR = AGENT_DIR / "releases"
CURRENT_DIR = RELEASES_DIR / "current"
AVAILABLE_DIR = RELEASES_DIR / "available"
BACKUPS_DIR = RELEASES_DIR / "backups"
MANIFEST_FILE = RELEASES_DIR / "manifest.json"


def _ensure_dirs():
    """Create release directories if needed."""
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)
    CURRENT_DIR.mkdir(exist_ok=True)
    AVAILABLE_DIR.mkdir(exist_ok=True)
    BACKUPS_DIR.mkdir(exist_ok=True)


# ============================================================
# MANIFEST
# ============================================================

def get_manifest() -> Dict:
    """Get release manifest."""
    if MANIFEST_FILE.exists():
        try:
            return json.loads(MANIFEST_FILE.read_text())
        except:
            pass
    return {
        "current_version": None,
        "available_version": None,
        "last_check": None,
        "history": []
    }


def save_manifest(manifest: Dict):
    """Save release manifest."""
    _ensure_dirs()
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2))


def get_current_version() -> str:
    """Get currently installed version."""
    try:
        from localagent.main import VERSION
        return VERSION
    except:
        manifest = get_manifest()
        return manifest.get("current_version", "unknown")


def get_available_version() -> Optional[str]:
    """Get version available for update (if any)."""
    manifest = get_manifest()
    return manifest.get("available_version")


# ============================================================
# UPLOAD & EXTRACT
# ============================================================

def upload_release(zip_path: str) -> Dict:
    """
    Upload a new release zip file.
    
    Args:
        zip_path: Path to the uploaded zip file
        
    Returns:
        {
            "success": bool,
            "version": str (extracted version),
            "error": str (if failed)
        }
    """
    _ensure_dirs()
    
    zip_file = Path(zip_path)
    if not zip_file.exists():
        return {"success": False, "error": "File not found"}
    
    if not zip_file.suffix == ".zip":
        return {"success": False, "error": "Not a zip file"}
    
    # Clear available directory
    if AVAILABLE_DIR.exists():
        shutil.rmtree(AVAILABLE_DIR)
    AVAILABLE_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        # Extract zip
        with zipfile.ZipFile(zip_file, 'r') as zf:
            zf.extractall(AVAILABLE_DIR)
        
        # Find version in extracted files
        version = _detect_version(AVAILABLE_DIR)
        
        if not version:
            return {"success": False, "error": "Could not detect version in zip"}
        
        # Update manifest
        manifest = get_manifest()
        manifest["available_version"] = version
        manifest["available_path"] = str(AVAILABLE_DIR)
        manifest["available_uploaded"] = datetime.now().isoformat()
        manifest["available_file"] = zip_file.name
        save_manifest(manifest)
        
        print(f"📦 Release uploaded: v{version}")
        
        return {
            "success": True,
            "version": version,
            "current": get_current_version(),
            "needs_update": version != get_current_version()
        }
        
    except zipfile.BadZipFile:
        return {"success": False, "error": "Invalid zip file"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _detect_version(extract_dir: Path) -> Optional[str]:
    """Detect version from extracted files."""
    
    # Look for VERSION file
    for version_file in extract_dir.rglob("VERSION"):
        content = version_file.read_text().strip()
        if content:
            return content
    
    # Look for version in main.py
    for main_file in extract_dir.rglob("main.py"):
        content = main_file.read_text()
        for line in content.split("\n"):
            if line.startswith("VERSION"):
                # VERSION = "2.10.37"
                try:
                    version = line.split("=")[1].strip().strip('"\'')
                    return version
                except:
                    pass
    
    # Look for version in setup.py
    for setup_file in extract_dir.rglob("setup.py"):
        content = setup_file.read_text()
        if "version=" in content:
            try:
                import re
                match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    return match.group(1)
            except:
                pass
    
    return None


# ============================================================
# INSTALL UPDATE
# ============================================================

def install_update() -> Dict:
    """
    Install the available update.
    
    1. Backup current installation
    2. Install new version
    3. Run pip install
    4. Update manifest
    
    Returns:
        {
            "success": bool,
            "old_version": str,
            "new_version": str,
            "error": str (if failed),
            "rollback_available": bool
        }
    """
    manifest = get_manifest()
    
    available_version = manifest.get("available_version")
    if not available_version:
        return {"success": False, "error": "No update available"}
    
    current_version = get_current_version()
    
    # Use explicit install location ~/localagent_v3
    install_root = Path.home() / "localagent_v3"
    current_install = install_root / "localagent"
    
    if not install_root.exists():
        return {"success": False, "error": f"Install directory not found: {install_root}"}
    
    # Create backup
    backup_name = f"backup_v{current_version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_path = BACKUPS_DIR / backup_name
    
    try:
        print(f"📦 Backing up v{current_version}...")
        if current_install.exists():
            shutil.copytree(current_install, backup_path)
        else:
            print(f"⚠️ No localagent/ dir to backup")
        
        # Find the localagent_v3 root directory in the update
        new_root = None
        new_localagent = None
        
        # Debug: list what's in AVAILABLE_DIR
        print(f"📂 AVAILABLE_DIR contents: {list(AVAILABLE_DIR.iterdir())}")
        
        # Look for localagent_v3 directory (contains VERSION, dashboard/, localagent/)
        for path in AVAILABLE_DIR.iterdir():
            print(f"  Checking: {path}, has VERSION: {(path / 'VERSION').exists() if path.is_dir() else 'N/A'}")
            if path.is_dir() and (path / "VERSION").exists():
                new_root = path
                print(f"  ✓ Found new_root: {new_root}")
                break
        
        # Fallback: look for localagent package
        for path in AVAILABLE_DIR.rglob("localagent"):
            if path.is_dir() and (path / "__init__.py").exists():
                new_localagent = path
                print(f"  ✓ Found new_localagent: {new_localagent}")
                if not new_root:
                    new_root = path.parent
                break
        
        if not new_localagent and not new_root:
            return {"success": False, "error": "Cannot find localagent in update", "rollback_available": True}
        
        print(f"📥 Installing v{available_version}...")
        print(f"   new_root: {new_root}")
        print(f"   install_root: {install_root}")
        
        # Copy ALL files from new_root to install_root
        if new_root:
            copied_items = []
            for item in new_root.iterdir():
                src = item
                dst = install_root / item.name
                
                print(f"   Copying: {src.name} -> {dst}")
                
                if src.is_dir():
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
                copied_items.append(item.name)
            print(f"✅ Copied: {', '.join(copied_items)}")
            
            # Verify VERSION was updated
            version_file = install_root / "VERSION"
            if version_file.exists():
                actual_new_version = version_file.read_text().strip()
                print(f"✅ VERSION file now reads: {actual_new_version}")
            else:
                actual_new_version = available_version
                print(f"⚠️ No VERSION file found")
        else:
            # Fallback: just copy localagent package
            actual_new_version = available_version
            for item in new_localagent.iterdir():
                src = item
                dst = current_install / item.name
                
                if src.is_dir():
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
        
        # Run pip install if setup.py exists
        setup_py = AVAILABLE_DIR / "setup.py"
        if not setup_py.exists():
            # Look deeper
            for sp in AVAILABLE_DIR.rglob("setup.py"):
                setup_py = sp
                break
        
        if setup_py.exists():
            print("📦 Running pip install...")
            result = subprocess.run(
                ["pip3", "install", "-e", str(setup_py.parent)],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                print(f"⚠️ pip install warning: {result.stderr[:200]}")
        
        # Update manifest
        manifest["current_version"] = actual_new_version
        manifest["available_version"] = None
        manifest["last_update"] = datetime.now().isoformat()
        manifest["history"].append({
            "from": current_version,
            "to": actual_new_version,
            "date": datetime.now().isoformat(),
            "backup": backup_name
        })
        save_manifest(manifest)
        
        # Push to GitHub - update version history
        print("📤 Pushing to GitHub...")
        try:
            from .orchestrator import git_sync_to_remote
            from ..connectors.github import update_version_history
            
            # Update GitHub version history
            update_version_history(actual_new_version, [
                f"Updated from v{current_version}",
                f"Installed via dashboard upload"
            ])
            
            # If project has git, sync to remote
            # Note: This syncs the project, not the app itself
            # The app version is tracked in github.json
            
            print(f"✅ GitHub updated with v{available_version}")
        except Exception as e:
            print(f"⚠️ GitHub push skipped: {e}")
        
        print(f"✅ Updated: v{current_version} → v{actual_new_version}")
        
        return {
            "success": True,
            "old_version": current_version,
            "new_version": actual_new_version,
            "rollback_available": True,
            "backup": backup_name,
            "restart_required": True
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "rollback_available": backup_path.exists()
        }


# ============================================================
# ROLLBACK
# ============================================================

def rollback(backup_name: str = None) -> Dict:
    """
    Rollback to a previous version.
    
    Args:
        backup_name: Specific backup to restore, or None for latest
        
    Returns:
        {
            "success": bool,
            "restored_version": str,
            "error": str (if failed)
        }
    """
    # Find backup to restore
    if backup_name:
        backup_path = BACKUPS_DIR / backup_name
    else:
        # Get latest backup
        backups = sorted(BACKUPS_DIR.iterdir(), reverse=True) if BACKUPS_DIR.exists() else []
        if not backups:
            return {"success": False, "error": "No backups available"}
        backup_path = backups[0]
    
    if not backup_path.exists():
        return {"success": False, "error": f"Backup not found: {backup_name}"}
    
    try:
        import localagent
        current_install = Path(localagent.__file__).parent
        
        # Extract version from backup name
        restored_version = "unknown"
        if "backup_v" in backup_path.name:
            restored_version = backup_path.name.split("_v")[1].split("_")[0]
        
        print(f"🔄 Rolling back to v{restored_version}...")
        
        # Replace current with backup
        shutil.rmtree(current_install)
        shutil.copytree(backup_path, current_install)
        
        # Update manifest
        manifest = get_manifest()
        manifest["current_version"] = restored_version
        manifest["last_rollback"] = datetime.now().isoformat()
        save_manifest(manifest)
        
        print(f"✅ Rolled back to v{restored_version}")
        
        return {
            "success": True,
            "restored_version": restored_version,
            "restart_required": True
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# LIST BACKUPS
# ============================================================

def list_backups() -> list:
    """List available backups."""
    if not BACKUPS_DIR.exists():
        return []
    
    backups = []
    for backup in sorted(BACKUPS_DIR.iterdir(), reverse=True):
        if backup.is_dir():
            # Parse backup name: backup_v2.10.37_20250120_183000
            parts = backup.name.split("_")
            version = parts[1][1:] if len(parts) > 1 else "unknown"  # Remove 'v'
            date = f"{parts[2]}_{parts[3]}" if len(parts) > 3 else "unknown"
            
            backups.append({
                "name": backup.name,
                "version": version,
                "date": date,
                "path": str(backup),
                "size": sum(f.stat().st_size for f in backup.rglob("*") if f.is_file())
            })
    
    return backups


# ============================================================
# STATUS
# ============================================================

def get_update_status() -> Dict:
    """Get current update status for dashboard."""
    manifest = get_manifest()
    
    current = get_current_version()
    available = manifest.get("available_version")
    
    return {
        "current_version": current,
        "available_version": available,
        "update_available": available is not None and available != current,
        "last_check": manifest.get("last_check"),
        "last_update": manifest.get("last_update"),
        "backups": len(list_backups()),
        "history": manifest.get("history", [])[-5:]  # Last 5 updates
    }
