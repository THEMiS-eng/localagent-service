#!/usr/bin/env python3
"""
Validation and recovery utilities for LocalAgent
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from .error_handler import ErrorHandler

class ValidationError(Exception):
    """Custom validation error"""
    pass

class Validator:
    """Input validation and sanitization"""
    
    def __init__(self):
        self.error_handler = ErrorHandler()
        
    def validate_file_path(self, path: str) -> bool:
        """Validate file path safety"""
        try:
            path_obj = Path(path).resolve()
            
            # Check for path traversal
            if ".." in str(path_obj):
                raise ValidationError(f"Path traversal detected: {path}")
                
            # Check if parent directory exists
            if not path_obj.parent.exists():
                raise ValidationError(f"Parent directory does not exist: {path_obj.parent}")
                
            return True
            
        except Exception as e:
            self.error_handler.handle_error(e, "validate_file_path")
            return False
            
    def validate_json(self, data: str) -> Optional[Dict[str, Any]]:
        """Validate and parse JSON safely"""
        try:
            if not isinstance(data, str):
                raise ValidationError("JSON data must be string")
                
            parsed = json.loads(data)
            return parsed
            
        except json.JSONDecodeError as e:
            self.error_handler.handle_error(e, "validate_json")
            return None
        except Exception as e:
            self.error_handler.handle_error(e, "validate_json")
            return None
            
    def validate_command(self, command: List[str]) -> bool:
        """Validate command for safe execution"""
        try:
            if not isinstance(command, list):
                raise ValidationError("Command must be list")
                
            if not command:
                raise ValidationError("Command cannot be empty")
                
            # Check for dangerous commands
            dangerous = ['rm', 'del', 'format', 'dd', 'mkfs']
            if any(danger in ' '.join(command).lower() for danger in dangerous):
                raise ValidationError(f"Dangerous command detected: {command}")
                
            return True
            
        except Exception as e:
            self.error_handler.handle_error(e, "validate_command")
            return False