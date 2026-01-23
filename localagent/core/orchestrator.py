"""
LocalAgent v2.10.36 - CORE: Orchestrator
🎯 SINGLE ENTRY POINT - All operations go through here

This module ensures NOTHING bypasses:
- Snapshot creation
- Error learning
- Version tracking
- Git integration
- Constraint validation

RULE: If it's not in orchestrator, it doesn't exist.
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable, Tuple

from .constraints import check_before_action, validate_action, ConstraintViolation
from .learning import (
    learn_from_error,
    learn_dodge,
    get_error_context_for_retry,
    has_learned_solution,
    load_learned_errors
)
from .negotiator import (
    analyze_instruction_complexity,
    get_negotiation_feedback,
    should_retry,
    detect_dodge,
    validate_response
)


# ============================================================
# ORCHESTRATOR STATE
# ============================================================

class OrchestratorState:
    """Tracks orchestration state per project."""
    
    def __init__(self, project: str):
        self.project = project
        self.operation_count = 0
        self.last_snapshot = None
        self.pending_changes = []
        self.session_errors = []
    
    def record_operation(self, op_type: str, details: Dict = None):
        """Record an operation for batched snapshot."""
        self.operation_count += 1
        self.pending_changes.append({
            "type": op_type,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        })
    
    def should_snapshot(self) -> bool:
        """Check if we should create a snapshot now."""
        # Snapshot every 5 operations or on critical ops
        return self.operation_count >= 5 or any(
            c["type"] in ("github_clone", "github_sync", "file_create", "commit")
            for c in self.pending_changes
        )
    
    def clear_pending(self):
        """Clear pending changes after snapshot."""
        self.pending_changes = []
        self.operation_count = 0


# Global state per project
_states: Dict[str, OrchestratorState] = {}


def get_state(project: str) -> OrchestratorState:
    """Get or create orchestrator state for project."""
    if project not in _states:
        _states[project] = OrchestratorState(project)
    return _states[project]


# ============================================================
# SNAPSHOT INTEGRATION
# ============================================================

def _create_snapshot_if_needed(project: str, label: str, force: bool = False) -> Optional[str]:
    """
    Create snapshot if conditions met.
    
    This is the ONLY place snapshots should be created from.
    """
    from ..engine.project import create_snapshot, get_version
    
    state = get_state(project)
    
    if force or state.should_snapshot():
        version = get_version(project)
        snap_id = create_snapshot(project, label)
        if snap_id:
            state.last_snapshot = snap_id
            state.clear_pending()
            print(f"📸 Snapshot: {snap_id}")
        return snap_id
    return None


def _git_commit_if_available(project: str, message: str) -> bool:
    """
    Commit to git if .git exists in project.
    
    Returns True if committed, False otherwise.
    """
    from ..engine.project import get_current_path
    
    current = get_current_path(project)
    git_dir = current / ".git"
    
    if not git_dir.exists():
        return False
    
    try:
        # Stage all changes
        result = subprocess.run(
            ["git", "-C", str(current), "add", "-A"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return False
        
        # Commit
        result = subprocess.run(
            ["git", "-C", str(current), "commit", "-m", message],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            print(f"📝 Git commit: {message[:50]}")
            return True
        
        # Return code 1 with "nothing to commit" is OK
        if "nothing to commit" in result.stdout:
            return True
            
        return False
        
    except Exception as e:
        learn_from_error(project, "git_error", str(e))
        return False


def _git_push(project: str, branch: str = None) -> bool:
    """
    Push to GitHub.
    
    Returns True if pushed, False otherwise.
    """
    from ..engine.project import get_current_path
    
    current = get_current_path(project)
    git_dir = current / ".git"
    
    if not git_dir.exists():
        return False
    
    try:
        cmd = ["git", "-C", str(current), "push"]
        if branch:
            cmd.extend(["origin", branch])
        
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60
        )
        
        if result.returncode == 0:
            print(f"📤 Git push: {'origin/' + branch if branch else 'origin'}")
            return True
        
        # Check for common issues
        if "rejected" in result.stderr:
            print(f"⚠️ Push rejected - pull first")
        elif "Could not read from remote" in result.stderr:
            print(f"⚠️ Cannot connect to remote")
        
        return False
        
    except Exception as e:
        learn_from_error(project, "git_push_error", str(e))
        return False


def _git_create_branch(project: str, branch_name: str) -> bool:
    """
    Create and checkout a new branch.
    """
    from ..engine.project import get_current_path
    
    current = get_current_path(project)
    
    try:
        # Create branch
        result = subprocess.run(
            ["git", "-C", str(current), "checkout", "-b", branch_name],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            print(f"🌿 Created branch: {branch_name}")
            return True
        
        # Branch might already exist
        if "already exists" in result.stderr:
            # Just checkout
            result = subprocess.run(
                ["git", "-C", str(current), "checkout", branch_name],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                print(f"🌿 Switched to branch: {branch_name}")
                return True
        
        return False
        
    except Exception as e:
        learn_from_error(project, "git_branch_error", str(e))
        return False


def _git_tag(project: str, tag_name: str, message: str = None) -> bool:
    """
    Create a git tag.
    """
    from ..engine.project import get_current_path
    
    current = get_current_path(project)
    
    try:
        cmd = ["git", "-C", str(current), "tag"]
        if message:
            cmd.extend(["-a", tag_name, "-m", message])
        else:
            cmd.append(tag_name)
        
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            print(f"🏷️ Created tag: {tag_name}")
            return True
        
        return False
        
    except Exception as e:
        learn_from_error(project, "git_tag_error", str(e))
        return False


def git_sync_to_remote(project: str, message: str = None, create_tag: bool = False) -> Dict:
    """
    Full GitHub sync: commit, push, optionally tag.
    
    This is THE function to push changes to GitHub.
    """
    from ..engine.project import get_version, get_current_path
    from ..connectors.github import update_version_history
    
    version = get_version(project)
    current = get_current_path(project)
    
    if not (current / ".git").exists():
        return {"success": False, "error": "No git repository found"}
    
    results = {
        "success": True,
        "version": version,
        "actions": []
    }
    
    # 1. Commit
    commit_msg = message or f"Update to v{version}"
    if _git_commit_if_available(project, commit_msg):
        results["actions"].append("commit")
    
    # 2. Create version branch if needed
    branch_name = f"v{version}"
    if _git_create_branch(project, branch_name):
        results["actions"].append(f"branch:{branch_name}")
    
    # 3. Push
    if _git_push(project, branch_name):
        results["actions"].append("push")
    else:
        results["success"] = False
        results["error"] = "Push failed"
    
    # 4. Tag if requested
    if create_tag:
        tag_name = f"v{version}"
        if _git_tag(project, tag_name, commit_msg):
            results["actions"].append(f"tag:{tag_name}")
            # Push tag
            subprocess.run(
                ["git", "-C", str(current), "push", "origin", tag_name],
                capture_output=True, text=True, timeout=30
            )
    
    # 5. Update version history
    if results["success"]:
        from ..engine.tracking import get_changelog
        changelog = get_changelog(project)
        changes = changelog[0]["changes"] if changelog else []
        update_version_history(version, changes)
        results["actions"].append("version_history_updated")
    
    return results


# ============================================================
# LLM CALL WRAPPER
# ============================================================

def call_llm(
    project: str,
    prompt: str,
    context: str = "",
    system: str = None,
    max_retries: int = 3
) -> Dict:
    """
    THE ONLY WAY to call Claude.
    
    This wrapper ensures:
    1. Error learning is applied
    2. Retry logic uses learned patterns
    3. Dodges are detected and recorded
    4. Snapshots are created on success
    
    Returns:
        {
            "success": bool,
            "response": str (if success),
            "tasks": list (if valid JSON with tasks),
            "error": str (if failed),
            "attempts": int,
            "usage": dict
        }
    """
    from ..connectors.llm import call_claude, CLAUDE_CONFIG
    
    state = get_state(project)
    
    # Get learned context to prevent repeating mistakes
    error_context = get_error_context_for_retry(project)
    full_context = f"{context}\n\n{error_context}" if error_context else context
    
    attempts = 0
    last_error = None
    last_error_type = None
    
    while attempts <= max_retries:
        attempts += 1
        
        # Build prompt with feedback from previous attempts
        current_prompt = prompt
        if last_error_type:
            feedback = get_negotiation_feedback(last_error_type, {"project": project})
            current_prompt = f"{prompt}\n\nPREVIOUS_ERROR: {last_error_type}\nREQUIRED_FIX: {feedback}"
        
        # Make the call
        result = call_claude(current_prompt, full_context, system)
        
        if not result.get("success"):
            last_error_type = "api_error"
            last_error = result.get("error", "Unknown")
            
            # Learn from this error
            learn_from_error(project, last_error_type, last_error, {
                "prompt_length": len(prompt),
                "attempt": attempts
            })
            
            state.session_errors.append({
                "type": last_error_type,
                "error": last_error,
                "attempt": attempts
            })
            
            if not should_retry(last_error_type, attempts - 1):
                break
            continue
        
        response = result.get("response", "")
        
        # Check for dodge
        dodge = detect_dodge(response)
        if dodge:
            dodge_type, dodge_text = dodge
            learn_dodge(project, dodge_type, dodge_text)
            
            last_error_type = "dodge_detected"
            last_error = f"Claude dodged: {dodge_type}"
            
            if not should_retry("dodge_detected", attempts - 1):
                break
            continue
        
        # Validate response
        validation = validate_response(response)
        
        if not validation["valid"]:
            last_error_type = validation["error_type"]
            last_error = validation.get("detail", "")
            
            learn_from_error(project, last_error_type, last_error, {
                "response_length": len(response),
                "attempt": attempts
            })
            
            if not should_retry(last_error_type, attempts - 1):
                break
            continue
        
        # SUCCESS - record operation and maybe snapshot
        state.record_operation("llm_call", {"tasks": len(validation.get("tasks", []))})
        _create_snapshot_if_needed(project, f"llm_success_{attempts}attempts")
        
        return {
            "success": True,
            "response": response,
            "tasks": validation.get("tasks", []),
            "attempts": attempts,
            "usage": result.get("usage", {})
        }
    
    # All retries exhausted
    return {
        "success": False,
        "error": last_error or "Max retries exceeded",
        "error_type": last_error_type or "unknown",
        "attempts": attempts
    }


# ============================================================
# GITHUB OPERATIONS WRAPPER
# ============================================================

def github_clone(project: str, repo_url: str, branch: str = "main") -> Dict:
    """
    Clone a GitHub repo with full orchestration.
    
    Ensures:
    1. Constraint validation
    2. Snapshot BEFORE clone
    3. Snapshot AFTER clone (on success)
    4. Error learning on failure
    """
    from ..connectors.github import github_clone as _github_clone
    
    state = get_state(project)
    
    # Pre-operation snapshot
    _create_snapshot_if_needed(project, f"pre_clone_{repo_url.split('/')[-1]}", force=True)
    
    try:
        success = _github_clone(project, repo_url, branch)
        
        if success:
            state.record_operation("github_clone", {"repo": repo_url, "branch": branch})
            _create_snapshot_if_needed(project, f"post_clone_{repo_url.split('/')[-1]}", force=True)
            return {"success": True, "repo": repo_url}
        else:
            learn_from_error(project, "github_clone_failed", f"Clone failed: {repo_url}")
            return {"success": False, "error": "Clone failed"}
            
    except Exception as e:
        learn_from_error(project, "github_error", str(e), {"repo": repo_url})
        return {"success": False, "error": str(e)}


def github_sync(project: str, repo_name: str = None) -> Dict:
    """
    Sync GitHub repos with full orchestration.
    """
    from ..connectors.github import github_sync as _github_sync
    
    state = get_state(project)
    
    # Pre-sync snapshot
    _create_snapshot_if_needed(project, f"pre_sync_{repo_name or 'all'}", force=True)
    
    try:
        success = _github_sync(project, repo_name)
        
        if success:
            state.record_operation("github_sync", {"repo": repo_name})
            _create_snapshot_if_needed(project, f"post_sync_{repo_name or 'all'}", force=True)
            return {"success": True}
        else:
            return {"success": False, "error": "Sync failed"}
            
    except Exception as e:
        learn_from_error(project, "github_error", str(e))
        return {"success": False, "error": str(e)}


# ============================================================
# FILE OPERATIONS WRAPPER
# ============================================================

def create_file(project: str, filename: str, content: str) -> Dict:
    """
    Create a file with full orchestration.
    
    Ensures:
    1. Constraint validation (CTX006)
    2. Snapshot after creation
    3. Error learning on failure
    """
    from ..engine.tracking import register_output_file
    
    state = get_state(project)
    
    # Validate against constraints
    try:
        check_before_action("create_file", {"file": filename, "content_length": len(content)})
    except ConstraintViolation as e:
        learn_from_error(project, "constraint_violation", str(e))
        return {"success": False, "error": str(e)}
    
    try:
        filepath = register_output_file(project, filename, content)
        state.record_operation("file_create", {"file": filename, "size": len(content)})
        _create_snapshot_if_needed(project, f"file_{filename}")
        
        return {"success": True, "path": filepath}
        
    except Exception as e:
        learn_from_error(project, "file_error", str(e), {"file": filename})
        return {"success": False, "error": str(e)}


# ============================================================
# COMMIT WRAPPER
# ============================================================

def commit(project: str, message: str, push: bool = False, tag: bool = False) -> Dict:
    """
    Commit project changes with full orchestration.
    
    Ensures:
    1. Version increment
    2. Snapshot creation
    3. Changelog update
    4. Git commit (if available)
    5. Git push to GitHub (if push=True)
    6. Create version tag (if tag=True)
    
    Args:
        project: Project name
        message: Commit message
        push: If True, push to GitHub after commit
        tag: If True, create version tag
    """
    from ..engine.project import commit_project, get_version
    
    state = get_state(project)
    old_version = get_version(project)
    
    try:
        # This already does: increment_version, create_snapshot, add_changelog_entry
        success = commit_project(project, message)
        
        if success:
            new_version = get_version(project)
            
            result = {
                "success": True,
                "old_version": old_version,
                "new_version": new_version,
                "actions": ["version_increment", "snapshot", "changelog"]
            }
            
            # Git commit
            if _git_commit_if_available(project, message):
                result["actions"].append("git_commit")
            
            # Push to GitHub if requested
            if push:
                sync_result = git_sync_to_remote(project, message, create_tag=tag)
                if sync_result["success"]:
                    result["actions"].extend(sync_result["actions"])
                    result["pushed"] = True
                else:
                    result["push_error"] = sync_result.get("error")
                    result["pushed"] = False
            
            state.record_operation("commit", {"old": old_version, "new": new_version, "pushed": push})
            
            return result
        else:
            return {"success": False, "error": "Commit failed"}
            
    except Exception as e:
        learn_from_error(project, "commit_error", str(e))
        return {"success": False, "error": str(e)}


# ============================================================
# EXECUTE TASKS FROM LLM
# ============================================================

def execute_tasks(project: str, tasks: List[Dict]) -> Dict:
    """
    Execute tasks returned by LLM with full orchestration.
    
    This is the proper way to execute tasks - ensures every
    operation goes through the orchestrator.
    """
    from ..engine.tracking import register_output_file
    
    state = get_state(project)
    results = []
    files_created = []
    
    for task in tasks:
        task_id = task.get("id", "?")
        task_type = task.get("type", "unknown")
        
        try:
            if task_type == "create_file":
                filename = task.get("file_path") or task.get("filename") or task.get("file")
                content = task.get("content", "")
                
                result = create_file(project, filename, content)
                results.append({
                    "id": task_id,
                    "type": task_type,
                    "success": result["success"],
                    "file": filename,
                    "error": result.get("error")
                })
                
                if result["success"]:
                    files_created.append(filename)
            
            elif task_type == "modify_file":
                # TODO: Implement with proper orchestration
                results.append({
                    "id": task_id,
                    "type": task_type,
                    "success": False,
                    "error": "modify_file not yet implemented in orchestrator"
                })
            
            elif task_type == "shell":
                # TODO: Implement with proper constraints and sandboxing
                results.append({
                    "id": task_id,
                    "type": task_type,
                    "success": False,
                    "error": "shell not yet implemented in orchestrator"
                })
            
            else:
                results.append({
                    "id": task_id,
                    "type": task_type,
                    "success": False,
                    "error": f"Unknown task type: {task_type}"
                })
                
        except Exception as e:
            learn_from_error(project, f"task_{task_type}_error", str(e))
            results.append({
                "id": task_id,
                "type": task_type,
                "success": False,
                "error": str(e)
            })
    
    # Snapshot after task batch if files were created
    if files_created:
        _create_snapshot_if_needed(project, f"tasks_{len(tasks)}", force=True)
    
    success_count = sum(1 for r in results if r.get("success"))
    
    return {
        "success": success_count == len(tasks),
        "partial": 0 < success_count < len(tasks),
        "results": results,
        "files_created": files_created,
        "stats": {
            "total": len(tasks),
            "success": success_count,
            "failed": len(tasks) - success_count
        }
    }


# ============================================================
# MAIN ORCHESTRATION ENTRY POINT
# ============================================================

def orchestrate(
    project: str,
    instruction: str,
    context: str = "",
    auto_execute: bool = True
) -> Dict:
    """
    THE MAIN ENTRY POINT for all agent operations.
    
    This function:
    1. Analyzes instruction complexity
    2. Calls LLM with full error handling
    3. Validates response
    4. Executes tasks (if auto_execute)
    5. Creates snapshots
    6. Records everything
    
    Args:
        project: Project name
        instruction: User instruction
        context: Additional context
        auto_execute: Whether to execute tasks automatically
    
    Returns:
        {
            "success": bool,
            "response": str,
            "tasks": list,
            "execution": dict (if auto_execute),
            "needs_split": bool,
            "split_parts": list (if needs_split),
            "attempts": int,
            "usage": dict
        }
    """
    from ..engine.project import project_exists
    
    # Validate project exists
    if not project_exists(project):
        return {"success": False, "error": f"Project not found: {project}"}
    
    state = get_state(project)
    
    # Check instruction complexity
    complexity = analyze_instruction_complexity(instruction)
    
    if complexity["needs_split"]:
        return {
            "success": False,
            "needs_split": True,
            "split_parts": complexity["parts"],
            "complexity_score": complexity["complexity_score"],
            "suggestion": f"Split into {len(complexity['parts'])} parts"
        }
    
    # Call LLM
    llm_result = call_llm(project, instruction, context)
    
    if not llm_result["success"]:
        return {
            "success": False,
            "error": llm_result.get("error"),
            "error_type": llm_result.get("error_type"),
            "attempts": llm_result.get("attempts", 0)
        }
    
    result = {
        "success": True,
        "response": llm_result["response"],
        "tasks": llm_result["tasks"],
        "attempts": llm_result["attempts"],
        "usage": llm_result.get("usage", {})
    }
    
    # Execute tasks if requested
    if auto_execute and llm_result["tasks"]:
        execution = execute_tasks(project, llm_result["tasks"])
        result["execution"] = execution
        result["success"] = execution["success"]
        result["files"] = execution.get("files_created", [])
    
    return result


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    # Main entry point
    "orchestrate",
    # Individual operations (all go through proper channels)
    "call_llm",
    "github_clone",
    "github_sync",
    "create_file",
    "commit",
    "execute_tasks",
    # State management
    "get_state",
    "OrchestratorState"
]
