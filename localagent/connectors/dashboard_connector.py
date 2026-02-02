"""
Dashboard Connector for LocalAgent

Ce connecteur gère:
- L'interface UI du dashboard LocalAgent
- WebSocket pour updates real-time
- Routes spécifiques au dashboard
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pathlib import Path
from typing import Dict, List, Set
import json
import asyncio

router = APIRouter(prefix="/connector/dashboard", tags=["dashboard-connector"])

# WebSocket connections
_dashboard_clients: Set[WebSocket] = set()


# =============================================================================
# DASHBOARD UI
# =============================================================================

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the LocalAgent dashboard UI."""
    dashboard_path = Path(__file__).parent.parent.parent / "dashboard" / "index.html"
    if dashboard_path.exists():
        return HTMLResponse(dashboard_path.read_text())
    return HTMLResponse("<h1>Dashboard not found</h1>")


# =============================================================================
# WEBSOCKET FOR REAL-TIME UPDATES
# =============================================================================

@router.websocket("/ws")
async def dashboard_websocket(websocket: WebSocket):
    """WebSocket endpoint for dashboard real-time updates."""
    await websocket.accept()
    _dashboard_clients.add(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            # Handle incoming messages from dashboard
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg.get("type") == "subscribe":
                await websocket.send_json({"type": "subscribed", "channels": msg.get("channels", [])})
    
    except WebSocketDisconnect:
        _dashboard_clients.discard(websocket)
    except Exception:
        _dashboard_clients.discard(websocket)


async def broadcast_to_dashboard(event_type: str, data: Dict):
    """Broadcast an event to all connected dashboards."""
    message = json.dumps({"type": event_type, "data": data})
    disconnected = set()
    
    for client in _dashboard_clients:
        try:
            await client.send_text(message)
        except:
            disconnected.add(client)
    
    _dashboard_clients.difference_update(disconnected)


# =============================================================================
# DASHBOARD-SPECIFIC ROUTES
# =============================================================================

@router.get("/status")
async def dashboard_status():
    """Get dashboard connector status."""
    return {
        "connector": "dashboard",
        "version": "4.1.0",
        "websocket_clients": len(_dashboard_clients),
        "status": "online"
    }


@router.get("/config")
async def dashboard_config():
    """Get dashboard configuration."""
    return {
        "refresh_interval": 10000,
        "websocket_enabled": True,
        "features": ["chat", "todo", "bugfix", "releases", "apps"]
    }
