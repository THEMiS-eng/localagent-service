#!/usr/bin/env python3
"""
Comprehensive error handling utility for LocalAgent
"""

import logging
import traceback
import sys
from typing import Optional, Dict, Any, Callable
from functools import wraps
import json
from pathlib import Path

class ErrorHandler:
    """Centralized error handling with logging and recovery"""
    
    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file or "localagent_errors.log"
        self.setup_logging()
        self.error_counts = {}
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def handle_error(self, error: Exception, context: str = "", 
                    fatal: bool = False, retry_count: int = 0) -> Dict[str, Any]:
        """Handle errors with logging and context"""
        error_info = {
            'type': type(error).__name__,
            'message': str(error),
            'context': context,
            'traceback': traceback.format_exc(),
            'retry_count': retry_count,
            'fatal': fatal
        }
        
        # Count error types
        error_type = type(error).__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Log error
        log_msg = f"Error in {context}: {error_type} - {str(error)}"
        if fatal:
            self.logger.error(f"FATAL: {log_msg}")
        else:
            self.logger.warning(log_msg)
            
        return error_info