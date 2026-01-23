"""
LocalAgent v3.0.30 - CORE: Protocol Enforcement
🔐 SINGLE SOURCE OF TRUTH for TODO processing

This module enforces the EXACT protocol:

PROTOCOL FLOW (IMMUTABLE):
==========================
1. SERVICE WORKER receives TODO
2. SERVICE WORKER calls GitHub API → get latest release version
3. SERVICE WORKER calculates next version
4. SERVICE WORKER creates snapshot BEFORE (ENV003/ENV014)
5. SERVICE WORKER calls Claude with:
   - Current GitHub version
   - Next version (calculated)
   - TODO instruction
   - Constraints (CTX)
6. Claude returns tasks (max 3 per CTX003)
7. SERVICE WORKER validates response
8. SERVICE WORKER executes tasks
9. SERVICE WORKER creates snapshot AFTER
10. SERVICE WORKER commits to git
11. SERVICE WORKER pushes to GitHub
12. SERVICE WORKER creates GitHub release with next version
13. SERVICE WORKER verifies release (ENV013)
14. SERVICE WORKER marks TODO as done

TRACKING:
=========
Every step is logged with timestamp and status.
Any failure stops the protocol and logs the violation.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field, asdict

from .constraints import validate_action, ConstraintViolation, get_constraint

logger = logging.getLogger(__name__)


# ============================================================
# PROTOCOL TRACKING
# ============================================================

@dataclass
class ProtocolStep:
    """Single step in protocol execution."""
    step_id: str
    name: str
    status: str = "pending"  # pending, running, success, failed, skipped
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    data: Dict = field(default_factory=dict)
    error: Optional[str] = None
    constraint_checks: List[str] = field(default_factory=list)


@dataclass
class ProtocolExecution:
    """Complete protocol execution record."""
    execution_id: str
    todo_id: str
    todo_title: str
    project: str
    github_repo: str
    started_at: str
    completed_at: Optional[str] = None
    status: str = "running"  # running, success, failed, aborted
    current_step: int = 0
    steps: List[ProtocolStep] = field(default_factory=list)
    
    # Version tracking
    github_version_before: Optional[str] = None
    github_version_after: Optional[str] = None
    calculated_next_version: Optional[str] = None
    
    # Artifacts
    snapshot_before_id: Optional[str] = None
    snapshot_after_id: Optional[str] = None
    commit_sha: Optional[str] = None
    release_url: Optional[str] = None
    files_created: List[str] = field(default_factory=list)
    
    # Violations
    violations: List[str] = field(default_factory=list)


# ============================================================
# PROTOCOL STEPS DEFINITION
# ============================================================

PROTOCOL_STEPS = [
    {"id": "STEP_01", "name": "fetch_github_version", "constraint": "ENV012"},
    {"id": "STEP_02", "name": "calculate_next_version", "constraint": "ENV012"},
    {"id": "STEP_03", "name": "create_snapshot_before", "constraint": "ENV003"},
    {"id": "STEP_04", "name": "build_claude_context", "constraint": "ENV015"},
    {"id": "STEP_05", "name": "call_claude", "constraint": "CTX001"},
    {"id": "STEP_06", "name": "validate_response", "constraint": "CTX003"},
    {"id": "STEP_07", "name": "execute_tasks", "constraint": "CTX004"},
    {"id": "STEP_08", "name": "create_snapshot_after", "constraint": "ENV014"},
    {"id": "STEP_09", "name": "git_commit", "constraint": "ENV004"},
    {"id": "STEP_10", "name": "git_push", "constraint": "ENV009"},
    {"id": "STEP_11", "name": "create_github_release", "constraint": "ENV012"},
    {"id": "STEP_12", "name": "verify_release", "constraint": "ENV013"},
    {"id": "STEP_13", "name": "mark_todo_done", "constraint": None},
]


# ============================================================
# PROTOCOL EXECUTOR
# ============================================================

class ProtocolExecutor:
    """
    Executes TODO processing with STRICT protocol enforcement.
    
    Every step is tracked and validated against constraints.
    Any violation stops execution immediately.
    """
    
    def __init__(self, project: str, github_repo: str, github_token: Optional[str] = None):
        self.project = project
        self.github_repo = github_repo
        self.github_token = github_token
        self.execution: Optional[ProtocolExecution] = None
        self._call_claude_fn: Optional[Callable] = None
        
    def set_claude_function(self, fn: Callable):
        """Set the function to call Claude API."""
        self._call_claude_fn = fn
        
    def execute_todo(self, todo_id: str, todo_title: str) -> ProtocolExecution:
        """
        Execute a TODO with full protocol enforcement.
        
        Returns ProtocolExecution with complete tracking.
        """
        # Initialize execution record
        execution_id = f"EXEC_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{todo_id}"
        self.execution = ProtocolExecution(
            execution_id=execution_id,
            todo_id=todo_id,
            todo_title=todo_title,
            project=self.project,
            github_repo=self.github_repo,
            started_at=datetime.now().isoformat(),
            steps=[ProtocolStep(step_id=s["id"], name=s["name"]) for s in PROTOCOL_STEPS]
        )
        
        logger.info(f"{'='*60}")
        logger.info(f"🚀 PROTOCOL START: {execution_id}")
        logger.info(f"   TODO: [{todo_id}] {todo_title[:50]}")
        logger.info(f"   Project: {self.project}")
        logger.info(f"   GitHub: {self.github_repo}")
        logger.info(f"{'='*60}")
        
        try:
            # Execute each step in order
            for i, step_def in enumerate(PROTOCOL_STEPS):
                self.execution.current_step = i
                step = self.execution.steps[i]
                
                logger.info(f"\n📍 STEP {i+1}/{len(PROTOCOL_STEPS)}: {step_def['name']}")
                
                # Check constraint before step
                if step_def.get("constraint"):
                    constraint = get_constraint(step_def["constraint"])
                    if constraint:
                        step.constraint_checks.append(f"CHECK: {constraint['id']} - {constraint['rule']}")
                        logger.info(f"   🔒 Constraint: [{constraint['id']}] {constraint['rule']}")
                
                # Execute step
                step.status = "running"
                step.started_at = datetime.now().isoformat()
                
                success, data, error = self._execute_step(step_def["name"])
                
                step.completed_at = datetime.now().isoformat()
                step.data = data or {}
                
                if success:
                    step.status = "success"
                    logger.info(f"   ✅ {step_def['name']} completed")
                else:
                    step.status = "failed"
                    step.error = error
                    self.execution.status = "failed"
                    self.execution.violations.append(f"{step_def['id']}: {error}")
                    logger.error(f"   ❌ {step_def['name']} FAILED: {error}")
                    break
            
            # All steps completed
            if self.execution.status == "running":
                self.execution.status = "success"
                logger.info(f"\n{'='*60}")
                logger.info(f"✅ PROTOCOL SUCCESS: {execution_id}")
                logger.info(f"   Version: {self.execution.github_version_before} → {self.execution.github_version_after}")
                logger.info(f"   Files: {len(self.execution.files_created)}")
                logger.info(f"   Release: {self.execution.release_url}")
                logger.info(f"{'='*60}")
                
        except ConstraintViolation as e:
            self.execution.status = "aborted"
            self.execution.violations.extend(e.violations)
            logger.error(f"\n🚫 PROTOCOL ABORTED: Constraint violation")
            for v in e.violations:
                logger.error(f"   ❌ {v}")
                
        except Exception as e:
            self.execution.status = "failed"
            self.execution.violations.append(f"Unexpected error: {str(e)}")
            logger.exception(f"\n💥 PROTOCOL FAILED: {e}")
            
        finally:
            self.execution.completed_at = datetime.now().isoformat()
            self._save_execution_log()
            
        return self.execution
    
    def _execute_step(self, step_name: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Execute a single protocol step."""
        
        if step_name == "fetch_github_version":
            return self._step_fetch_github_version()
            
        elif step_name == "calculate_next_version":
            return self._step_calculate_next_version()
            
        elif step_name == "create_snapshot_before":
            return self._step_create_snapshot("before")
            
        elif step_name == "build_claude_context":
            return self._step_build_claude_context()
            
        elif step_name == "call_claude":
            return self._step_call_claude()
            
        elif step_name == "validate_response":
            return self._step_validate_response()
            
        elif step_name == "execute_tasks":
            return self._step_execute_tasks()
            
        elif step_name == "create_snapshot_after":
            return self._step_create_snapshot("after")
            
        elif step_name == "git_commit":
            return self._step_git_commit()
            
        elif step_name == "git_push":
            return self._step_git_push()
            
        elif step_name == "create_github_release":
            return self._step_create_github_release()
            
        elif step_name == "verify_release":
            return self._step_verify_release()
            
        elif step_name == "mark_todo_done":
            return self._step_mark_todo_done()
            
        else:
            return False, None, f"Unknown step: {step_name}"
    
    # ============================================================
    # STEP IMPLEMENTATIONS
    # ============================================================
    
    def _step_fetch_github_version(self) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """STEP 1: Fetch current version from GitHub releases (ENV012)."""
        from ..connectors.github import fetch_github_version, fetch_github_tags
        
        # Try releases first
        version = fetch_github_version(self.github_repo)
        
        if version:
            self.execution.github_version_before = version
            return True, {"version": version, "source": "releases"}, None
        
        # Fallback to tags
        tags = fetch_github_tags(self.github_repo, limit=1)
        if tags:
            version = tags[0]
            self.execution.github_version_before = version
            return True, {"version": version, "source": "tags"}, None
        
        # No version found - this is first release
        self.execution.github_version_before = "0.0.0"
        return True, {"version": "0.0.0", "source": "initial"}, None
    
    def _step_calculate_next_version(self) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """STEP 2: Calculate next version (patch increment)."""
        current = self.execution.github_version_before
        
        if not current:
            return False, None, "ENV012: No current version - must fetch from GitHub first"
        
        # Parse version
        parts = current.split(".")
        if len(parts) == 3:
            major, minor, patch = parts
            next_patch = int(patch) + 1
            next_version = f"{major}.{minor}.{next_patch:03d}"
        else:
            # Invalid format, start fresh
            next_version = "0.0.001"
        
        self.execution.calculated_next_version = next_version
        return True, {"current": current, "next": next_version}, None
    
    def _step_create_snapshot(self, label: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """STEP 3/8: Create snapshot before/after (ENV003/ENV014)."""
        from ..engine.project import create_snapshot
        
        snapshot_label = f"{label}_{self.execution.todo_id}"
        snapshot_id = create_snapshot(self.project, snapshot_label)
        
        if not snapshot_id:
            constraint = "ENV003" if label == "before" else "ENV014"
            return False, None, f"{constraint}: Failed to create snapshot {label}"
        
        if label == "before":
            self.execution.snapshot_before_id = snapshot_id
        else:
            self.execution.snapshot_after_id = snapshot_id
            
        return True, {"snapshot_id": snapshot_id, "label": snapshot_label}, None
    
    def _step_build_claude_context(self) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """STEP 4: Build context for Claude with version info (ENV015)."""
        from .constraints import build_system_prompt
        
        # Build system prompt with constraints
        system_prompt = build_system_prompt(self.project)
        
        # Add version context (ENV015)
        version_context = f"""
=== VERSION CONTEXT (ENV015) ===
Current GitHub version: {self.execution.github_version_before}
Next version to create: {self.execution.calculated_next_version}
GitHub repo: {self.github_repo}

You are generating code for version {self.execution.calculated_next_version}.
"""
        
        full_prompt = system_prompt + "\n" + version_context
        
        # Build user message
        user_message = f"""
TODO: {self.execution.todo_title}

Generate the necessary files for this TODO.
Remember: Max 3 tasks, each task max 50 lines.
Response must be valid JSON only.
"""
        
        self._claude_context = {
            "system": full_prompt,
            "user": user_message
        }
        
        return True, {"system_length": len(full_prompt), "user_length": len(user_message)}, None
    
    def _step_call_claude(self) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """STEP 5: Call Claude API (CTX001)."""
        if not self._call_claude_fn:
            return False, None, "No Claude function configured"
        
        if not hasattr(self, '_claude_context'):
            return False, None, "No context built - run build_claude_context first"
        
        try:
            response = self._call_claude_fn(
                system=self._claude_context["system"],
                user=self._claude_context["user"]
            )
            
            self._claude_response = response
            return True, {"response_length": len(response) if response else 0}, None
            
        except Exception as e:
            return False, None, f"Claude API error: {str(e)}"
    
    def _step_validate_response(self) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """STEP 6: Validate Claude response (CTX003)."""
        if not hasattr(self, '_claude_response') or not self._claude_response:
            return False, None, "No Claude response to validate"
        
        response = self._claude_response
        
        # Strip markdown if present (CTX002)
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        
        # Parse JSON (CTX001)
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            return False, None, f"CTX001: Invalid JSON - {str(e)}"
        
        # Check tasks
        tasks = data.get("tasks", [])
        
        # CTX003: Max 3 tasks
        if len(tasks) > 3:
            return False, None, f"CTX003: Too many tasks ({len(tasks)} > 3)"
        
        # CTX004: Max 50 lines per task
        for task in tasks:
            content = task.get("content", "")
            lines = content.count("\n") + 1
            if lines > 50:
                return False, None, f"CTX004: Task {task.get('id', '?')} exceeds 50 lines ({lines})"
        
        self._validated_tasks = tasks
        return True, {"task_count": len(tasks), "tasks": [t.get("id") for t in tasks]}, None
    
    def _step_execute_tasks(self) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """STEP 7: Execute validated tasks (CTX004)."""
        from ..engine.project import get_current_path
        from ..engine.tracking import register_output_file
        
        if not hasattr(self, '_validated_tasks'):
            return False, None, "No validated tasks to execute"
        
        tasks = self._validated_tasks
        current_path = get_current_path(self.project)
        
        # Create TODO folder
        todo_folder = current_path / self.execution.todo_id
        todo_folder.mkdir(parents=True, exist_ok=True)
        
        files_created = []
        
        for task in tasks:
            task_type = task.get("type", "")
            
            if task_type == "create_file":
                filename = task.get("filename") or task.get("file_path") or task.get("file")
                content = task.get("content", "")
                
                if filename and content:
                    # Save to TODO folder
                    file_path = todo_folder / filename
                    file_path.write_text(content)
                    
                    # Register in outputs
                    rel_path = f"{self.execution.todo_id}/{filename}"
                    register_output_file(self.project, rel_path, content)
                    files_created.append(rel_path)
                    
                    logger.info(f"      📄 Created: {rel_path}")
        
        self.execution.files_created = files_created
        return True, {"files_created": files_created, "folder": str(todo_folder)}, None
    
    def _step_git_commit(self) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """STEP 9: Git commit (ENV004)."""
        import subprocess
        from ..engine.project import get_current_path
        
        current_path = get_current_path(self.project)
        
        # Ensure git is initialized
        git_dir = current_path / ".git"
        if not git_dir.exists():
            subprocess.run(["git", "-C", str(current_path), "init"], capture_output=True)
            gitignore = current_path / ".gitignore"
            if not gitignore.exists():
                gitignore.write_text("__pycache__/\n*.pyc\n.DS_Store\n")
        
        # Add all files
        subprocess.run(["git", "-C", str(current_path), "add", "-A"], capture_output=True)
        
        # Commit
        commit_msg = f"[{self.execution.todo_id}] {self.execution.todo_title[:50]} - v{self.execution.calculated_next_version}"
        result = subprocess.run(
            ["git", "-C", str(current_path), "commit", "-m", commit_msg],
            capture_output=True, text=True
        )
        
        if result.returncode != 0 and "nothing to commit" not in result.stdout:
            return False, None, f"Git commit failed: {result.stderr}"
        
        # Get commit SHA
        sha_result = subprocess.run(
            ["git", "-C", str(current_path), "rev-parse", "HEAD"],
            capture_output=True, text=True
        )
        
        if sha_result.returncode == 0:
            self.execution.commit_sha = sha_result.stdout.strip()
        
        # Create tag
        tag_name = f"v{self.execution.calculated_next_version}"
        subprocess.run(
            ["git", "-C", str(current_path), "tag", "-a", tag_name, "-m", commit_msg],
            capture_output=True
        )
        
        return True, {"commit_sha": self.execution.commit_sha, "tag": tag_name, "message": commit_msg}, None
    
    def _step_git_push(self) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """STEP 10: Push to GitHub (ENV009)."""
        import subprocess
        from ..engine.project import get_current_path
        
        current_path = get_current_path(self.project)
        
        # Check if remote exists
        result = subprocess.run(
            ["git", "-C", str(current_path), "remote", "-v"],
            capture_output=True, text=True
        )
        
        if "origin" not in result.stdout:
            # Add remote
            remote_url = f"https://github.com/{self.github_repo}.git"
            subprocess.run(
                ["git", "-C", str(current_path), "remote", "add", "origin", remote_url],
                capture_output=True
            )
        
        # Push with tags
        push_result = subprocess.run(
            ["git", "-C", str(current_path), "push", "-u", "origin", "main", "--follow-tags"],
            capture_output=True, text=True, timeout=60
        )
        
        if push_result.returncode != 0:
            # Try master branch
            push_result = subprocess.run(
                ["git", "-C", str(current_path), "push", "-u", "origin", "master", "--follow-tags"],
                capture_output=True, text=True, timeout=60
            )
        
        if push_result.returncode != 0:
            return False, None, f"ENV009: Git push failed - {push_result.stderr[:100]}"
        
        return True, {"pushed": True}, None
    
    def _step_create_github_release(self) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """STEP 11: Create GitHub release (ENV012)."""
        from ..connectors.github import create_github_release
        
        version = self.execution.calculated_next_version
        title = f"v{version} - {self.execution.todo_title[:50]}"
        body = f"""
## Changes
- [{self.execution.todo_id}] {self.execution.todo_title}

## Files Created
{chr(10).join('- ' + f for f in self.execution.files_created)}

## Commit
{self.execution.commit_sha or 'N/A'}
"""
        
        success = create_github_release(
            self.github_repo,
            version,
            title,
            body
        )
        
        if success:
            self.execution.release_url = f"https://github.com/{self.github_repo}/releases/tag/v{version}"
            return True, {"release_url": self.execution.release_url}, None
        else:
            return False, None, "ENV012: Failed to create GitHub release"
    
    def _step_verify_release(self) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """STEP 12: Verify release exists (ENV013)."""
        from ..connectors.github import fetch_github_version
        
        # Fetch version again to verify
        new_version = fetch_github_version(self.github_repo)
        
        if new_version == self.execution.calculated_next_version:
            self.execution.github_version_after = new_version
            return True, {"verified_version": new_version}, None
        else:
            return False, None, f"ENV013: Release verification failed - expected {self.execution.calculated_next_version}, got {new_version}"
    
    def _step_mark_todo_done(self) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """STEP 13: Mark TODO as completed."""
        from ..engine.tracking import get_todo, save_todo
        
        todos = get_todo(self.project)
        
        for todo in todos:
            if todo.get("id") == self.execution.todo_id:
                todo["done"] = True
                todo["status"] = "done"
                todo["completed"] = datetime.now().isoformat()
                todo["version"] = self.execution.calculated_next_version
                todo["files"] = self.execution.files_created
                todo["execution_id"] = self.execution.execution_id
                todo["release_url"] = self.execution.release_url
                break
        
        save_todo(self.project, todos)
        return True, {"marked_done": True}, None
    
    # ============================================================
    # LOGGING
    # ============================================================
    
    def _save_execution_log(self):
        """Save execution log to project directory."""
        from ..engine.project import PROJECTS_DIR
        
        log_dir = PROJECTS_DIR / self.project / "protocol_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"{self.execution.execution_id}.json"
        log_file.write_text(json.dumps(asdict(self.execution), indent=2, default=str))
        
        logger.info(f"📝 Execution log saved: {log_file}")


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def process_todo_with_protocol(
    project: str,
    github_repo: str,
    todo_id: str,
    todo_title: str,
    call_claude_fn: Callable,
    github_token: Optional[str] = None
) -> ProtocolExecution:
    """
    Process a single TODO with full protocol enforcement.
    
    Args:
        project: Project name
        github_repo: GitHub repo (owner/repo)
        todo_id: TODO ID (e.g., T001)
        todo_title: TODO description
        call_claude_fn: Function to call Claude API
        github_token: GitHub token for creating releases
    
    Returns:
        ProtocolExecution with complete tracking
    """
    executor = ProtocolExecutor(project, github_repo, github_token)
    executor.set_claude_function(call_claude_fn)
    return executor.execute_todo(todo_id, todo_title)
