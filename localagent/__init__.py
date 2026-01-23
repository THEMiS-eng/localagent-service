"""
LocalAgent DEV-TEST v2.10.36
Smart Agent Orchestrator
"""

from pathlib import Path as _Path
_version_file = _Path(__file__).parent.parent / "VERSION"
__version__ = _version_file.read_text().strip() if _version_file.exists() else "0.0.0"
__author__ = "THEMiS-eng"

from .main import main

__all__ = ["main", "__version__"]
