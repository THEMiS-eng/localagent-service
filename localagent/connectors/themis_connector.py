"""
Themis Connector for LocalAgent

Gère:
- UI Themis servie par LocalAgent
- Proxy vers Themis Backend (localhost:8765)
- Intégration MLX, Spotlight, Tags macOS
- WebSocket bridge
- Linting des prompts chat
- Version/Release management
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import json
import asyncio
import httpx

router = APIRouter(prefix="/connector/themis", tags=["themis-connector"])

# =============================================================================
# CONFIGURATION
# =============================================================================

THEMIS_BACKEND = "http://localhost:8765"
THEMIS_WS = "ws://localhost:8765/ws"
THEMIS_VERSION = "10.1.9"
PROXY_TIMEOUT = 30.0

# WebSocket clients
_themis_clients: Set[WebSocket] = set()


# =============================================================================
# THEMIS UI
# =============================================================================

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def serve_themis():
    """Serve Themis UI with LocalAgent integration."""
    search_paths = [
        Path(__file__).parent.parent.parent / "themis_v10_1_9_with_localagent.html",
        Path(__file__).parent.parent.parent / "themis.html",
    ]
    
    for path in search_paths:
        if path.exists():
            return HTMLResponse(path.read_text())
    
    return HTMLResponse("""
        <html><head><title>Themis</title></head>
        <body style="font-family:system-ui;padding:40px;text-align:center">
            <h1>Themis Connector Active</h1>
            <p>Themis UI file not found. Place themis_v10_1_9_with_localagent.html in localagent root.</p>
        </body></html>
    """)


# =============================================================================
# CONNECTOR STATUS & CONFIG
# =============================================================================

@router.get("/status")
async def themis_status():
    """Get Themis connector status."""
    themis_online = False
    themis_version = None
    
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{THEMIS_BACKEND}/api/health")
            if r.status_code == 200:
                themis_online = True
                data = r.json()
                themis_version = data.get("version")
    except:
        pass
    
    return {
        "connector": "themis",
        "connector_version": "4.1.0",
        "themis_backend": THEMIS_BACKEND,
        "themis_online": themis_online,
        "themis_version": themis_version or THEMIS_VERSION,
        "websocket_clients": len(_themis_clients),
        "features": {
            "proxy": True,
            "mlx": True,
            "spotlight": True,
            "tags": True,
            "smartfolders": True,
            "chat_linting": True
        }
    }


@router.get("/config")
async def themis_config():
    """Get Themis connector configuration."""
    return {
        "themis_backend": THEMIS_BACKEND,
        "themis_ws": THEMIS_WS,
        "version": THEMIS_VERSION,
        "proxy_timeout": PROXY_TIMEOUT,
        "supported_apis": [
            "cases", "evidence", "tags", "frameworks", "folders",
            "search", "context", "analysis", "outputs", "settings",
            "caselaw", "mlx", "provenance", "chat", "import", "quarantine", "scl"
        ]
    }


# =============================================================================
# GENERIC PROXY - Route all Themis API calls
# =============================================================================

@router.api_route("/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_to_themis(path: str, request: Request):
    """
    Generic proxy to Themis backend.
    Routes: /connector/themis/proxy/api/... -> localhost:8765/api/...
    """
    # Build target URL
    target_url = f"{THEMIS_BACKEND}/{path}"
    
    # Get query params
    if request.query_params:
        target_url += f"?{request.query_params}"
    
    # Get body if present
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.body()
    
    # Forward headers (except host)
    headers = dict(request.headers)
    headers.pop("host", None)
    
    try:
        async with httpx.AsyncClient(timeout=PROXY_TIMEOUT) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                content=body,
                headers=headers
            )
            
            # Return response with same status and headers
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type")
            )
    
    except httpx.TimeoutException:
        return {"error": "Themis backend timeout", "path": path}
    except httpx.ConnectError:
        return {"error": "Themis backend not available", "path": path}
    except Exception as e:
        return {"error": str(e), "path": path}


# =============================================================================
# SPECIFIC PROXIES WITH LOCALAGENT ENHANCEMENT
# =============================================================================

@router.post("/proxy/api/chat")
async def proxy_chat_with_linting(request: Request):
    """
    Proxy chat to Themis WITH LocalAgent PromptLinter.
    1. Lint the message
    2. Optionally optimize
    3. Forward to Themis
    4. Return combined result
    """
    data = await request.json()
    original_message = data.get("message", "")
    case_id = data.get("case_id", "")
    context = data.get("context", {})
    
    # 1. Lint via LocalAgent
    lint_result = None
    optimized_message = original_message
    
    try:
        # Internal lint call
        from ..core.orchestrator import lint_prompt
        lint_result = lint_prompt(original_message)
        if lint_result and lint_result.get("optimized"):
            optimized_message = lint_result["optimized"]
    except:
        pass
    
    # 2. Forward to Themis
    themis_response = None
    try:
        async with httpx.AsyncClient(timeout=PROXY_TIMEOUT) as client:
            r = await client.post(
                f"{THEMIS_BACKEND}/api/chat",
                json={"message": optimized_message, "case_id": case_id, "context": context}
            )
            if r.status_code == 200:
                themis_response = r.json()
    except Exception as e:
        themis_response = {"error": str(e)}
    
    return {
        "original_message": original_message,
        "optimized_message": optimized_message if optimized_message != original_message else None,
        "lint_result": lint_result,
        "response": themis_response
    }


@router.get("/proxy/api/mlx-feeder/stats")
async def proxy_mlx_stats():
    """Proxy MLX stats with LocalAgent tracking."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{THEMIS_BACKEND}/api/mlx-feeder/stats")
            if r.status_code == 200:
                stats = r.json()
                # Add LocalAgent tracking info
                stats["localagent_tracking"] = True
                return stats
    except:
        pass
    
    return {
        "error": "MLX unavailable",
        "localagent_tracking": True,
        "fallback": {
            "documents_classified": 0,
            "accuracy": 0,
            "last_training": None
        }
    }


