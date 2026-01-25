#!/usr/bin/env python3
"""
Initialize tracking data from real development history.
Run this once after fresh install to populate TODO, BUGFIX, CHANGELOG.
"""

import json
from pathlib import Path
from datetime import datetime

PROJECTS_DIR = Path.home() / "Desktop" / "localagent-projects" / "LOCALAGENT"
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# HISTORICAL DATA - Real changes from v3.0 to v3.3.3
# ============================================================

TODOS = [
    # v3.1.x
    {"id": "TD001", "title": "Add file drop in chat input", "done": True, "version": "3.1.0", "category": "todo"},
    {"id": "TD002", "title": "Dynamic resizable chat input", "done": True, "version": "3.1.1", "category": "todo"},
    {"id": "TD003", "title": "Sidebar panel accordeon (collapsible)", "done": True, "version": "3.1.8", "category": "todo"},
    {"id": "TD004", "title": "Sidebar toggle button (Ctrl+B)", "done": True, "version": "3.1.9", "category": "todo"},
    {"id": "TD005", "title": "Release notes generation from git", "done": True, "version": "3.1.7", "category": "todo"},
    
    # v3.2.x
    {"id": "TD006", "title": "GitHub Actions CI/CD workflows", "done": True, "version": "3.2.0", "category": "todo"},
    {"id": "TD007", "title": "TODO click toggle (mark done/restore)", "done": True, "version": "3.2.2", "category": "todo"},
    {"id": "TD008", "title": "GitHub workflow integration - auto-complete TODOs", "done": True, "version": "3.2.3", "category": "todo"},
    {"id": "TD009", "title": "Changelog sync from GitHub releases", "done": True, "version": "3.2.4", "category": "todo"},
    {"id": "TD010", "title": "TODO status 'testing' (pending GitHub tests)", "done": True, "version": "3.2.5", "category": "todo"},
    {"id": "TD011", "title": "Release notes version filtering", "done": True, "version": "3.2.6", "category": "todo"},
    
    # v3.3.x
    {"id": "TD012", "title": "Phase 1: TTL Cache system (30s)", "done": True, "version": "3.2.7", "category": "todo"},
    {"id": "TD013", "title": "Phase 2: FastAPI routers (todo, bugfix, github, debug)", "done": True, "version": "3.2.8", "category": "todo"},
    {"id": "TD014", "title": "Release notes from git commits fallback", "done": True, "version": "3.2.9", "category": "todo"},
    {"id": "TD015", "title": "Polling interval optimization (30s)", "done": True, "version": "3.3.1", "category": "todo"},
    {"id": "TD016", "title": "Console error injection to Claude context", "done": True, "version": "3.3.3", "category": "todo"},
    
    # Pending
    {"id": "TD017", "title": "Download artifacts in Chrome extension", "done": False, "category": "todo"},
]

BUGFIXES = [
    {"id": "BF001", "title": "Fix VERSION import in server.py", "description": "Hardcoded 3.0.22 should import from __init__.py", "status": "applied", "version": "3.1.0"},
    {"id": "BF002", "title": "Fix message timestamp display", "description": "Timestamps showing incorrect format", "status": "applied", "version": "3.1.2"},
    {"id": "BF003", "title": "Fix changelog panel empty", "description": "Changelog showing 'No notes available'", "status": "applied", "version": "3.2.1"},
    {"id": "BF004", "title": "Fix release notes empty sections", "description": "Bug fixes section showing empty dashes", "status": "applied", "version": "3.2.6"},
    {"id": "BF005", "title": "Fix duplicate code in tracking.py", "description": "Duplicate generate_release_notes code", "status": "applied", "version": "3.2.9"},
    {"id": "BF006", "title": "Fix test_debug_context assertion", "description": "Test expected 'context' key but got 'pending_errors'", "status": "applied", "version": "3.2.8"},
]

CHANGELOG = [
    {"version": "3.3.3", "date": datetime.now().isoformat(), "notes": "Console error injection to Claude context"},
    {"version": "3.3.2", "date": "2026-01-25T21:00:00", "notes": "DevOps config (VS Code, pre-commit, GitHub Actions)"},
    {"version": "3.3.1", "date": "2026-01-25T20:45:00", "notes": "Polling optimization 30s TTL"},
    {"version": "3.3.0", "date": "2026-01-25T20:35:00", "notes": "Performance analysis"},
    {"version": "3.2.9", "date": "2026-01-25T20:20:00", "notes": "Release notes from git commits"},
    {"version": "3.2.8", "date": "2026-01-25T20:10:00", "notes": "FastAPI routers (Phase 2)"},
    {"version": "3.2.7", "date": "2026-01-25T19:50:00", "notes": "TTL Cache system (Phase 1)"},
    {"version": "3.2.6", "date": "2026-01-25T19:30:00", "notes": "Release notes version filtering"},
    {"version": "3.2.5", "date": "2026-01-25T19:15:00", "notes": "TODO testing status"},
    {"version": "3.2.4", "date": "2026-01-25T19:00:00", "notes": "Changelog sync from GitHub"},
    {"version": "3.2.3", "date": "2026-01-25T18:45:00", "notes": "GitHub workflow TODO integration"},
    {"version": "3.2.2", "date": "2026-01-25T18:30:00", "notes": "TODO click toggle"},
    {"version": "3.2.1", "date": "2026-01-25T18:15:00", "notes": "Release notes fix"},
    {"version": "3.2.0", "date": "2026-01-25T18:00:00", "notes": "GitHub Actions CI/CD"},
    {"version": "3.1.9", "date": "2026-01-25T17:00:00", "notes": "Sidebar toggle"},
    {"version": "3.1.8", "date": "2026-01-25T16:45:00", "notes": "Panel accordeon"},
    {"version": "3.1.7", "date": "2026-01-25T16:30:00", "notes": "Release notes generation"},
]


def init_tracking():
    """Initialize all tracking files."""
    
    # TODOs
    todo_file = PROJECTS_DIR / "TODO.json"
    for t in TODOS:
        if t.get("done"):
            t["completed"] = "2026-01-25T12:00:00"
            t["status"] = "completed"
        else:
            t["status"] = "pending"
    todo_file.write_text(json.dumps(TODOS, indent=2))
    print(f"✓ Created {todo_file} ({len(TODOS)} items)")
    
    # Bugfixes
    bugfix_file = PROJECTS_DIR / "BUGFIX.json"
    for b in BUGFIXES:
        b["applied_at"] = "2026-01-25T12:00:00"
    bugfix_file.write_text(json.dumps(BUGFIXES, indent=2))
    print(f"✓ Created {bugfix_file} ({len(BUGFIXES)} items)")
    
    # Changelog
    changelog_file = PROJECTS_DIR / "CHANGELOG.json"
    changelog_file.write_text(json.dumps(CHANGELOG, indent=2))
    print(f"✓ Created {changelog_file} ({len(CHANGELOG)} versions)")
    
    # Empty backlog
    backlog_file = PROJECTS_DIR / "BACKLOG.json"
    backlog_file.write_text(json.dumps([], indent=2))
    print(f"✓ Created {backlog_file}")
    
    # Create current dir
    (PROJECTS_DIR / "current").mkdir(exist_ok=True)
    
    print(f"\n✅ Tracking initialized at {PROJECTS_DIR}")


if __name__ == "__main__":
    init_tracking()
