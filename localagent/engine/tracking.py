"""
LocalAgent v3.0.35 - ENGINE: Tracking
Backlog, TODO, NTH, BUGFIX, changelog, conversation, output files (per project)

RELEASE RULES:
- ADD TODO/NTH → Roadmap only, NO release
- PROCESS TODO/NTH → Version bump, push, release notes
- APPLY BUGFIX → Version bump, push, release notes
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .project import PROJECTS_DIR


# ============================================================
# BACKLOG
# ============================================================

def get_backlog(project: str) -> List[Dict]:
    """Get project backlog."""
    backlog_file = PROJECTS_DIR / project / "BACKLOG.json"
    if backlog_file.exists():
        try:
            return json.loads(backlog_file.read_text())
        except:
            pass
    return []


def save_backlog(project: str, backlog: List[Dict]):
    """Save project backlog."""
    project_dir = PROJECTS_DIR / project
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "BACKLOG.json").write_text(json.dumps(backlog, indent=2))


def add_backlog_item(project: str, title: str, priority: str = "medium", item_type: str = "task", metadata: Dict = None) -> str:
    """Add backlog item. Returns item ID."""
    backlog = get_backlog(project)
    
    # Generate unique ID
    num = 1
    existing = {b.get("id", "") for b in backlog}
    while f"B{num:03d}" in existing:
        num += 1
    item_id = f"B{num:03d}"
    
    item = {
        "id": item_id,
        "title": title,
        "type": item_type,
        "priority": priority,
        "status": "pending",
        "created": datetime.now().isoformat()
    }
    
    if metadata:
        item["metadata"] = metadata
    
    backlog.append(item)
    save_backlog(project, backlog)
    return item_id


def complete_backlog_item(project: str, item_id: str, commit_sha: str = None) -> bool:
    """
    Mark backlog item as complete.
    
    Args:
        project: Project name
        item_id: Backlog item ID
        commit_sha: Git commit SHA (required for proper tracking)
    """
    return update_backlog_item(
        project, 
        item_id, 
        status="done",
        completed=datetime.now().isoformat(),
        commit_sha=commit_sha
    )


def update_backlog_item(project: str, item_id: str, **updates) -> bool:
    """Update backlog item."""
    backlog = get_backlog(project)
    for item in backlog:
        if item["id"] == item_id:
            for key, value in updates.items():
                item[key] = value
            item["updated"] = datetime.now().isoformat()
            save_backlog(project, backlog)
            return True
    return False


def get_pending_backlog(project: str) -> List[Dict]:
    """Get pending backlog items sorted by priority."""
    backlog = get_backlog(project)
    pending = [b for b in backlog if b.get("status") == "pending"]
    
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    pending.sort(key=lambda x: priority_order.get(x.get("priority", "medium"), 2))
    
    return pending


# ============================================================
# TODO (Roadmap - no release on add)
# ============================================================

def get_todo(project: str) -> List[Dict]:
    """Get project TODO list."""
    todo_file = PROJECTS_DIR / project / "TODO.json"
    if todo_file.exists():
        try:
            return json.loads(todo_file.read_text())
        except:
            pass
    return []


def save_todo(project: str, todo: List[Dict]):
    """Save project TODO list."""
    project_dir = PROJECTS_DIR / project
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "TODO.json").write_text(json.dumps(todo, indent=2))


def add_todo_item(project: str, title: str, category: str = "todo") -> str:
    """
    Add TODO item. Categories: todo, nth.
    NOTE: Adding does NOT trigger release - roadmap only.
    """
    todo = get_todo(project)
    
    # Use T prefix for todo, N prefix for nth
    prefix = "N" if category == "nth" else "T"
    num = 1
    existing = {t.get("id", "") for t in todo}
    while f"{prefix}{num:03d}" in existing:
        num += 1
    item_id = f"{prefix}{num:03d}"
    
    todo.append({
        "id": item_id,
        "title": title,
        "category": category,
        "status": "pending",  # pending, processing, done
        "done": False,
        "created": datetime.now().isoformat()
    })
    save_todo(project, todo)
    return item_id


def toggle_todo(project: str, item_id: str) -> bool:
    """Toggle TODO item done status."""
    todo = get_todo(project)
    for item in todo:
        if item["id"] == item_id:
            item["done"] = not item["done"]
            item["updated"] = datetime.now().isoformat()
            save_todo(project, todo)
            return True
    return False


def complete_todo_item(project: str, item_id: str, version: str, commit_sha: str = None, release_url: str = None) -> bool:
    """
    Mark TODO/NTH as processed (triggers release).
    
    Args:
        project: Project name
        item_id: TODO/NTH ID (T001 or N001)
        version: Version this was released in
        commit_sha: Git commit SHA
        release_url: GitHub release URL
    """
    todo = get_todo(project)
    for item in todo:
        if item["id"] == item_id:
            item["done"] = True
            item["status"] = "done"
            item["completed"] = datetime.now().isoformat()
            item["version"] = version
            item["commit_sha"] = commit_sha
            item["release_url"] = release_url
            save_todo(project, todo)
            
            # Add to release log
            add_release_item(project, item_id, item["category"].upper(), item["title"], version, commit_sha)
            return True
    return False


# ============================================================
# BUGFIX (Always triggers release)
# ============================================================

def get_bugfixes(project: str) -> List[Dict]:
    """Get project bugfixes."""
    bugfix_file = PROJECTS_DIR / project / "BUGFIX.json"
    if bugfix_file.exists():
        try:
            return json.loads(bugfix_file.read_text())
        except:
            pass
    return []


def save_bugfixes(project: str, bugfixes: List[Dict]):
    """Save project bugfixes."""
    project_dir = PROJECTS_DIR / project
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "BUGFIX.json").write_text(json.dumps(bugfixes, indent=2))


def add_bugfix(project: str, title: str, description: str = "", source: str = "manual") -> str:
    """
    Add a bugfix entry. Returns bugfix ID.
    NOTE: This just records it - call apply_bugfix after fix is applied.
    
    Args:
        project: Project name
        title: Short description of the bug/fix
        description: Detailed description
        source: Where bug was found (console, test, manual, etc.)
    """
    bugfixes = get_bugfixes(project)
    
    num = 1
    existing = {b.get("id", "") for b in bugfixes}
    while f"BF{num:03d}" in existing:
        num += 1
    item_id = f"BF{num:03d}"
    
    bugfixes.append({
        "id": item_id,
        "title": title,
        "description": description,
        "source": source,
        "status": "pending",  # pending, applied
        "created": datetime.now().isoformat()
    })
    save_bugfixes(project, bugfixes)
    return item_id


def apply_bugfix(project: str, bugfix_id: str, version: str, commit_sha: str, files_changed: List[str] = None, release_url: str = None) -> bool:
    """
    Mark bugfix as applied. This triggers release notes.
    
    Args:
        project: Project name
        bugfix_id: Bugfix ID (BF001)
        version: Version this fix is released in
        commit_sha: Git commit SHA (REQUIRED)
        files_changed: List of files modified
        release_url: GitHub release URL
    """
    if not commit_sha:
        raise ValueError("commit_sha is REQUIRED for bugfix tracking")
    
    bugfixes = get_bugfixes(project)
    for item in bugfixes:
        if item["id"] == bugfix_id:
            item["status"] = "applied"
            item["applied"] = datetime.now().isoformat()
            item["version"] = version
            item["commit_sha"] = commit_sha
            item["files_changed"] = files_changed or []
            item["release_url"] = release_url
            save_bugfixes(project, bugfixes)
            
            # Add to release log
            add_release_item(project, bugfix_id, "BUGFIX", item["title"], version, commit_sha)
            return True
    return False


def get_pending_bugfixes(project: str) -> List[Dict]:
    """Get bugfixes that haven't been applied yet."""
    bugfixes = get_bugfixes(project)
    return [b for b in bugfixes if b.get("status") == "pending"]


