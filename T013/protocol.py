import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from pathlib import Path

# Import GitHub utilities
from github_utils import create_github_release

logger = logging.getLogger(__name__)

class ProtocolHandler:
    """Handles protocol-level communication and operations"""
    
    def __init__(self):
        self.active_connections = set()
        self.message_handlers = {
            'ping': self._handle_ping,
            'status': self._handle_status,
            'release': self._handle_release,
            'version': self._handle_version
        }
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming protocol messages"""
        try:
            msg_type = message.get('type')
            handler = self.message_handlers.get(msg_type)
            
            if handler:
                return await handler(message)
            else:
                return {'error': f'Unknown message type: {msg_type}'}
                
        except Exception as e:
            logger.error(f"Protocol error: {e}")
            return {'error': str(e)}
    
    async def _handle_ping(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ping messages"""
        return {'type': 'pong', 'timestamp': datetime.now().isoformat()}
    
    async def _handle_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status requests"""
        return {
            'type': 'status_response',
            'active_connections': len(self.active_connections),
            'timestamp': datetime.now().isoformat()
        }
    
    async def _handle_release(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle GitHub release creation"""
        try:
            version = message.get('version')
            if not version:
                return {'error': 'Version required for release'}
            
            result = await create_github_release(version)
            return {'type': 'release_response', 'result': result}
            
        except Exception as e:
            return {'error': f'Release failed: {str(e)}'}
    
    async def _handle_version(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle version requests"""
        return {
            'type': 'version_response',
            'version': '3.3.007',
            'timestamp': datetime.now().isoformat()
        }