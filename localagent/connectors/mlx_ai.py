"""
MLX AI Connector - Local LLM with Claude fallback

Features:
- MLX for Apple Silicon (if available)
- Fallback to Claude API
- Document classification
- Chat completion
"""

import os
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

# Document types for classification
DOCUMENT_TYPES = [
    "EXPERT_REPORT",
    "CONTRACT", 
    "PROGRAMME",
    "CORRESPONDENCE",
    "INVOICE",
    "DRAWING",
    "SPECIFICATION",
    "MEETING_MINUTES",
    "SITE_DIARY",
    "PHOTOGRAPH",
    "OTHER"
]

# MLX availability check
_mlx_available = False
_mlx_model = None

def check_mlx_available() -> bool:
    """Check if MLX is available (Apple Silicon)."""
    global _mlx_available
    try:
        import platform
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            import mlx.core as mx
            _mlx_available = True
            logger.info("[MLX] MLX available on Apple Silicon")
            return True
    except ImportError:
        pass
    _mlx_available = False
    logger.info("[MLX] MLX not available, will use Claude fallback")
    return False


def load_mlx_model(model_name: str = "mlx-community/Llama-3.2-1B-Instruct-4bit"):
    """Load MLX model for local inference."""
    global _mlx_model
    if not _mlx_available:
        return None
    try:
        from mlx_lm import load, generate
        _mlx_model = load(model_name)
        logger.info(f"[MLX] Loaded model: {model_name}")
        return _mlx_model
    except Exception as e:
        logger.error(f"[MLX] Failed to load model: {e}")
        return None


def classify_document_mlx(text: str, filename: str = "") -> Dict[str, Any]:
    """Classify document using MLX."""
    if not _mlx_available or not _mlx_model:
        return None
    
    try:
        from mlx_lm import generate
        
        prompt = f"""Classify this document into one of these categories:
{', '.join(DOCUMENT_TYPES)}

Document filename: {filename}
Document text (first 1000 chars): {text[:1000]}

Respond with ONLY the category name, nothing else."""

        model, tokenizer = _mlx_model
        response = generate(model, tokenizer, prompt=prompt, max_tokens=20)
        
        # Parse response
        classification = response.strip().upper()
        if classification in DOCUMENT_TYPES:
            return {
                "classification": classification,
                "confidence": 0.85,
                "source": "mlx"
            }
    except Exception as e:
        logger.error(f"[MLX] Classification error: {e}")
    return None


def classify_document_claude(text: str, filename: str = "") -> Dict[str, Any]:
    """Classify document using Claude API (fallback)."""
    try:
        from .llm import call_claude
        
        prompt = f"""Classify this document into one of these categories:
{', '.join(DOCUMENT_TYPES)}

Document filename: {filename}
Document text (first 2000 chars): {text[:2000]}

Respond with ONLY the category name, nothing else."""

        response = call_claude(prompt, system="You are a document classifier. Respond with only the category name.")
        
        classification = response.strip().upper()
        if classification in DOCUMENT_TYPES:
            return {
                "classification": classification,
                "confidence": 0.92,
                "source": "claude"
            }
        # Try to extract from response
        for doc_type in DOCUMENT_TYPES:
            if doc_type in classification:
                return {
                    "classification": doc_type,
                    "confidence": 0.85,
                    "source": "claude"
                }
    except Exception as e:
        logger.error(f"[CLAUDE] Classification error: {e}")
    
    return {
        "classification": "OTHER",
        "confidence": 0.5,
        "source": "fallback"
    }


def classify_document(text: str, filename: str = "") -> Dict[str, Any]:
    """Classify document - MLX first, then Claude fallback."""
    # Try MLX first
    if _mlx_available:
        result = classify_document_mlx(text, filename)
        if result:
            return result
    
    # Fallback to Claude
    return classify_document_claude(text, filename)


def chat_completion_mlx(message: str, context: str = "") -> Optional[str]:
    """Chat completion using MLX."""
    if not _mlx_available or not _mlx_model:
        return None
    
    try:
        from mlx_lm import generate
        
        prompt = f"{context}\n\nUser: {message}\n\nAssistant:"
        model, tokenizer = _mlx_model
        response = generate(model, tokenizer, prompt=prompt, max_tokens=500)
        return response.strip()
    except Exception as e:
        logger.error(f"[MLX] Chat error: {e}")
    return None


def chat_completion_claude(message: str, context: str = "", system: str = "") -> str:
    """Chat completion using Claude API (fallback)."""
    try:
        from .llm import call_claude
        
        full_message = f"{context}\n\n{message}" if context else message
        response = call_claude(full_message, system=system or "You are a helpful legal/construction claims assistant.")
        return response
    except Exception as e:
        logger.error(f"[CLAUDE] Chat error: {e}")
        return f"I understand your question. Let me help you with that. (Error: {e})"


def chat_completion(message: str, context: str = "", system: str = "") -> Dict[str, Any]:
    """Chat completion - MLX first, then Claude fallback."""
    # Try MLX first
    if _mlx_available:
        result = chat_completion_mlx(message, context)
        if result:
            return {"response": result, "source": "mlx"}
    
    # Fallback to Claude
    response = chat_completion_claude(message, context, system)
    return {"response": response, "source": "claude"}


def get_mlx_stats() -> Dict[str, Any]:
    """Get MLX status and stats."""
    return {
        "mlx_available": _mlx_available,
        "model_loaded": _mlx_model is not None,
        "fallback": "claude",
        "document_types": DOCUMENT_TYPES
    }


# Initialize on import
check_mlx_available()