# ============================================================
# RELEASE LOG (Tracks all released items)
# ============================================================

def get_release_log(project: str) -> List[Dict]:
    """Get release log - all items that triggered releases."""
    release_file = PROJECTS_DIR / project / "RELEASES.json"
    if release_file.exists():
        try:
            return json.loads(release_file.read_text())
        except:
            pass
    return []


def save_release_log(project: str, releases: List[Dict]):
    """Save release log."""
    (PROJECTS_DIR / project / "RELEASES.json").write_text(json.dumps(releases, indent=2))


def add_release_item(project: str, item_id: str, item_type: str, title: str, version: str, commit_sha: str = None):
    """
    Add item to release log.
    
    Args:
        item_id: ID (T001, N001, BF001)
        item_type: TODO, NTH, or BUGFIX
        title: Description
        version: Release version
        commit_sha: Git commit
    """
    releases = get_release_log(project)
    releases.append({
        "id": item_id,
        "type": item_type,
        "title": title,
        "version": version,
        "commit_sha": commit_sha,
        "released_at": datetime.now().isoformat()
    })
    save_release_log(project, releases)


def get_releases_for_version(project: str, version: str) -> List[Dict]:
    """Get all released items for a specific version."""
    releases = get_release_log(project)
    return [r for r in releases if r.get("version") == version]