@router.get("/proxy/api/search/evidence")
async def proxy_spotlight_search(q: str, case_id: str):
    """
    Proxy Spotlight search with LocalAgent logging.
    Themis uses macOS Spotlight (mdfind) for search.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{THEMIS_BACKEND}/api/search/evidence",
                params={"q": q, "case_id": case_id}
            )
            if r.status_code == 200:
                results = r.json()
                # Log search to LocalAgent
                # await log_search(q, len(results.get("results", [])))
                return results
    except:
        pass
    
    return {"results": [], "error": "Search unavailable", "query": q}


@router.get("/proxy/api/tags/{evidence_id}")
async def proxy_get_tags(evidence_id: str):
    """
    Proxy macOS native tags.
    Themis uses xattr for native macOS Finder tags.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{THEMIS_BACKEND}/api/tags/{evidence_id}")
            if r.status_code == 200:
                return r.json()
    except:
        pass
    
    return {"tags": [], "error": "Tags unavailable", "evidence_id": evidence_id}


@router.post("/proxy/api/tags/{evidence_id}")
async def proxy_add_tag(evidence_id: str, namespace: str, value: str):
    """Add a macOS native tag."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(
                f"{THEMIS_BACKEND}/api/tags/{evidence_id}",
                params={"namespace": namespace, "value": value}
            )
            if r.status_code == 200:
                return r.json()
    except:
        pass
    
    return {"error": "Failed to add tag"}


@router.get("/proxy/api/folders")
async def proxy_smartfolders(case_id: str):
    """
    Proxy SmartFolders.
    Themis uses macOS SmartFolders (saved searches).
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{THEMIS_BACKEND}/api/folders", params={"case_id": case_id})
            if r.status_code == 200:
                return r.json()
    except:
        pass
    
    return {"folders": [], "error": "SmartFolders unavailable"}


# =============================================================================
# WEBSOCKET BRIDGE
# =============================================================================

@router.websocket("/ws")
async def themis_websocket(websocket: WebSocket):
    """WebSocket bridge to Themis."""
    await websocket.accept()
    _themis_clients.add(websocket)
    
    # TODO: Connect to Themis WS and bridge messages
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg.get("type") == "subscribe":
                await websocket.send_json({"type": "subscribed", "channels": msg.get("channels", [])})
    
    except WebSocketDisconnect:
        _themis_clients.discard(websocket)
    except Exception:
        _themis_clients.discard(websocket)


# =============================================================================
# REGISTRATION
# =============================================================================

@router.post("/register")
async def register_themis(request: Request):
    """Register Themis with LocalAgent."""
    from datetime import datetime
    
    data = await request.json()
    
    return {
        "status": "registered",
        "app_id": "themis-qs",
        "name": data.get("name", "THEMIS-QS"),
        "version": data.get("version", THEMIS_VERSION),
        "port": data.get("port", 8765),
        "registered_at": datetime.now().isoformat(),
        "connector": "/connector/themis"
    }
