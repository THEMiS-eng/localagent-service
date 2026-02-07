"""
LocalAgent v3.0 - CONNECTOR: LLM
Claude API communication - Standalone (no circular imports)
"""

import os
import json
import urllib.request
import urllib.error
from pathlib import Path

SERVICE_DIR = Path.home() / ".localagent"
CONFIG_DIR = SERVICE_DIR / "config"

CLAUDE_CONFIG = {
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 4096
}

# Persistent HTTP session for connection reuse (avoids TLS handshake per request)
_http_session = None

def _get_session():
    global _http_session
    if _http_session is None:
        try:
            import requests
            _http_session = requests.Session()
            _http_session.headers.update({
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            })
        except ImportError:
            _http_session = False  # requests not available, use urllib
    return _http_session

def get_api_key():
    """Get Claude API key."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]
    for p in [CONFIG_DIR / "api_key", SERVICE_DIR / "api_key", Path.home() / ".localagent-dev" / "api_key"]:
        if p.exists():
            return p.read_text().strip()
    return None

def set_api_key(key: str):
    """Save Claude API key."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (CONFIG_DIR / "api_key").write_text(key.strip())

def has_api_key() -> bool:
    """Check if API key is configured."""
    return get_api_key() is not None

def call_claude(prompt: str, context: str = "", system: str = None, images: list = None):
    """Call Claude API with optional multimodal support.

    Args:
        prompt: Text prompt
        context: Additional context
        system: System prompt
        images: List of image dicts with {data: base64, type: mime_type}
    """
    api_key = get_api_key()
    if not api_key:
        return {"success": False, "error": "No API key configured"}

    sys_prompt = system or "You are a helpful assistant."
    if context:
        sys_prompt += f"\n\nCONTEXT:\n{context}"

    # Build message content (multimodal if images provided)
    if images and len(images) > 0:
        content = []
        # Add images first
        for img in images:
            if img.get("data"):
                # Extract base64 data (remove data:image/xxx;base64, prefix if present)
                img_data = img["data"]
                if "," in img_data:
                    img_data = img_data.split(",", 1)[1]
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img.get("type", "image/png"),
                        "data": img_data
                    }
                })
        # Add text prompt
        content.append({"type": "text", "text": prompt})
    else:
        content = prompt

    payload = {
        "model": CLAUDE_CONFIG["model"],
        "max_tokens": CLAUDE_CONFIG["max_tokens"],
        "system": sys_prompt,
        "messages": [{"role": "user", "content": content}]
    }

    session = _get_session()

    try:
        if session and session is not False:
            # Use requests with connection pooling (fast: reuses TCP+TLS)
            session.headers["x-api-key"] = api_key
            resp = session.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                timeout=180
            )
            resp.raise_for_status()
            data = resp.json()
        else:
            # Fallback to urllib
            body = json.dumps(payload).encode()
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=body,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
            )
            resp = urllib.request.urlopen(req, timeout=180)
            data = json.loads(resp.read())

        text = data.get("content", [{}])[0].get("text", "").strip()
        return {"success": True, "response": text, "usage": data.get("usage", {})}
    except Exception as e:
        error_detail = ""
        if hasattr(e, 'response') and e.response is not None:
            error_detail = e.response.text[:500]
        return {"success": False, "error": str(e), "detail": error_detail}

def call_claude_simple(message: str) -> str:
    """Simple call returning just response text or error message."""
    result = call_claude(message)
    return result.get("response", result.get("error", "Error"))