# ============================================================
# CHANGELOG
# ============================================================

def get_changelog(project: str) -> List[Dict]:
    """Get project changelog."""
    changelog_file = PROJECTS_DIR / project / "CHANGELOG.json"
    if changelog_file.exists():
        try:
            return json.loads(changelog_file.read_text())
        except:
            pass
    return []


def add_changelog_entry(project: str, version: str, changes: List[str]):
    """Add changelog entry."""
    changelog = get_changelog(project)
    changelog.insert(0, {
        "version": version,
        "date": datetime.now().isoformat(),
        "changes": changes
    })
    (PROJECTS_DIR / project / "CHANGELOG.json").write_text(json.dumps(changelog, indent=2))


def generate_release_notes(project: str, version: str = None) -> str:
    """
    Generate release notes markdown from release log.
    Groups by type: BUGFIX, TODO, NTH
    """
    from .project import get_version
    
    if not version:
        version = get_version(project)
    
    releases = get_releases_for_version(project, version)
    
    if not releases:
        return f"# v{version} Release Notes\n\nNo changes recorded."
    
    # Group by type
    bugfixes = [r for r in releases if r.get("type") == "BUGFIX"]
    todos = [r for r in releases if r.get("type") == "TODO"]
    nths = [r for r in releases if r.get("type") == "NTH"]
    rel_items = [r for r in releases if r.get("type") == "RELEASE"]
    
    lines = [
        f"# v{version} Release Notes",
        "",
        f"**Released:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ""
    ]
    
    if rel_items:
        for item in rel_items:
            lines.append(f"- {item['title']}")
        lines.append("")
    
    if bugfixes:
        lines.append("## BUGFIX")
        for item in bugfixes:
            lines.append(f"- [{item['id']}] {item['title']}")
        lines.append("")
    
    if todos:
        lines.append("## TODO")
        for item in todos:
            lines.append(f"- [{item['id']}] {item['title']}")
        lines.append("")
    
    if nths:
        lines.append("## NTH")
        for item in nths:
            lines.append(f"- [{item['id']}] {item['title']}")
        lines.append("")
    
    content = "\n".join(lines)
    
    # Save to file
    notes_dir = PROJECTS_DIR / project / "release_notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    (notes_dir / f"v{version}.md").write_text(content)
    
    return content


def generate_full_release_notes(project: str) -> str:
    """Generate complete release notes for all versions."""
    releases = get_release_log(project)
    
    # Get unique versions in reverse order (by semver)
    def version_key(v):
        try:
            parts = v.replace("v", "").split(".")
            return tuple(int(p) for p in parts)
        except:
            return (0, 0, 0)
    
    versions = sorted(set(r.get("version", "") for r in releases if r.get("version")), key=version_key, reverse=True)
    
    # Use latest version from releases, not project VERSION file
    current_version = versions[0] if versions else "unknown"
    
    lines = [
        f"# {project} Release Notes",
        "",
        f"**Current Version:** v{current_version}",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ""
    ]
    
    for ver in versions:
        ver_releases = [r for r in releases if r.get("version") == ver]
        bugfixes = [r for r in ver_releases if r.get("type") == "BUGFIX"]
        todos = [r for r in ver_releases if r.get("type") == "TODO"]
        nths = [r for r in ver_releases if r.get("type") == "NTH"]
        rel_items = [r for r in ver_releases if r.get("type") == "RELEASE"]
        
        lines.append(f"## v{ver}")
        
        if rel_items:
            for item in rel_items:
                lines.append(f"- {item['title']}")
        
        if bugfixes:
            lines.append("### BUGFIX")
            for item in bugfixes:
                lines.append(f"- [{item['id']}] {item['title']}")
        
        if todos:
            lines.append("### TODO")
            for item in todos:
                lines.append(f"- [{item['id']}] {item['title']}")
        
        if nths:
            lines.append("### NTH")
            for item in nths:
                lines.append(f"- [{item['id']}] {item['title']}")
        
        lines.append("")
    
    content = "\n".join(lines)
    (PROJECTS_DIR / project / "RELEASE_NOTES.md").write_text(content)
    return content


