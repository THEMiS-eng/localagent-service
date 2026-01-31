#!/usr/bin/env python3
"""
Error handling decorators for LocalAgent functions
"""

import functools
import logging
from typing import Callable, Any, Optional
from .error_handler import ErrorHandler

# Global error handler instance
error_handler = ErrorHandler()

def handle_errors(context: str = "", fatal: bool = False, 
                 max_retries: int = 3, default_return: Any = None):
    """Decorator for comprehensive error handling"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retry_count = 0
            
            while retry_count <= max_retries:
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    error_info = error_handler.handle_error(
                        e, context or func.__name__, fatal, retry_count
                    )
                    
                    if fatal or retry_count >= max_retries:
                        if fatal:
                            raise e
                        return default_return
                        
                    retry_count += 1
                    
            return default_return
        return wrapper
    return decorator

def safe_execute(context: str = ""):
    """Decorator for safe execution with error logging"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler.handle_error(e, context or func.__name__)
                return None
        return wrapper
    return decorator