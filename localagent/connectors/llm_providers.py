"""
LocalAgent - CONNECTOR: LLM Provider Abstraction
Multi-provider LLM support with skill injection

Supported Providers:
- mlx: Apple Silicon local inference
- claude: Anthropic Claude API
- openai: OpenAI API
- ollama: Ollama local server
- custom: User-defined endpoint

Architecture:
    User Request + Active Skill
           ↓
    LLMProvider.complete()
           ↓
    Inject skill context
           ↓
    Send to selected provider
           ↓
    Return response
"""

import os
import json
import logging
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

SERVICE_DIR = Path.home() / ".localagent"
CONFIG_DIR = SERVICE_DIR / "config"


# ============================================================
# PROVIDER CONFIGURATION
# ============================================================

@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""
    name: str
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    model: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    enabled: bool = True
    priority: int = 0  # Lower = higher priority for fallback
    extra: Dict[str, Any] = field(default_factory=dict)


# Default provider configurations
DEFAULT_PROVIDERS = {
    "mlx": ProviderConfig(
        name="mlx",
        model="mlx-community/Llama-3.2-1B-Instruct-4bit",
        priority=0,  # Highest priority (local)
    ),
    "claude": ProviderConfig(
        name="claude",
        api_url="https://api.anthropic.com/v1/messages",
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        priority=1,
    ),
    "openai": ProviderConfig(
        name="openai",
        api_url="https://api.openai.com/v1/chat/completions",
        model="gpt-4o",
        max_tokens=4096,
        priority=2,
    ),
    "ollama": ProviderConfig(
        name="ollama",
        api_url="http://localhost:11434/api/generate",
        model="llama3.2",
        priority=1,
    ),
}


# ============================================================
# ABSTRACT PROVIDER
# ============================================================

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.name = config.name
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available."""
        pass
    
    @abstractmethod
    def complete(self, prompt: str, system: str = "", context: str = "") -> Dict[str, Any]:
        """
        Send completion request.
        
        Returns:
            {"success": bool, "response": str, "usage": dict, "error": str}
        """
        pass
    
    def complete_with_skill(self, prompt: str, skill_context: str = "", system: str = "") -> Dict[str, Any]:
        """Complete with skill context injected."""
        full_system = system
        if skill_context:
            full_system = f"{system}\n\n{skill_context}" if system else skill_context
        return self.complete(prompt, system=full_system)


# ============================================================
# MLX PROVIDER (Apple Silicon)
# ============================================================

class MLXProvider(BaseLLMProvider):
    """MLX local inference on Apple Silicon."""
    
    def __init__(self, config: ProviderConfig = None):
        super().__init__(config or DEFAULT_PROVIDERS["mlx"])
        self._model = None
        self._available = False
        self._check_availability()
    
    def _check_availability(self):
        """Check MLX availability."""
        try:
            import platform
            if platform.system() == "Darwin" and platform.machine() == "arm64":
                import mlx.core as mx
                self._available = True
                logger.info("[MLX] Available on Apple Silicon")
        except ImportError:
            self._available = False
    
    def is_available(self) -> bool:
        return self._available
    
    def _load_model(self):
        """Lazy load model."""
        if self._model is None and self._available:
            try:
                from mlx_lm import load
                self._model = load(self.config.model)
                logger.info(f"[MLX] Loaded: {self.config.model}")
            except Exception as e:
                logger.error(f"[MLX] Load failed: {e}")
                self._model = None
        return self._model
    
    def complete(self, prompt: str, system: str = "", context: str = "") -> Dict[str, Any]:
        if not self._available:
            return {"success": False, "error": "MLX not available"}
        
        model = self._load_model()
        if not model:
            return {"success": False, "error": "MLX model not loaded"}
        
        try:
            from mlx_lm import generate
            
            full_prompt = ""
            if system:
                full_prompt += f"System: {system}\n\n"
            if context:
                full_prompt += f"Context: {context}\n\n"
            full_prompt += f"User: {prompt}\n\nAssistant:"
            
            model_obj, tokenizer = model
            response = generate(
                model_obj, tokenizer,
                prompt=full_prompt,
                max_tokens=self.config.max_tokens
            )
            
            return {
                "success": True,
                "response": response.strip(),
                "usage": {"provider": "mlx"},
                "provider": "mlx"
            }
        except Exception as e:
            logger.error(f"[MLX] Generate error: {e}")
            return {"success": False, "error": str(e)}


# ============================================================
# CLAUDE PROVIDER
# ============================================================

class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude API provider."""
    
    def __init__(self, config: ProviderConfig = None):
        super().__init__(config or DEFAULT_PROVIDERS["claude"])
        self._api_key = None
    
    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment or file."""
        if self._api_key:
            return self._api_key
        
        if os.environ.get("ANTHROPIC_API_KEY"):
            self._api_key = os.environ["ANTHROPIC_API_KEY"]
            return self._api_key
        
        for p in [CONFIG_DIR / "api_key", SERVICE_DIR / "api_key"]:
            if p.exists():
                self._api_key = p.read_text().strip()
                return self._api_key
        return None
    
    def is_available(self) -> bool:
        return self._get_api_key() is not None
    
    def complete(self, prompt: str, system: str = "", context: str = "") -> Dict[str, Any]:
        api_key = self._get_api_key()
        if not api_key:
            return {"success": False, "error": "No Claude API key"}
        
        full_system = system or "You are a helpful assistant."
        if context:
            full_system += f"\n\nContext:\n{context}"
        
        body = json.dumps({
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "system": full_system,
            "messages": [{"role": "user", "content": prompt}]
        }).encode()
        
        try:
            req = urllib.request.Request(
                self.config.api_url,
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
            
            return {
                "success": True,
                "response": text,
                "usage": data.get("usage", {}),
                "provider": "claude"
            }
        except urllib.error.HTTPError as e:
            return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ============================================================
# OPENAI PROVIDER
# ============================================================

class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider."""
    
    def __init__(self, config: ProviderConfig = None):
        super().__init__(config or DEFAULT_PROVIDERS["openai"])
        self._api_key = None
    
    def _get_api_key(self) -> Optional[str]:
        if self._api_key:
            return self._api_key
        
        if os.environ.get("OPENAI_API_KEY"):
            self._api_key = os.environ["OPENAI_API_KEY"]
            return self._api_key
        
        key_file = CONFIG_DIR / "openai_key"
        if key_file.exists():
            self._api_key = key_file.read_text().strip()
            return self._api_key
        return None
    
    def is_available(self) -> bool:
        return self._get_api_key() is not None
    
    def complete(self, prompt: str, system: str = "", context: str = "") -> Dict[str, Any]:
        api_key = self._get_api_key()
        if not api_key:
            return {"success": False, "error": "No OpenAI API key"}
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if context:
            messages.append({"role": "system", "content": f"Context:\n{context}"})
        messages.append({"role": "user", "content": prompt})
        
        body = json.dumps({
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": messages
        }).encode()
        
        try:
            req = urllib.request.Request(
                self.config.api_url,
                data=body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
            )
            resp = urllib.request.urlopen(req, timeout=180)
            data = json.loads(resp.read())
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            
            return {
                "success": True,
                "response": text,
                "usage": data.get("usage", {}),
                "provider": "openai"
            }
        except urllib.error.HTTPError as e:
            return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ============================================================