# ============================================================
# ROADMAP (TODO + NTH not yet processed)
# ============================================================

def get_roadmap(project: str) -> Dict:
    """Get roadmap - pending TODOs and NTHs."""
    todo = get_todo(project)
    
    pending_todos = [t for t in todo if t.get("category") == "todo" and not t.get("done")]
    pending_nths = [t for t in todo if t.get("category") == "nth" and not t.get("done")]
    
    return {
        "todo": pending_todos,
        "nth": pending_nths,
        "total": len(pending_todos) + len(pending_nths)
    }


def generate_roadmap_md(project: str) -> str:
    """Generate roadmap markdown."""
    roadmap = get_roadmap(project)
    
    lines = [
        f"# {project} Roadmap",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ""
    ]
    
    if roadmap["todo"]:
        lines.append("## TODO (Planned Features)")
        for item in roadmap["todo"]:
            lines.append(f"- [{item['id']}] {item['title']}")
        lines.append("")
    
    if roadmap["nth"]:
        lines.append("## NTH (Nice-to-Have)")
        for item in roadmap["nth"]:
            lines.append(f"- [{item['id']}] {item['title']}")
        lines.append("")
    
    if not roadmap["todo"] and not roadmap["nth"]:
        lines.append("*No pending items*")
    
    content = "\n".join(lines)
    (PROJECTS_DIR / project / "ROADMAP.md").write_text(content)
    return content


# ============================================================
# CONVERSATION (per project - CTX007)
# ============================================================

def get_conversation(project: str) -> List[Dict]:
    """Get project conversation history."""
    conv_file = PROJECTS_DIR / project / "conversation.json"
    if conv_file.exists():
        try:
            return json.loads(conv_file.read_text())
        except:
            pass
    return []


def save_conversation(project: str, conversation: List[Dict]):
    """Save conversation."""
    (PROJECTS_DIR / project / "conversation.json").write_text(json.dumps(conversation, indent=2))


