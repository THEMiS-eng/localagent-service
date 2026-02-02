"""
LocalAgent - ENGINE Module
Project management + Tracking (TODO, NTH, BUGFIX, Releases)
"""

from .project import (
    AGENT_DIR,
    PROJECTS_DIR,
    CONFIG_DIR,
    API_KEY_FILE,
    get_project_path,
    get_current_path,
    get_snapshots_path,
    get_version,
    set_version,
    increment_version,
    create_snapshot,
    list_snapshots,
    rollback,
    init_project,
    commit_project,
    list_projects,
    project_exists
)

from .tracking import (
    # Backlog
    get_backlog,
    save_backlog,
    add_backlog_item,
    update_backlog_item,
    complete_backlog_item,
    get_pending_backlog,
    # TODO/NTH
    get_todo,
    save_todo,
    add_todo_item,
    toggle_todo,
    complete_todo_item,
    # BUGFIX
    get_bugfixes,
    save_bugfixes,
    add_bugfix,
    apply_bugfix,
    get_pending_bugfixes,
    # Release Log
    get_release_log,
    add_release_item,
    get_releases_for_version,
    # Changelog & Release Notes
    get_changelog,
    add_changelog_entry,
    generate_release_notes,
    generate_full_release_notes,
    # Roadmap
    get_roadmap,
    generate_roadmap_md,
    # Conversation
    get_conversation,
    save_conversation,
    add_message,
    clear_conversation,
    # Display
    show_backlog,
    show_todo,
    show_bugfixes,
    # Output files
    get_outputs_path,
    get_output_files,
    register_output_file,
    delete_output_file
)

__all__ = [
    # Paths
    "AGENT_DIR", "PROJECTS_DIR", "CONFIG_DIR", "API_KEY_FILE",
    "get_project_path", "get_current_path", "get_snapshots_path",
    # Versioning
    "get_version", "set_version", "increment_version",
    # Snapshots
    "create_snapshot", "list_snapshots", "rollback",
    # Project lifecycle
    "init_project", "commit_project", "list_projects", "project_exists",
    # Backlog
    "get_backlog", "save_backlog", "add_backlog_item", "update_backlog_item", 
    "complete_backlog_item", "get_pending_backlog",
    # TODO/NTH
    "get_todo", "save_todo", "add_todo_item", "toggle_todo", "complete_todo_item",
    # BUGFIX
    "get_bugfixes", "save_bugfixes", "add_bugfix", "apply_bugfix", "get_pending_bugfixes",
    # Release Log
    "get_release_log", "add_release_item", "get_releases_for_version",
    # Changelog & Release Notes
    "get_changelog", "add_changelog_entry", "generate_release_notes", "generate_full_release_notes",
    # Roadmap
    "get_roadmap", "generate_roadmap_md",
    # Conversation
    "get_conversation", "save_conversation", "add_message", "clear_conversation",
    # Output files
    "get_outputs_path", "get_output_files", "register_output_file", "delete_output_file",
    # Display
    "show_backlog", "show_todo", "show_bugfixes"
]
