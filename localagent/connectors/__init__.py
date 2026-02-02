"""
LocalAgent Connectors
- github: Git operations & GitHub API
- llm: Claude/Anthropic API
- llm_providers: Multi-provider LLM abstraction
- dashboard: Dashboard UI serving
- themis: THEMIS-QS integration
"""

from .github import (
    github_clone, github_sync, github_list, github_remove,
    github_push, github_list_releases
)
from .llm import (
    has_api_key, set_api_key, get_api_key, call_claude
)
from .llm_providers import (
    LLMManager, get_llm_manager, complete, set_provider,
    get_available_providers
)
from .dashboard import (
    start_server, generate_dashboard
)

__all__ = [
    # GitHub
    "github_clone", "github_sync", "github_list", "github_remove",
    "github_push", "github_list_releases",
    # LLM (legacy)
    "has_api_key", "set_api_key", "get_api_key", "call_claude",
    # LLM Providers (multi-provider)
    "LLMManager", "get_llm_manager", "complete", "set_provider",
    "get_available_providers",
    # Dashboard
    "start_server", "generate_dashboard",
]