def add_message(project: str, role: str, content: str, metadata: Dict = None) -> Dict:
    """Add message to conversation."""
    conversation = get_conversation(project)
    
    msg_id = f"MSG_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6].upper()}"
    message = {
        "id": msg_id,
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    if metadata:
        message["metadata"] = metadata
    
    conversation.append(message)
    # Keep last 100 messages
    conversation = conversation[-100:]
    save_conversation(project, conversation)
    
    return message


def clear_conversation(project: str):
    """Clear conversation history."""
    save_conversation(project, [])


# ============================================================
# DISPLAY
# ============================================================

def show_backlog(project: str):
    """Display project backlog."""
    backlog = get_backlog(project)
    print(f"\n📋 Backlog for {project}:")
    print("-" * 50)
    
    if not backlog:
        print("  (empty)")
        return
    
    for b in backlog:
        status = {"pending": "⏳", "in_progress": "🔄", "done": "✅"}.get(b["status"], "❓")
        prio = b.get("priority", "medium")
        print(f"  {status} [{b['id']}] {b['title'][:45]} ({prio})")
    print()


def show_todo(project: str):
    """Display project TODO."""
    todo = get_todo(project)
    print(f"\n📝 TODO for {project}:")
    print("-" * 50)
    
    if not todo:
        print("  (empty)")
        return
    
    icons = {"todo": "📌", "nth": "💡", "idea": "💭"}
    for t in todo:
        done = "✅" if t["done"] else "⬜"
        icon = icons.get(t.get("category", "todo"), "📝")
        print(f"  {done} [{t['id']}] {icon} {t['title'][:40]}")
    print()


def show_bugfixes(project: str):
    """Display project bugfixes."""
    bugfixes = get_bugfixes(project)
    print(f"\n🐛 Bugfixes for {project}:")
    print("-" * 50)
    
    if not bugfixes:
        print("  (empty)")
        return
    
    for b in bugfixes:
        status = "✅" if b.get("status") == "applied" else "⏳"
        version = f" (v{b['version']})" if b.get("version") else ""
        print(f"  {status} [{b['id']}] {b['title'][:40]}{version}")
    print()


# ============================================================
# OUTPUT FILES
# ============================================================

def get_outputs_path(project: str) -> Path:
    """Get project current directory (where files are generated)."""
    return PROJECTS_DIR / project / "current"


def get_output_files(project: str) -> List[Dict]:
    """Get list of generated files in project current directory (including subdirs like T001/, T002/)."""
    current_dir = get_outputs_path(project)
    if not current_dir.exists():
        return []
    
    # File extensions to show as outputs
    output_extensions = {'.html', '.py', '.js', '.css', '.json', '.md', '.txt', '.sh', '.yaml', '.yml'}
    # Directories/files to skip
    skip_names = {'github', '__pycache__', '.git', 'node_modules', '.snapshot.json', 'snapshots'}
    
    files = []
    
    # Use rglob to recursively find all files
    for f in sorted(current_dir.rglob('*')):
        # Skip if any parent directory is in skip_names
        if any(part in skip_names for part in f.parts):
            continue
        
        if f.is_file() and not f.name.startswith('.') and f.suffix.lower() in output_extensions:
            if f.name not in skip_names:
                stat = f.stat()
                # Get relative path from current_dir
                rel_path = f.relative_to(current_dir)
                files.append({
                    "name": str(rel_path),  # e.g., "T001/manifest.json"
                    "path": str(f),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "ext": f.suffix.lower()
                })
    return files


def register_output_file(project: str, filename: str, content: str = None, binary: bytes = None) -> str:
    """
    Create an output file in project current directory.
    Returns full path to the file.
    """
    current_dir = get_outputs_path(project)
    current_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = current_dir / filename
    
    # Create parent directories if needed
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    if content is not None:
        filepath.write_text(content)
    elif binary is not None:
        filepath.write_bytes(binary)
    
    return str(filepath)


def delete_output_file(project: str, filename: str) -> bool:
    """Delete an output file."""
    filepath = get_outputs_path(project) / filename
    if filepath.exists():
        filepath.unlink()
        return True
    return False


def generate_release_notes(project: str, version: str, since_date: str = None) -> str:
    """
    Generate release notes from completed items.
    
    Args:
        project: Project name
        version: Version being released
        since_date: ISO date string to filter items (optional)
        
    Returns:
        Markdown formatted release notes
    """
    lines = [f"## LocalAgent v{version}", ""]
    lines.append(f"Released: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    
    # Get completed TODO items
    todo = get_todo(project)
    completed_todos = [t for t in todo if t.get("done") and t.get("category") != "nth"]
    if since_date:
        completed_todos = [t for t in completed_todos if t.get("completed", "") >= since_date]
    
    if completed_todos:
        lines.append("### ✅ Completed")
        for item in completed_todos[-10:]:  # Last 10
            title = item.get("title", item.get("task", ""))
            lines.append(f"- {title}")
        lines.append("")
    
    # Get completed NTH (nice-to-have)
    completed_nth = [t for t in todo if t.get("done") and t.get("category") == "nth"]
    if since_date:
        completed_nth = [t for t in completed_nth if t.get("completed", "") >= since_date]
    
    if completed_nth:
        lines.append("### 🎁 Nice-to-Have")
        for item in completed_nth[-5:]:
            title = item.get("title", item.get("task", ""))
            lines.append(f"- {title}")
        lines.append("")
    
    # Get applied bugfixes
    bugfixes = get_bugfixes(project)
    applied_fixes = [b for b in bugfixes if b.get("status") == "applied"]
    if since_date:
        applied_fixes = [b for b in applied_fixes if b.get("applied_at", "") >= since_date]
    
    if applied_fixes:
        lines.append("### 🐛 Bug Fixes")
        for fix in applied_fixes[-5:]:
            lines.append(f"- {fix.get('description', fix.get('title', ''))}")
        lines.append("")
    
    # Get recent backlog items completed
    backlog = get_backlog(project)
    completed_backlog = [b for b in backlog if b.get("done")]
    if since_date:
        completed_backlog = [b for b in completed_backlog if b.get("completed", "") >= since_date]
    
    if completed_backlog:
        lines.append("### 📋 Backlog")
        for item in completed_backlog[-5:]:
            lines.append(f"- {item.get('title', '')}")
        lines.append("")
    
    # If nothing completed, add generic note
    if len(lines) <= 4:
        lines.append("### Changes")
        lines.append("- Various improvements and updates")
        lines.append("")
    
    return "\n".join(lines)


def get_version_changelog(project: str) -> List[Dict]:
    """Get changelog/release history."""
    changelog_file = PROJECTS_DIR / project / "CHANGELOG.json"
    if changelog_file.exists():
        try:
            return json.loads(changelog_file.read_text())
        except:
            pass
    return []


def add_changelog_entry(project: str, version: str, notes: str, commit_sha: str = None):
    """Add entry to changelog."""
    changelog = get_version_changelog(project)
    changelog.insert(0, {
        "version": version,
        "date": datetime.now().isoformat(),
        "notes": notes,
        "commit_sha": commit_sha
    })
    # Keep last 50 entries
    changelog = changelog[:50]
    
    project_dir = PROJECTS_DIR / project
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "CHANGELOG.json").write_text(json.dumps(changelog, indent=2))


# ============================================================
# PENDING RELEASES (waiting for GitHub tests)
# ============================================================

def get_pending_releases(project: str) -> List[Dict]:
    """Get releases waiting for GitHub test results."""
    pending_file = PROJECTS_DIR / project / "PENDING_RELEASES.json"
    if pending_file.exists():
        try:
            return json.loads(pending_file.read_text())
        except:
            pass
    return []


def save_pending_releases(project: str, pending: List[Dict]):
    """Save pending releases."""
    project_dir = PROJECTS_DIR / project
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "PENDING_RELEASES.json").write_text(json.dumps(pending, indent=2))


