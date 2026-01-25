"""
LocalAgent v3.0.31 - CONNECTORS Module
LLM + GitHub + Dashboard
"""

from .llm import (
    CLAUDE_CONFIG,
    get_api_key,
    set_api_key,
    has_api_key,
    call_claude,
    call_claude_simple
)

from .github import (
    github_clone,
    github_sync,
    github_list,
    github_remove,
    github_push,
    github_push_all,
    github_create_release,
    github_delete_release,
    github_list_releases,
    get_repos,
    get_version_history,
    get_branches,
    get_current_branch_info,
    update_version_history,
    sync_app_version,
    get_app_info,
    get_service_version,
    get_dashboard_version,
    REPOS
)

from .dashboard import (
    DASHBOARD_PORT,
    set_project,
    get_project,
    start_server,
    generate_dashboard
)

__all__ = [
    # LLM
    "CLAUDE_CONFIG", "get_api_key", "set_api_key", "has_api_key", "call_claude", "call_claude_simple",
    # GitHub
    "github_clone", "github_sync", "github_list", "github_remove", "get_repos",
    "github_push", "github_push_all", "github_create_release", "github_delete_release", "github_list_releases",
    "get_version_history", "get_branches", "get_current_branch_info", "update_version_history",
    "get_service_version", "get_dashboard_version", "REPOS",
    # Dashboard
    "DASHBOARD_PORT", "set_project", "get_project", "start_server", "generate_dashboard"
]
