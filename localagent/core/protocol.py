"""
LocalAgent - CORE: Protocol Enforcement
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
    
    def set_instruction(self, instruction: str):
        """Set the instruction for task mismatch validation."""
        self._instruction = instruction
        
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
        
        # Initialize retry counter
        self._retry_count = 0
        
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
        """STEP 4: Build context for Claude with version info, case context, and skills (ENV015)."""
        from .constraints import build_system_prompt
        from .case_context import get_case_context_manager, get_skill_context
        import re
        
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
        
        # Check if instruction mentions specific file to modify
        target_file_context = ""
        instruction = getattr(self, '_instruction', '') or self.execution.todo_title
        mentioned_files = re.findall(r'[\w/\-_.]+\.(?:py|js|ts|html|css|json|md)', instruction)
        modify_keywords = ['modify', 'update', 'fix', 'edit', 'change', 'patch', 'correct', 'in ']
        is_modify_instruction = any(kw in instruction.lower() for kw in modify_keywords) and mentioned_files
        
        if is_modify_instruction and mentioned_files:
            target_file = mentioned_files[0]
            self._target_file = target_file  # Store for validation
            
            # Fetch current file content from GitHub
            try:
                from ..connectors.github import github_get_file_content
                owner, repo = self.github_repo.split('/')
                file_content = github_get_file_content(owner, repo, target_file)
                
                if file_content:
                    target_file_context = f"""
=== TARGET FILE TO MODIFY ===
File: {target_file}
IMPORTANT: You must return a task that modifies THIS EXACT FILE.
DO NOT create new files in Txxx/ folders.
DO NOT create test files.
Return the COMPLETE modified file content.

Current content:
```
{file_content[:5000]}
```
"""
                    logger.info(f"   📄 Fetched target file: {target_file} ({len(file_content)} bytes)")
            except Exception as e:
                logger.warning(f"Could not fetch target file {target_file}: {e}")
        
        # Add Case Context if available
        case_context = ""
        try:
            ctx_manager = get_case_context_manager()
            ctx = ctx_manager.get_context()
            if ctx.case_id:
                skill_ctx = ctx_manager.get_skill_context()
                case_context = f"""
=== CASE CONTEXT ===
Case ID: {ctx.case_id}
Case Name: {ctx.case_name}
Framework: {ctx.framework}
Methodology: {ctx.methodology}
Jurisdiction: {ctx.jurisdiction}
Contract Type: {ctx.contract_type}
Dispute Type: {ctx.dispute_type}
Forum: {ctx.forum}

Derived Context:
- US Federal: {skill_ctx.get('is_us_federal', False)}
- UK: {skill_ctx.get('is_uk', False)}
- Uses AACE: {skill_ctx.get('uses_aace', False)}
- Uses SCL: {skill_ctx.get('uses_scl', False)}
- Delay Case: {skill_ctx.get('is_delay_case', False)}
- Quantum Case: {skill_ctx.get('is_quantum_case', False)}
"""
        except Exception as e:
            logger.warning(f"Could not load case context: {e}")
        
        # Match and inject relevant skills
        skill_context = ""
        matched_skills = []
        try:
            matched_skills = self._match_skills_for_todo(self.execution.todo_title)
            if matched_skills:
                skill_context = "\n=== MATCHED SKILLS ===\n"
                for match in matched_skills[:3]:  # Top 3 skills
                    skill_context += f"\n### Skill: {match['skill']} (score: {match['score']})\n"
                    skill_context += f"Matched triggers: {', '.join([t['trigger'] if isinstance(t, dict) else t for t in match.get('matchedTriggers', [])[:5]])}\n"
                    
                    # Get skill template if available
                    template = self._get_skill_template(match['skill'], self.execution.todo_title)
                    if template:
                        skill_context += f"\nRecommended template:\n```\n{template[:1000]}\n```\n"
        except Exception as e:
            logger.warning(f"Could not match skills: {e}")
        
        full_prompt = system_prompt + "\n" + version_context + target_file_context + case_context + skill_context
        
        # Build user message
        user_message = f"""
TODO: {self.execution.todo_title}

