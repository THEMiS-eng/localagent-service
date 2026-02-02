"""
Spotlight Connector - macOS Native Search

Features:
- mdfind CLI for Spotlight search
- Full-text search in documents
- Metadata search (tags, dates, types)
- Smart Folders (saved searches)
"""

import subprocess
import os
import logging
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Data directory for Themis
DATA_DIR = Path.home() / ".localagent" / "themis"
UPLOADS_DIR = DATA_DIR / "uploads"


def is_macos() -> bool:
    """Check if running on macOS."""
    import platform
    return platform.system() == "Darwin"


def mdfind(query: str, scope: str = None, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Search using macOS Spotlight (mdfind).
    
    Args:
        query: Search query (Spotlight query syntax)
        scope: Directory to limit search to
        limit: Max results
    
    Returns:
        List of matching files with metadata
    """
    if not is_macos():
        logger.warning("[SPOTLIGHT] Not on macOS, using fallback search")
        return fallback_search(query, scope, limit)
    
    try:
        cmd = ["mdfind"]
        
        if scope:
            cmd.extend(["-onlyin", str(scope)])
        
        cmd.append(query)
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            logger.error(f"[SPOTLIGHT] mdfind error: {result.stderr}")
            return []
        
        files = result.stdout.strip().split("\n")
        files = [f for f in files if f][:limit]
        
        # Get metadata for each file
        results = []
        for filepath in files:
            meta = get_file_metadata(filepath)
            if meta:
                results.append(meta)
        
        return results
    
    except subprocess.TimeoutExpired:
        logger.error("[SPOTLIGHT] mdfind timeout")
        return []
    except Exception as e:
        logger.error(f"[SPOTLIGHT] Error: {e}")
        return fallback_search(query, scope, limit)


def get_file_metadata(filepath: str) -> Optional[Dict[str, Any]]:
    """Get file metadata using mdls."""
    if not is_macos() or not os.path.exists(filepath):
        return None
    
    try:
        result = subprocess.run(
            ["mdls", "-plist", "-", filepath],
            capture_output=True,
            timeout=5
        )
        
        if result.returncode == 0:
            import plistlib
            meta = plistlib.loads(result.stdout)
            
            return {
                "path": filepath,
                "filename": os.path.basename(filepath),
                "size": os.path.getsize(filepath),
                "modified": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat(),
                "content_type": meta.get("kMDItemContentType", ""),
                "title": meta.get("kMDItemTitle", os.path.basename(filepath)),
                "tags": meta.get("kMDItemUserTags", []),
                "spotlight_meta": {
                    "kind": meta.get("kMDItemKind", ""),
                    "creator": meta.get("kMDItemCreator", ""),
                    "pages": meta.get("kMDItemNumberOfPages"),
                }
            }
    except Exception as e:
        logger.error(f"[SPOTLIGHT] mdls error for {filepath}: {e}")
    
    # Basic fallback
    return {
        "path": filepath,
        "filename": os.path.basename(filepath),
        "size": os.path.getsize(filepath) if os.path.exists(filepath) else 0,
        "modified": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat() if os.path.exists(filepath) else None,
    }


def fallback_search(query: str, scope: str = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Fallback search when Spotlight unavailable."""
    results = []
    search_dir = Path(scope) if scope else UPLOADS_DIR
    
    if not search_dir.exists():
        return []
    
    query_lower = query.lower()
    
    for filepath in search_dir.rglob("*"):
        if filepath.is_file():
            # Search in filename
            if query_lower in filepath.name.lower():
                results.append({
                    "path": str(filepath),
                    "filename": filepath.name,
                    "size": filepath.stat().st_size,
                    "modified": datetime.fromtimestamp(filepath.stat().st_mtime).isoformat(),
                    "match_type": "filename"
                })
            # Search in content (text files only)
            elif filepath.suffix.lower() in [".txt", ".md", ".json", ".csv"]:
                try:
                    content = filepath.read_text(errors="ignore")
                    if query_lower in content.lower():
                        results.append({
                            "path": str(filepath),
                            "filename": filepath.name,
                            "size": filepath.stat().st_size,
                            "modified": datetime.fromtimestamp(filepath.stat().st_mtime).isoformat(),
                            "match_type": "content"
                        })
                except:
                    pass
        
        if len(results) >= limit:
            break
    
    return results


def search_evidence(query: str, case_id: str = None) -> List[Dict[str, Any]]:
    """Search evidence using Spotlight."""
    scope = str(UPLOADS_DIR / case_id) if case_id else str(UPLOADS_DIR)
    
    # Build Spotlight query
    # kMDItemTextContent for full-text, kMDItemDisplayName for filename
    spotlight_query = f'(kMDItemTextContent == "*{query}*"wcd || kMDItemDisplayName == "*{query}*"cd)'
    
    return mdfind(spotlight_query, scope=scope)


def get_tags(filepath: str) -> List[str]:
    """Get macOS tags for a file using xattr."""
    if not is_macos() or not os.path.exists(filepath):
        return []
    
    try:
        result = subprocess.run(
            ["xattr", "-p", "com.apple.metadata:_kMDItemUserTags", filepath],
            capture_output=True,
            timeout=5
        )
        
        if result.returncode == 0:
            import plistlib
            tags = plistlib.loads(result.stdout)
            return tags if isinstance(tags, list) else []
    except:
        pass
    
    return []


def set_tags(filepath: str, tags: List[str]) -> bool:
    """Set macOS tags for a file using xattr."""
    if not is_macos() or not os.path.exists(filepath):
        return False
    
    try:
        import plistlib
        plist_data = plistlib.dumps(tags)
        
        result = subprocess.run(
            ["xattr", "-w", "com.apple.metadata:_kMDItemUserTags", plist_data.hex(), filepath],
            capture_output=True,
            timeout=5
        )
        
        return result.returncode == 0
    except Exception as e:
        logger.error(f"[SPOTLIGHT] Failed to set tags: {e}")
    
    return False


def add_tag(filepath: str, tag: str) -> bool:
    """Add a tag to a file."""
    tags = get_tags(filepath)
    if tag not in tags:
        tags.append(tag)
        return set_tags(filepath, tags)
    return True


def remove_tag(filepath: str, tag: str) -> bool:
    """Remove a tag from a file."""
    tags = get_tags(filepath)
    if tag in tags:
        tags.remove(tag)
        return set_tags(filepath, tags)
    return True


# Smart Folders (saved searches)
SMART_FOLDERS_FILE = DATA_DIR / "smart_folders.json"


def get_smart_folders() -> List[Dict[str, Any]]:
    """Get saved smart folders."""
    if SMART_FOLDERS_FILE.exists():
        return json.loads(SMART_FOLDERS_FILE.read_text())
    
    # Default smart folders
    return [
        {"id": "recent", "name": "Recent Documents", "query": "kMDItemFSContentChangeDate >= $time.today(-7)"},
        {"id": "contracts", "name": "Contracts", "query": "kMDItemDisplayName == '*contract*'cd"},
        {"id": "reports", "name": "Reports", "query": "kMDItemDisplayName == '*report*'cd"},
        {"id": "pending", "name": "Pending Review", "query": "kMDItemUserTags == 'pending'"},
    ]


def save_smart_folder(folder: Dict[str, Any]) -> bool:
    """Save a smart folder."""
    folders = get_smart_folders()
    
    # Update or add
    found = False
    for i, f in enumerate(folders):
        if f["id"] == folder["id"]:
            folders[i] = folder
            found = True
            break
    
    if not found:
        folders.append(folder)
    
    SMART_FOLDERS_FILE.write_text(json.dumps(folders, indent=2))
    return True


def execute_smart_folder(folder_id: str, case_id: str = None) -> List[Dict[str, Any]]:
    """Execute a smart folder query."""
    folders = get_smart_folders()
    
    for f in folders:
        if f["id"] == folder_id:
            scope = str(UPLOADS_DIR / case_id) if case_id else str(UPLOADS_DIR)
            return mdfind(f["query"], scope=scope)
    
    return []
