"""
Modules Router - handles module management and auto-push
"""
from fastapi import APIRouter
from typing import Dict, Any
from pathlib import Path
import json

router = APIRouter(prefix="/api", tags=["modules"])


@router.get("/modules")
async def get_modules():
    """Get available modules."""
    modules_dir = Path.home() / "localagent_v3" / "modules"
    if not modules_dir.exists():
        return {"modules": [], "count": 0}
    
    modules = []
    for d in modules_dir.iterdir():
        if d.is_dir() and not d.name.startswith("."):
            pkg_file = d / "package.json"
            if pkg_file.exists():
                try:
                    pkg = json.loads(pkg_file.read_text())
                    modules.append({
                        "name": pkg.get("name", d.name),
                        "version": pkg.get("version", "0.0.0"),
                        "description": pkg.get("description", ""),
                        "path": str(d)
                    })
                except:
                    modules.append({"name": d.name, "path": str(d)})
    
    return {"modules": modules, "count": len(modules)}


@router.post("/modules/init")
async def init_module(data: Dict[str, Any]):
    """Initialize a new module from template."""
    name = data.get("name", "new-module")
    template = data.get("template", "basic")
    
    modules_dir = Path.home() / "localagent_v3" / "modules"
    module_dir = modules_dir / name
    
    if module_dir.exists():
        return {"error": "Module already exists", "path": str(module_dir)}
    
    module_dir.mkdir(parents=True, exist_ok=True)
    
    # Create basic structure
    pkg = {
        "name": name,
        "version": "1.0.0",
        "description": f"LocalAgent module: {name}",
        "main": "index.js"
    }
    (module_dir / "package.json").write_text(json.dumps(pkg, indent=2))
    (module_dir / "index.js").write_text(f"// {name} module\nexport default {{}};")
    (module_dir / "README.md").write_text(f"# {name}\n\nLocalAgent module.")
    
    return {"created": True, "path": str(module_dir), "name": name}


@router.post("/modules/push")
async def push_module(data: Dict[str, Any]):
    """Push a module to GitHub."""
    from ...connectors.github import github_push
    
    name = data.get("name")
    if not name:
        return {"error": "Module name required"}
    
    module_dir = Path.home() / "localagent_v3" / "modules" / name
    if not module_dir.exists():
        return {"error": "Module not found", "path": str(module_dir)}
    
    # Get version from package.json
    pkg_file = module_dir / "package.json"
    version = "1.0.0"
    if pkg_file.exists():
        try:
            pkg = json.loads(pkg_file.read_text())
            version = pkg.get("version", "1.0.0")
        except:
            pass
    
    message = data.get("message", f"Update {name} v{version}")
    
    try:
        result = github_push(str(module_dir), version, message)
        return {"pushed": True, "module": name, "version": version, "result": result}
    except Exception as e:
        return {"error": str(e), "module": name}
