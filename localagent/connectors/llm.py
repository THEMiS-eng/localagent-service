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

def call_claude(prompt: str, context: str = "", system: str = None):
    """Call Claude API."""
    api_key = get_api_key()
    if not api_key:
        return {"success": False, "error": "No API key configured"}
    
    sys_prompt = system or "You are a helpful assistant."
    if context:
        sys_prompt += f"\n\nCONTEXT:\n{context}"
    
    body = json.dumps({
        "model": CLAUDE_CONFIG["model"],
        "max_tokens": CLAUDE_CONFIG["max_tokens"],
        "system": sys_prompt,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()
    
    try:
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
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def call_claude_simple(message: str) -> str:
    """Simple call returning just response text or error message."""
    result = call_claude(message)
    return result.get("response", result.get("error", "Error"))
