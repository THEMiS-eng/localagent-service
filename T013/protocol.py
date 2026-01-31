import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from .github_utils import create_github_release
from .file_manager import FileManager
from .code_generator import CodeGenerator
from .version_manager import VersionManager
from .websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)

class ProtocolHandler:
    def __init__(self, file_manager: FileManager, code_generator: CodeGenerator, 
                 version_manager: VersionManager, websocket_manager: WebSocketManager):
        self.file_manager = file_manager
        self.code_generator = code_generator
        self.version_manager = version_manager
        self.websocket_manager = websocket_manager
        
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming protocol requests"""
        try:
            command = request.get('command')
            
            if command == 'create_release':
                return await self._handle_create_release(request)
            elif command == 'generate_code':
                return await self._handle_generate_code(request)
            elif command == 'get_version':
                return await self._handle_get_version(request)
            else:
                return {'error': f'Unknown command: {command}'}
                
        except Exception as e:
            logger.error(f"Protocol error: {e}")
            return {'error': str(e)}
    
    async def _handle_create_release(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle GitHub release creation"""
        try:
            version = request.get('version')
            notes = request.get('notes', '')
            
            result = await create_github_release(version, notes)
            return {'success': True, 'release_url': result.get('html_url')}
            
        except Exception as e:
            return {'error': f'Release creation failed: {str(e)}'}
    
    async def _handle_generate_code(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code generation requests"""
        prompt = request.get('prompt')
        result = await self.code_generator.generate(prompt)
        return result
    
    async def _handle_get_version(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle version info requests"""
        version_info = self.version_manager.get_current_version()
        return {'version': version_info}