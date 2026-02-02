"""
Config Router - handles API keys, apps registration, settings
"""
from fastapi import APIRouter, Request
from typing import Dict, Any
from pathlib import Path
import json
import os

router = APIRouter(prefix="/api", tags=["config"])


@router.get("/config/api-key/status")
async def get_api_key_status():
    """Check if API key is configured."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    return {"configured": bool(key), "masked": f"sk-...{key[-4:]}" if key else None}


@router.post("/config/api-key")
async def set_api_key(data: Dict[str, Any]):
    """Set API key (session only)."""
    key = data.get("key", "")
    if key:
        os.environ["ANTHROPIC_API_KEY"] = key
        return {"set": True, "masked": f"sk-...{key[-4:]}"}
    return {"set": False, "error": "No key provided"}


@router.get("/app")
async def get_app_info():
    """Get app info."""
    return {
        "name": "LocalAgent",
        "version": _get_version(),
        "project": "LOCALAGENT"
    }


@router.post("/apps/register")
async def register_app(data: Dict[str, Any]):
    """Register an external app."""
    apps_file = Path.home() / ".localagent" / "apps.json"
    apps_file.parent.mkdir(parents=True, exist_ok=True)
    
    apps = []
    if apps_file.exists():
        try:
            apps = json.loads(apps_file.read_text())
        except:
            apps = []
    
    app = {
        "name": data.get("name", "unknown"),
        "url": data.get("url", ""),
        "registered": True
    }
    apps.append(app)
    apps_file.write_text(json.dumps(apps, indent=2))
    
    return {"registered": True, "app": app}


@router.get("/apps")
async def get_apps():
    """Get registered apps."""
    apps_file = Path.home() / ".localagent" / "apps.json"
    if not apps_file.exists():
        return {"apps": []}
    try:
        apps = json.loads(apps_file.read_text())
        return {"apps": apps}
    except:
        return {"apps": []}


def _get_version():
    # Try to find VERSION file relative to package
    import sys
    from pathlib import Path
    
    # Check multiple locations
    possible_paths = [
        Path(__file__).parent.parent.parent.parent / "VERSION",  # localagent package root
        Path.cwd() / "VERSION",  # current working directory
        Path.home() / ".localagent" / "VERSION",
    ]
    
    for version_file in possible_paths:
        if version_file.exists():
            return version_file.read_text().strip()
    
    return "0.0.0"


# Connected Apps Registry
_connected_apps = {}


@router.get("/apps")
async def get_apps():
    """Get list of connected apps."""
    apps = []
    for app_id, app_data in _connected_apps.items():
        # Check if app is still online
        status = "offline"
        try:
            import requests
            r = requests.get(f"http://localhost:{app_data.get('port', 8765)}/api/health", timeout=1)
            if r.ok:
                status = "online"
        except:
            pass
        
        apps.append({
            "id": app_id,
            "name": app_data.get("name", app_id),
            "version": app_data.get("version", "?"),
            "port": app_data.get("port", "?"),
            "status": status,
            "registered_at": app_data.get("registered_at")
        })
    
    return {"apps": apps}


@router.post("/apps/register")
async def register_app(request: Request):
    """Register an app with LocalAgent."""
    from datetime import datetime
    
    data = await request.json()
    app_id = data.get("app_id") or data.get("id")
    if not app_id:
        return {"error": "app_id required"}
    
    _connected_apps[app_id] = {
        "name": data.get("name", app_id),
        "version": data.get("version", "?"),
        "port": data.get("port", 8765),
        "registered_at": datetime.now().isoformat()
    }
    
    return {"status": "registered", "app_id": app_id}


@router.delete("/apps/{app_id}")
async def unregister_app(app_id: str):
    """Unregister an app."""
    if app_id in _connected_apps:
        del _connected_apps[app_id]
        return {"status": "unregistered"}
    return {"error": "App not found"}