def track_pending_release(project: str, version: str, todo_ids: List[str], commit_sha: str = None):
    """Track a release that's waiting for GitHub tests to complete."""
    pending = get_pending_releases(project)
    
    # Remove existing entry for same version
    pending = [p for p in pending if p.get("version") != version]
    
    pending.append({
        "version": version,
        "todo_ids": todo_ids,
        "commit_sha": commit_sha,
        "created": datetime.now().isoformat(),
        "status": "pending"
    })
    
    save_pending_releases(project, pending)


def set_todos_testing(project: str, todo_ids: List[str], version: str):
    """Mark TODOs as 'testing' status (waiting for GitHub tests)."""
    todo = get_todo(project)
    for item in todo:
        if item.get("id") in todo_ids:
            item["status"] = "testing"
            item["testing_version"] = version
            item["testing_started"] = datetime.now().isoformat()
    save_todo(project, todo)


def complete_pending_release(project: str, version: str, todo_ids: List[str], failed: bool = False):
    """Mark a pending release as complete and update TODOs."""
    pending = get_pending_releases(project)
    
    # Remove from pending
    pending = [p for p in pending if p.get("version") != version]
    save_pending_releases(project, pending)
    
    # Get TODOs that were testing for this version
    todo = get_todo(project)
    
    if failed:
        # Revert TODOs back to pending status
        for item in todo:
            if item.get("testing_version") == version:
                item["status"] = "pending"
                item.pop("testing_version", None)
                item.pop("testing_started", None)
        save_todo(project, todo)
        return
    
    # Mark TODOs as done
    for item in todo:
        if item.get("id") in todo_ids or item.get("testing_version") == version:
            item["done"] = True
            item["status"] = "completed"
            item["completed"] = datetime.now().isoformat()
            item["version"] = version
            item.pop("testing_version", None)
            item.pop("testing_started", None)
    
    save_todo(project, todo)