# OLLAMA PROVIDER (Local)
# ============================================================

class OllamaProvider(BaseLLMProvider):
    """Ollama local server provider."""
    
    def __init__(self, config: ProviderConfig = None):
        super().__init__(config or DEFAULT_PROVIDERS["ollama"])
    
    def is_available(self) -> bool:
        """Check if Ollama server is running."""
        try:
            req = urllib.request.Request(
                "http://localhost:11434/api/tags",
                method="GET"
            )
            resp = urllib.request.urlopen(req, timeout=2)
            return resp.status == 200
        except:
            return False
    
    def complete(self, prompt: str, system: str = "", context: str = "") -> Dict[str, Any]:
        full_prompt = ""
        if system:
            full_prompt += f"{system}\n\n"
        if context:
            full_prompt += f"{context}\n\n"
        full_prompt += prompt
        
        body = json.dumps({
            "model": self.config.model,
            "prompt": full_prompt,
            "stream": False
        }).encode()
        
        try:
            req = urllib.request.Request(
                self.config.api_url,
                data=body,
                headers={"Content-Type": "application/json"}
            )
            resp = urllib.request.urlopen(req, timeout=180)
            data = json.loads(resp.read())
            
            return {
                "success": True,
                "response": data.get("response", "").strip(),
                "usage": {"provider": "ollama"},
                "provider": "ollama"
            }
        except urllib.error.URLError as e:
            return {"success": False, "error": f"Ollama not available: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ============================================================
# LLM MANAGER (Main Interface)
# ============================================================

class LLMManager:
    """
    Manages LLM providers with automatic fallback and skill injection.
    
    Usage:
        manager = LLMManager()
        manager.set_provider("claude")  # or "mlx", "openai", "ollama"
        result = manager.complete("Hello", skill_name="construction-forensics")
    """
    
    PROVIDER_CLASSES = {
        "mlx": MLXProvider,
        "claude": ClaudeProvider,
        "openai": OpenAIProvider,
        "ollama": OllamaProvider,
    }
    
    def __init__(self):
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._active_provider: Optional[str] = None
        self._fallback_chain: List[str] = ["mlx", "ollama", "claude", "openai"]
        self._init_providers()
    
    def _init_providers(self):
        """Initialize all available providers."""
        for name, cls in self.PROVIDER_CLASSES.items():
            try:
                provider = cls()
                self._providers[name] = provider
                logger.info(f"[LLM] Provider '{name}' initialized (available: {provider.is_available()})")
            except Exception as e:
                logger.error(f"[LLM] Failed to init provider '{name}': {e}")
    
    def get_available_providers(self) -> List[str]:
        """List available providers."""
        return [name for name, p in self._providers.items() if p.is_available()]
    
    def get_all_providers(self) -> Dict[str, bool]:
        """Get all providers with availability status."""
        return {name: p.is_available() for name, p in self._providers.items()}
    
    def set_provider(self, name: str) -> bool:
        """Set the active provider."""
        if name not in self._providers:
            logger.error(f"[LLM] Unknown provider: {name}")
            return False
        
        if not self._providers[name].is_available():
            logger.warning(f"[LLM] Provider '{name}' not available")
            return False
        
        self._active_provider = name
        logger.info(f"[LLM] Active provider set to: {name}")
        return True
    
    def get_active_provider(self) -> Optional[str]:
        """Get current active provider name."""
        return self._active_provider
    
    def _get_skill_context(self, skill_name: str = None) -> str:
        """Get skill context for injection."""
        if not skill_name:
            # Get from active skills
            try:
                from ..skills import build_skill_context
                return build_skill_context()
            except:
                return ""
        
        # Load specific skill
        try:
            from ..skills import get_manager
            manager = get_manager()
            skill = manager.get_skill(skill_name)
            if skill:
                return f"=== SKILL: {skill.name} ===\n{skill.description}\n\n{skill.body}"
        except:
            pass
        return ""
    
    def complete(
        self,
        prompt: str,
        system: str = "",
        context: str = "",
        skill_name: str = None,
        provider: str = None,
        fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Send completion request with skill injection.
        
        Args:
            prompt: User prompt
            system: System prompt
            context: Additional context
            skill_name: Skill to inject (or use active skills)
            provider: Specific provider to use (or use active/fallback)
            fallback: Enable fallback to other providers on failure
        
        Returns:
            {"success": bool, "response": str, "provider": str, "usage": dict}
        """
        # Get skill context
        skill_context = self._get_skill_context(skill_name)
        
        # Build full system prompt
        full_system = system
        if skill_context:
            full_system = f"{system}\n\n{skill_context}" if system else skill_context
        
        # Determine provider(s) to try
        providers_to_try = []
        
        if provider:
            providers_to_try = [provider]
        elif self._active_provider:
            providers_to_try = [self._active_provider]
            if fallback:
                providers_to_try += [p for p in self._fallback_chain if p != self._active_provider]
        else:
            providers_to_try = self._fallback_chain
        
        # Try providers in order
        last_error = None
        for pname in providers_to_try:
            if pname not in self._providers:
                continue
            
            p = self._providers[pname]
            if not p.is_available():
                continue
            
            logger.info(f"[LLM] Trying provider: {pname}")
            result = p.complete(prompt, system=full_system, context=context)
            
            if result.get("success"):
                result["provider"] = pname
                result["skill_injected"] = bool(skill_context)
                return result
            
            last_error = result.get("error", "Unknown error")
            logger.warning(f"[LLM] Provider '{pname}' failed: {last_error}")
            
            if not fallback:
                break
        
        return {
            "success": False,
            "error": last_error or "No available providers",
            "providers_tried": providers_to_try
        }


# ============================================================
# GLOBAL INSTANCE
# ============================================================

_manager: Optional[LLMManager] = None


def get_llm_manager() -> LLMManager:
    """Get global LLM manager instance."""
    global _manager
    if _manager is None:
        _manager = LLMManager()
    return _manager


# Convenience functions
def complete(prompt: str, **kwargs) -> Dict[str, Any]:
    """Quick completion with default settings."""
    return get_llm_manager().complete(prompt, **kwargs)


def set_provider(name: str) -> bool:
    """Set active LLM provider."""
    return get_llm_manager().set_provider(name)


def get_available_providers() -> List[str]:
    """List available providers."""
    return get_llm_manager().get_available_providers()
