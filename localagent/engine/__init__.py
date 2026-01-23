"""
LocalAgent v2.10.17 - ENGINE Module
Project management + Tracking
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
    get_backlog,
    save_backlog,
    add_backlog_item,
    update_backlog_item,
    complete_backlog_item,
    get_pending_backlog,
    get_todo,
    save_todo,
    add_todo_item,
    toggle_todo,
    get_changelog,
    add_changelog_entry,
    generate_release_notes,
    get_conversation,
    save_conversation,
    add_message,
    clear_conversation,
    show_backlog,
    show_todo,
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
    # TODO
    "get_todo", "save_todo", "add_todo_item", "toggle_todo",
    # Changelog
    "get_changelog", "add_changelog_entry", "generate_release_notes",
    # Conversation
    "get_conversation", "save_conversation", "add_message", "clear_conversation",
    # Output files
    "get_outputs_path", "get_output_files", "register_output_file", "delete_output_file",
    # Display
    "show_backlog", "show_todo"
]
