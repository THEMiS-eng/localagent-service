"""
LocalAgent Routers
"""
from .todo import router as todo_router
from .bugfix import router as bugfix_router
from .releases import router as releases_router
from .github import router as github_router
from .config import router as config_router
from .debug import router as debug_router
from .learning import router as learning_router
from .snapshots import router as snapshots_router
from .protocol import router as protocol_router
from .modules import router as modules_router
from .lint import router as lint_router
from .themis import router as themis_router
from .skills import router as skills_router
from .llm import router as llm_router

__all__ = [
    "todo_router", "bugfix_router", "releases_router", "github_router",
    "config_router", "debug_router", "learning_router", "snapshots_router",
    "protocol_router", "modules_router", "lint_router", "themis_router",
    "skills_router", "llm_router"
]
