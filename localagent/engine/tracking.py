"""
LocalAgent v2.10.20 - ENGINE: Tracking
Backlog, TODO, changelog, conversation, output files (per project)
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List

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
    (PROJECTS_DIR / project / "BACKLOG.json").write_text(json.dumps(backlog, indent=2))


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
# TODO
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
    (PROJECTS_DIR / project / "TODO.json").write_text(json.dumps(todo, indent=2))


def add_todo_item(project: str, title: str, category: str = "todo") -> str:
    """Add TODO item. Categories: todo, nth, idea."""
    todo = get_todo(project)
    
    num = 1
    existing = {t.get("id", "") for t in todo}
    while f"T{num:03d}" in existing:
        num += 1
    item_id = f"T{num:03d}"
    
    todo.append({
        "id": item_id,
        "title": title,
        "category": category,
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


def generate_release_notes(project: str) -> str:
    """Generate release notes markdown."""
    from .project import get_version
    
    changelog = get_changelog(project)
    version = get_version(project)
    
    lines = [
        f"# {project} Release Notes",
        "",
        f"**Version:** v{version}",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ""
    ]
    
    for entry in changelog[:20]:
        lines.append(f"## v{entry['version']} ({entry['date'][:10]})")
        for change in entry["changes"]:
            lines.append(f"- {change}")
        lines.append("")
    
    content = "\n".join(lines)
    (PROJECTS_DIR / project / "RELEASE_NOTES.md").write_text(content)
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