Generate the necessary files for this TODO.
Remember: Max 3 tasks, each task max 50 lines.
Response must be valid JSON only.
"""
        
        self._claude_context = {
            "system": full_prompt,
            "user": user_message,
            "case_context": case_context,
            "matched_skills": matched_skills
        }
        
        return True, {
            "system_length": len(full_prompt), 
            "user_length": len(user_message),
            "case_context_injected": bool(case_context),
            "skills_matched": len(matched_skills)
        }, None
    
    def _match_skills_for_todo(self, todo_title: str) -> List[Dict]:
        """Match skills based on TODO title."""
        from ..skills import get_manager
        
        manager = get_manager()
        manager.discover()
        
        text_lower = todo_title.lower()
        matches = []
        
        # Weight constants
        WEIGHTS = {"core": 20, "strong": 10, "weak": 3}
        
        for skill in manager.get_available():
            score = 0
            matched_triggers = []
            
            # Parse triggers from description
            desc = skill.description or ""
            
            for category in ["core", "strong", "weak"]:
                import re
                pattern = f"Triggers-{category.capitalize()}:\\s*([^\\n]+(?:\\n(?![A-Z][a-z]*[-:])[^\\n]+)*)"
                match = re.search(pattern, desc, re.IGNORECASE)
                if match:
                    triggers_text = match.group(1).replace("\n", " ")
                    triggers = [t.strip().lower() for t in triggers_text.split(",") if t.strip()]
                    
                    for trigger in triggers:
                        if len(trigger) > 1:
                            # Check if trigger is in todo title
                            escaped = re.escape(trigger).replace(r"\ ", r"\s*")
                            if re.search(r"\b" + escaped + r"\b", text_lower, re.IGNORECASE):
                                score += WEIGHTS.get(category, 3)
                                matched_triggers.append({"trigger": trigger, "category": category})
            
            if score > 0:
                matches.append({
                    "skill": skill.name,
                    "score": score,
                    "matchedTriggers": matched_triggers
                })
        
        # Sort by score descending
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches
    
    def _get_skill_template(self, skill_name: str, todo_title: str) -> Optional[str]:
        """Get the best matching template from a skill."""
        from ..skills import get_manager
        from .case_context import get_skill_context
        
        manager = get_manager()
        skill = manager.get_skill(skill_name)
        
        if not skill or not skill.body:
            return None
        
        # Parse rewrites from skill body
        import re
        section_match = re.search(r"## Prompt Rewrites\s*\n([\s\S]*?)(?=\n## [A-Za-z]|$)", skill.body, re.IGNORECASE)
        if not section_match:
            return None
        
        content = section_match.group(1)
        
        # Find best matching template
        block_regex = r"###\s+([^\n]+)\n```(?:[^\n]*)?\n([\s\S]*?)```"
        text_lower = todo_title.lower()
        best_template = None
        best_score = 0
        
        for match in re.finditer(block_regex, content):
            pattern_line = match.group(1).strip()
            template = match.group(2).strip()
            
            # Check if any pattern matches
            patterns = [p.strip().lower() for p in pattern_line.split("|")]
            score = 0
            for pattern in patterns:
                if pattern and len(pattern) > 1:
                    escaped = re.escape(pattern).replace(r"\ ", r"\s*")
                    if re.search(r"\b" + escaped + r"\b", text_lower, re.IGNORECASE):
                        score += len(pattern)
            
            if score > best_score:
                best_score = score
                best_template = template
        
        # Apply case context to template
        if best_template:
            try:
                ctx = get_skill_context()
                best_template = self._apply_context_to_template(best_template, ctx)
            except Exception as e:
                # Log error but continue with unmodified template (graceful fallback)
                logger.warning(f"Failed to apply skill context to template: {e}")

        return best_template
    
    def _apply_context_to_template(self, template: str, context: Dict) -> str:
        """Apply case context variables to template."""
        import re
        
        result = template
        
        # Handle conditionals: {{#if condition}}content{{/if}}
        def replace_conditional(match):
            condition = match.group(1)
            content = match.group(2)
            if context.get(condition):
                return content
            return ""
        
        result = re.sub(r"\{\{#if\s+(\w+)\}\}([\s\S]*?)\{\{/if\}\}", replace_conditional, result)
        
        # Handle variables: {{variable}}
        def replace_variable(match):
            var_name = match.group(1)
            return str(context.get(var_name, match.group(0)))
        
        result = re.sub(r"\{\{(\w+)\}\}", replace_variable, result)
        
        # Clean up empty lines
        result = re.sub(r"\n\s*\n\s*\n", "\n\n", result)
        
        return result
    
    def _retry_with_feedback(self, feedback: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Retry Claude call with constraint feedback."""
        logger.info(f"   🔄 Retry {self._retry_count}/3 with feedback: {feedback[:50]}...")
        
        # Add feedback to context
        self._claude_context["user"] = f"{feedback}\n\nOriginal request: {self._claude_context['user']}"
        
        # Re-call Claude
        success, data, error = self._step_call_claude()
        if not success:
            return False, data, error
        
        # Re-validate (recursive call will continue validation)
        return self._step_validate_response()
    
    def _step_call_claude(self) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """STEP 5: Call Claude API (CTX001)."""
        if not self._call_claude_fn:
            return False, None, "No Claude function configured"
        
        if not hasattr(self, '_claude_context'):
            return False, None, "No context built - run build_claude_context first"
        
        try:
            # call_claude signature: (prompt, context="", system=None)
            # Pass case_context if available for additional context
            context = self._claude_context.get("case_context", "") or ""

            result = self._call_claude_fn(
                self._claude_context["user"],
                context,
                self._claude_context["system"]
            )
            
            # Handle dict response from call_claude
            if isinstance(result, dict):
                if not result.get("success"):
                    return False, None, f"Claude API error: {result.get('error', 'Unknown')}"
                response = result.get("response", "")
            else:
                response = result
            
            self._claude_response = response
            return True, {"response_length": len(response) if response else 0}, None
            
        except Exception as e:
            return False, None, f"Claude API error: {str(e)}"
    
    def _step_validate_response(self) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """STEP 6: Validate Claude response (CTX003). Uses negotiator strategies for retry."""
        from .negotiator import NEGOTIATION_STRATEGIES
        
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
            # Use negotiator strategy for parse_error
            strategy = NEGOTIATION_STRATEGIES.get("parse_error", {})
            if self._retry_count < strategy.get("max_retries", 3):
                self._retry_count += 1
                feedback = strategy.get("feedback", "Invalid JSON")
                return self._retry_with_feedback(feedback)
            return False, None, f"CTX001: Invalid JSON after {self._retry_count} retries - {str(e)}"
        
        # Check tasks
        tasks = data.get("tasks", [])
        
        if not tasks:
            # Use negotiator strategy for no_tasks
            strategy = NEGOTIATION_STRATEGIES.get("no_tasks", {})
            if self._retry_count < strategy.get("max_retries", 2):
                self._retry_count += 1
                feedback = strategy.get("feedback", "No tasks found")
                return self._retry_with_feedback(feedback)
            return False, None, f"No tasks in response after {self._retry_count} retries"
        
        # CTX003: Max 3 tasks
        if len(tasks) > 3:
            # Use negotiator strategy for truncation (reduce complexity)
            strategy = NEGOTIATION_STRATEGIES.get("truncation", {})
            if self._retry_count < strategy.get("max_retries", 3):
                self._retry_count += 1
                feedback = f"CTX003 VIOLATION: {len(tasks)} tasks returned but max is 3. {strategy.get('feedback', '')}"
                return self._retry_with_feedback(feedback)
            return False, None, f"CTX003: Too many tasks ({len(tasks)} > 3) after {self._retry_count} retries"
        
        # CTX004: Max 150 lines per task
        for task in tasks:
            content = task.get("content", "")
            lines = content.count("\n") + 1
            if lines > 150:
                # Use negotiator strategy for truncation
                strategy = NEGOTIATION_STRATEGIES.get("truncation", {})
                if self._retry_count < strategy.get("max_retries", 3):
                    self._retry_count += 1
                    feedback = f"CTX004 VIOLATION: Task {task.get('id', '?')} has {lines} lines but max is 150. {strategy.get('feedback', '')}"
                    return self._retry_with_feedback(feedback)
                return False, None, f"CTX004: Task {task.get('id', '?')} exceeds 150 lines ({lines}) after {self._retry_count} retries"
        
        self._validated_tasks = tasks
        
        # Task mismatch validation - check if tasks match instruction
        from .negotiator import validate_tasks_match_instruction, NEGOTIATION_STRATEGIES
        instruction = getattr(self, '_instruction', '') or self.execution.todo_title
        target_file = getattr(self, '_target_file', None)
        
        mismatch_result = validate_tasks_match_instruction(tasks, instruction, target_file)
        
        if not mismatch_result.get("valid"):
            strategy = NEGOTIATION_STRATEGIES.get("task_mismatch", {})
            max_retries = strategy.get("max_retries", 3)

            # Check if max retries exceeded BEFORE attempting another retry
            if self._retry_count >= max_retries:
                return False, None, f"Task mismatch after {self._retry_count} retries (max: {max_retries}): {mismatch_result.get('detail', '')}"

            self._retry_count += 1
            feedback = mismatch_result.get("detail", strategy.get("feedback", "Task does not match instruction"))
            logger.warning(f"   ❌ Task mismatch (retry {self._retry_count}/{max_retries}): {feedback[:100]}")
            return self._retry_with_feedback(feedback)
        
        return True, {"task_count": len(tasks), "tasks": [t.get("id") for t in tasks]}, None
    
    def _step_execute_tasks(self) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """STEP 7: Execute validated tasks (CTX004)."""
        from ..engine.project import get_current_path
        from ..engine.tracking import register_output_file
        
        if not hasattr(self, '_validated_tasks'):
            return False, None, "No validated tasks to execute"
        
        tasks = self._validated_tasks
        current_path = get_current_path(self.project)
        target_file = getattr(self, '_target_file', None)
        
        # Determine if this is a file modification (write to project root) or new file creation (write to Txxx/)
        is_modification = target_file is not None
        
        if is_modification:
            # For modifications, write directly to project root
            base_path = current_path
            logger.info(f"      📝 Modification mode: writing to project root")
        else:
            # For new files, create TODO folder
            todo_folder = current_path / self.execution.todo_id
            todo_folder.mkdir(parents=True, exist_ok=True)
            base_path = todo_folder
        
        files_created = []
        
        for task in tasks:
            task_type = task.get("type", "")
            
            if task_type in ("create_file", "modify_file", "file", "update_file"):
                filename = task.get("filename") or task.get("file_path") or task.get("file") or task.get("path")
                content = task.get("content", "")
                
                if filename and content:
                    # For modification, use exact target path; otherwise use task filename
                    if is_modification and target_file:
                        # Check if this task is for the target file
                        if filename.endswith(target_file.split('/')[-1]) or filename == target_file:
                            file_path = current_path / target_file
                        else:
                            # Non-target file, put in Txxx/
                            todo_folder = current_path / self.execution.todo_id
                            todo_folder.mkdir(parents=True, exist_ok=True)
                            file_path = todo_folder / filename
                    else:
                        file_path = base_path / filename
                    
                    # Create parent directories if needed
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content)
                    
                    # Register in outputs
                    rel_path = str(file_path.relative_to(current_path))
                    register_output_file(self.project, rel_path, content)
                    files_created.append(rel_path)
                    
                    logger.info(f"      📄 {'Modified' if is_modification else 'Created'}: {rel_path}")
        
        self.execution.files_created = files_created
        return True, {"files_created": files_created, "base_path": str(base_path)}, None
    
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
        
        # Get current branch name
        branch_result = subprocess.run(
            ["git", "-C", str(current_path), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True
        )
        current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "main"
        
        # If no branch, create main
        if not current_branch or current_branch == "HEAD":
            subprocess.run(
                ["git", "-C", str(current_path), "checkout", "-b", "main"],
                capture_output=True
            )
            current_branch = "main"
        
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
        
        # Push current branch with tags
        # First, try to pull any remote changes
        pull_result = subprocess.run(
            ["git", "-C", str(current_path), "pull", "--rebase", "origin", current_branch],
            capture_output=True, text=True, timeout=60
        )
        # Ignore pull errors (e.g., if remote branch doesn't exist yet)
        
        push_result = subprocess.run(
            ["git", "-C", str(current_path), "push", "-u", "origin", current_branch, "--follow-tags"],
            capture_output=True, text=True, timeout=60
        )
        
        # Check for actual errors (not just info messages)
        # Git often puts progress/info in stderr even on success
        is_error = push_result.returncode != 0
        has_fatal = "fatal:" in push_result.stderr.lower() or "error:" in push_result.stderr.lower()
        has_rejected = "rejected" in push_result.stderr.lower()
        
        if is_error and (has_fatal or has_rejected):
            return False, None, f"ENV009: Git push failed - {push_result.stderr[:100]}"
        
        return True, {"pushed": True, "branch": current_branch}, None
    
    def _step_create_github_release(self) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """STEP 11: Create GitHub release (ENV012)."""
        from ..connectors.github import github_create_release
        
        version = self.execution.calculated_next_version
        body = f"""## Changes
- [{self.execution.todo_id}] {self.execution.todo_title}

## Files Created
{chr(10).join('- ' + f for f in self.execution.files_created)}

## Commit
{self.execution.commit_sha or 'N/A'}
"""
        
        # Try to create release, handle "already exists" by incrementing version
        max_attempts = 5
        for attempt in range(max_attempts):
            result = github_create_release("service", version, body, repo=self.github_repo)
            
            if result.get("success"):
                self.execution.release_url = result.get("url", f"https://github.com/{self.github_repo}/releases/tag/v{version}")
                self.execution.calculated_next_version = version  # Update if we had to increment
                return True, {"release_url": self.execution.release_url, "version": version}, None
            elif "already exists" in result.get("error", "").lower():
                # Increment version and retry
                parts = version.split(".")
                parts[-1] = str(int(parts[-1]) + 1)
                version = ".".join(parts)
                logger.info(f"      Release exists, trying v{version}")
            else:
                return False, None, f"ENV012: Failed to create GitHub release - {result.get('error', 'unknown')}"
        
        return False, None, f"ENV012: Failed to create GitHub release after {max_attempts} attempts"
    
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
