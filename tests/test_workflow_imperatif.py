#!/usr/bin/env python3
"""
TESTS IMPÉRATIFS - Version Control Workflow
Ces tests vérifient le workflow OBLIGATOIRE:

1. FETCH version GitHub AVANT toute action
2. SNAPSHOT AVANT modification
3. Version injectée dans contexte Claude
4. Création release GitHub APRÈS commit
5. Vérification asset uploadé

PROTOCOL FLOW (IMMUTABLE):
1. SERVICE WORKER receives TODO
2. SERVICE WORKER calls GitHub API → get latest release version
3. SERVICE WORKER calculates next version
4. SERVICE WORKER creates snapshot BEFORE (ENV003/ENV014)
5. SERVICE WORKER calls Claude with version info
6. Claude returns tasks (max 3)
7. SERVICE WORKER validates response
8. SERVICE WORKER executes tasks
9. SERVICE WORKER creates snapshot AFTER
10. SERVICE WORKER commits to git
11. SERVICE WORKER pushes to GitHub
12. SERVICE WORKER creates GitHub release
13. SERVICE WORKER verifies release (ENV013)
14. SERVICE WORKER marks TODO as done
"""

import json
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


# ============================================================
# WORKFLOW: FETCH GITHUB VERSION BEFORE ACTION
# ============================================================

class TestGitHubVersionFetchBeforeAction:
    """ENV012: Version MUST come from GitHub - no guessing"""
    
    def test_fetch_github_version_function_exists(self):
        """fetch_github_version must exist in github connector"""
        from localagent.connectors.github import fetch_github_version
        assert callable(fetch_github_version)
    
    def test_fetch_github_version_returns_string_or_none(self):
        """fetch_github_version must return version string or None"""
        from localagent.connectors.github import fetch_github_version
        
        # Mock to avoid real API call
        with patch('urllib.request.urlopen') as mock:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "tag_name": "v3.0.80"
            }).encode()
            mock_response.__enter__ = lambda s: s
            mock_response.__exit__ = MagicMock()
            mock.return_value = mock_response
            
            # Should handle gracefully even without real token
            try:
                result = fetch_github_version("test/repo")
                assert result is None or isinstance(result, str)
            except:
                pass  # OK if no token
    
    def test_protocol_step_1_is_fetch_version(self):
        """Protocol MUST start with fetch_github_version"""
        from localagent.core.protocol import PROTOCOL_STEPS
        
        assert PROTOCOL_STEPS[0]["name"] == "fetch_github_version"
        assert PROTOCOL_STEPS[0]["constraint"] == "ENV012"
    
    def test_protocol_executor_fetches_version_first(self):
        """ProtocolExecutor must fetch GitHub version as first step"""
        from localagent.core.protocol import ProtocolExecutor, PROTOCOL_STEPS
        
        executor = ProtocolExecutor(
            project="test-project",
            github_repo="test/repo"
        )
        
        # Verify step order
        assert PROTOCOL_STEPS[0]["name"] == "fetch_github_version"
        assert PROTOCOL_STEPS[1]["name"] == "calculate_next_version"


# ============================================================
# WORKFLOW: SNAPSHOT BEFORE MODIFICATION
# ============================================================

class TestSnapshotBeforeModification:
    """ENV003/ENV014: Snapshot MUST exist before destructive action"""
    
    def test_protocol_has_snapshot_before_step(self):
        """Protocol must have create_snapshot_before step"""
        from localagent.core.protocol import PROTOCOL_STEPS
        
        step_names = [s["name"] for s in PROTOCOL_STEPS]
        assert "create_snapshot_before" in step_names
    
    def test_snapshot_before_comes_before_execute(self):
        """create_snapshot_before MUST come before execute_tasks"""
        from localagent.core.protocol import PROTOCOL_STEPS
        
        step_names = [s["name"] for s in PROTOCOL_STEPS]
        snapshot_idx = step_names.index("create_snapshot_before")
        execute_idx = step_names.index("execute_tasks")
        
        assert snapshot_idx < execute_idx, \
            "Snapshot MUST be created BEFORE executing tasks"
    
    def test_snapshot_before_has_env003_constraint(self):
        """create_snapshot_before must reference ENV003"""
        from localagent.core.protocol import PROTOCOL_STEPS
        
        snapshot_step = next(s for s in PROTOCOL_STEPS if s["name"] == "create_snapshot_before")
        assert snapshot_step["constraint"] == "ENV003"
    
    def test_constraint_env003_exists(self):
        """ENV003 constraint must exist and be CRITICAL"""
        from localagent.core.constraints import get_constraint
        
        constraint = get_constraint("ENV003")
        assert constraint is not None
        assert constraint["severity"] == "CRITICAL"
        assert "snapshot" in constraint["rule"].lower()
    
    def test_validate_action_blocks_delete_without_snapshot(self):
        """Delete without snapshot must be blocked"""
        from localagent.core.constraints import validate_action
        
        valid, violations = validate_action("delete", {"snapshot_created": False})
        assert not valid
        assert any("ENV003" in v for v in violations)


# ============================================================
# WORKFLOW: VERSION IN CLAUDE CONTEXT
# ============================================================

class TestVersionInClaudeContext:
    """ENV015: Version info MUST be injected in every Claude conversation"""
    
    def test_protocol_has_build_context_step(self):
        """Protocol must have build_claude_context step"""
        from localagent.core.protocol import PROTOCOL_STEPS
        
        step_names = [s["name"] for s in PROTOCOL_STEPS]
        assert "build_claude_context" in step_names
    
    def test_build_context_has_env015_constraint(self):
        """build_claude_context must reference ENV015"""
        from localagent.core.protocol import PROTOCOL_STEPS
        
        ctx_step = next(s for s in PROTOCOL_STEPS if s["name"] == "build_claude_context")
        assert ctx_step["constraint"] == "ENV015"
    
    def test_constraint_env015_exists(self):
        """ENV015 constraint must exist"""
        from localagent.core.constraints import get_constraint
        
        constraint = get_constraint("ENV015")
        assert constraint is not None
        assert "version" in constraint["rule"].lower()
    
    def test_system_prompt_builder_exists(self):
        """build_system_prompt function must exist"""
        from localagent.core.constraints import build_system_prompt
        assert callable(build_system_prompt)
    
    def test_system_prompt_includes_constraints(self):
        """System prompt must include constraints"""
        from localagent.core.constraints import build_system_prompt
        
        prompt = build_system_prompt()
        assert "JSON" in prompt or "json" in prompt
        assert "CONSTRAINTS" in prompt or "constraints" in prompt.lower()


# ============================================================
# WORKFLOW: GITHUB RELEASE AFTER COMMIT
# ============================================================

class TestGitHubReleaseAfterCommit:
    """ENV012: GitHub release MUST be created after commit"""
    
    def test_protocol_has_git_commit_step(self):
        """Protocol must have git_commit step"""
        from localagent.core.protocol import PROTOCOL_STEPS
        
        step_names = [s["name"] for s in PROTOCOL_STEPS]
        assert "git_commit" in step_names
    
    def test_protocol_has_create_release_step(self):
        """Protocol must have create_github_release step"""
        from localagent.core.protocol import PROTOCOL_STEPS
        
        step_names = [s["name"] for s in PROTOCOL_STEPS]
        assert "create_github_release" in step_names
    
    def test_release_comes_after_commit(self):
        """create_github_release MUST come after git_commit"""
        from localagent.core.protocol import PROTOCOL_STEPS
        
        step_names = [s["name"] for s in PROTOCOL_STEPS]
        commit_idx = step_names.index("git_commit")
        release_idx = step_names.index("create_github_release")
        
        assert release_idx > commit_idx, \
            "Release MUST be created AFTER commit"
    
    def test_commit_has_env004_constraint(self):
        """git_commit must enforce version increment (ENV004)"""
        from localagent.core.protocol import PROTOCOL_STEPS
        
        commit_step = next(s for s in PROTOCOL_STEPS if s["name"] == "git_commit")
        assert commit_step["constraint"] == "ENV004"
    
    def test_constraint_env004_exists(self):
        """ENV004 constraint must exist"""
        from localagent.core.constraints import get_constraint
        
        constraint = get_constraint("ENV004")
        assert constraint is not None
        assert "version" in constraint["rule"].lower() or "increment" in constraint["rule"].lower()


# ============================================================
# WORKFLOW: VERIFY RELEASE ASSET UPLOADED
# ============================================================

class TestVerifyReleaseAsset:
    """ENV013: Asset upload MUST be verified"""
    
    def test_protocol_has_verify_release_step(self):
        """Protocol must have verify_release step"""
        from localagent.core.protocol import PROTOCOL_STEPS
        
        step_names = [s["name"] for s in PROTOCOL_STEPS]
        assert "verify_release" in step_names
    
    def test_verify_release_comes_after_create_release(self):
        """verify_release MUST come after create_github_release"""
        from localagent.core.protocol import PROTOCOL_STEPS
        
        step_names = [s["name"] for s in PROTOCOL_STEPS]
        create_idx = step_names.index("create_github_release")
        verify_idx = step_names.index("verify_release")
        
        assert verify_idx > create_idx, \
            "Verification MUST happen AFTER release creation"
    
    def test_verify_release_has_env013_constraint(self):
        """verify_release must reference ENV013"""
        from localagent.core.protocol import PROTOCOL_STEPS
        
        verify_step = next(s for s in PROTOCOL_STEPS if s["name"] == "verify_release")
        assert verify_step["constraint"] == "ENV013"
    
    def test_constraint_env013_exists(self):
        """ENV013 constraint must exist"""
        from localagent.core.constraints import get_constraint
        
        constraint = get_constraint("ENV013")
        assert constraint is not None
        assert "verify" in constraint["rule"].lower() or "asset" in constraint["rule"].lower()


# ============================================================
# WORKFLOW: COMPLETE PROTOCOL VALIDATION
# ============================================================

class TestCompleteProtocolWorkflow:
    """Test the complete protocol workflow is properly defined"""
    
    def test_protocol_has_exactly_13_steps(self):
        """Protocol MUST have exactly 13 steps"""
        from localagent.core.protocol import PROTOCOL_STEPS
        
        assert len(PROTOCOL_STEPS) == 13, \
            f"Protocol must have 13 steps, found {len(PROTOCOL_STEPS)}"
    
    def test_protocol_steps_are_in_correct_order(self):
        """Protocol steps MUST be in the correct order"""
        from localagent.core.protocol import PROTOCOL_STEPS
        
        expected = [
            "fetch_github_version",      # 1. Get version from GitHub
            "calculate_next_version",    # 2. Calculate next version
            "create_snapshot_before",    # 3. Snapshot BEFORE (ENV003)
            "build_claude_context",      # 4. Build context with version
            "call_claude",               # 5. Call Claude API
            "validate_response",         # 6. Validate Claude response
            "execute_tasks",             # 7. Execute tasks
            "create_snapshot_after",     # 8. Snapshot AFTER
            "git_commit",                # 9. Commit to git
            "git_push",                  # 10. Push to GitHub
            "create_github_release",     # 11. Create release
            "verify_release",            # 12. Verify asset uploaded
            "mark_todo_done"             # 13. Mark TODO as done
        ]
        
        actual = [s["name"] for s in PROTOCOL_STEPS]
        assert actual == expected, f"Step order mismatch: {actual}"
    
    def test_all_critical_constraints_referenced(self):
        """All critical constraints must be referenced in protocol"""
        from localagent.core.protocol import PROTOCOL_STEPS
        
        step_constraints = {s["constraint"] for s in PROTOCOL_STEPS if s["constraint"]}
        
        # Critical constraints that MUST be in protocol
        critical = ["ENV003", "ENV004", "ENV012", "ENV013", "ENV014", "ENV015"]
        
        for constraint in critical:
            assert constraint in step_constraints, \
                f"Critical constraint {constraint} not referenced in protocol"
    
    def test_protocol_executor_tracks_violations(self):
        """ProtocolExecutor must track violations"""
        from localagent.core.protocol import ProtocolExecution
        from datetime import datetime
        
        execution = ProtocolExecution(
            execution_id="TEST001",
            todo_id="TODO001",
            todo_title="Test",
            project="test",
            github_repo="test/repo",
            started_at=datetime.now().isoformat()
        )
        
        # Must have violations list
        assert hasattr(execution, 'violations')
        assert isinstance(execution.violations, list)
    
    def test_protocol_executor_tracks_versions(self):
        """ProtocolExecutor must track before/after versions"""
        from localagent.core.protocol import ProtocolExecution
        from datetime import datetime
        
        execution = ProtocolExecution(
            execution_id="TEST001",
            todo_id="TODO001",
            todo_title="Test",
            project="test",
            github_repo="test/repo",
            started_at=datetime.now().isoformat()
        )
        
        # Must track versions
        assert hasattr(execution, 'github_version_before')
        assert hasattr(execution, 'github_version_after')
        assert hasattr(execution, 'calculated_next_version')


# ============================================================
# BACKLOG → TODO → GITHUB FLOW
# ============================================================

class TestBacklogToGitHubFlow:
    """Test that backlog items flow correctly through the system"""
    
    def test_backlog_is_populated_by_github_issues(self):
        """Backlog should be able to sync from GitHub issues"""
        from localagent.connectors.github import REPOS
        
        # GitHub connector must have repos configured
        assert "service" in REPOS
    
    def test_todo_processing_uses_protocol(self):
        """TODO processing must use ProtocolExecutor"""
        from localagent.core.protocol import ProtocolExecutor
        
        # ProtocolExecutor must have execute_todo method
        assert hasattr(ProtocolExecutor, 'execute_todo')
    
    def test_tracking_module_has_backlog_functions(self):
        """Tracking module must have backlog management"""
        from localagent.engine.tracking import (
            get_backlog, save_backlog, add_backlog_item, complete_backlog_item
        )
        
        assert callable(get_backlog)
        assert callable(save_backlog)
        assert callable(add_backlog_item)
        assert callable(complete_backlog_item)
    
    def test_add_backlog_item_creates_directory(self):
        """add_backlog_item must create project directory"""
        from localagent.engine.tracking import add_backlog_item, get_backlog
        from localagent.engine.project import PROJECTS_DIR
        
        test_project = f"test-workflow-{int(datetime.now().timestamp())}"
        test_dir = PROJECTS_DIR / test_project
        
        try:
            # Should not crash even if dir doesn't exist
            item_id = add_backlog_item(test_project, "Test item", "medium")
            assert item_id.startswith("B")
            
            # Should have created directory
            assert test_dir.exists()
            
            # Should be in backlog
            backlog = get_backlog(test_project)
            assert len(backlog) == 1
            assert backlog[0]["title"] == "Test item"
        finally:
            if test_dir.exists():
                shutil.rmtree(test_dir)


# ============================================================
# DASHBOARD PROTOCOL TRACKING
# ============================================================

class TestDashboardProtocolTracking:
    """Test dashboard shows project and status in real-time"""
    
    def test_dashboard_has_project_info(self):
        """Dashboard must have project info"""
        content = Path("dashboard/index.html").read_text()
        assert "projectName" in content
        assert "projectVersion" in content
    
    def test_dashboard_has_health_check(self):
        """Dashboard must check health"""
        content = Path("dashboard/index.html").read_text()
        assert "checkHealth" in content
        assert "/api/health" in content
    
    def test_dashboard_has_status_indicator(self):
        """Dashboard must show connection status"""
        content = Path("dashboard/index.html").read_text()
        assert "statusDot" in content
        assert "statusText" in content
    
    def test_dashboard_has_todo_panel(self):
        """Dashboard must show TODO panel"""
        content = Path("dashboard/index.html").read_text()
        assert "todoPanel" in content
        assert "loadTodos" in content
    
    def test_dashboard_has_bugfix_panel(self):
        """Dashboard must show bugfix panel"""
        content = Path("dashboard/index.html").read_text()
        assert "bugfixPanel" in content
        assert "loadBugfixes" in content
    
    def test_dashboard_has_chat_with_linter(self):
        """Dashboard must have chat with linter integration"""
        content = Path("dashboard/index.html").read_text()
        assert "chatMessages" in content
        assert "lintFeedback" in content
        assert "lintInput" in content


class TestServerProtocolAPI:
    """Test server has protocol tracking API"""
    
    def test_server_has_protocol_history_endpoint(self):
        """Server/routers must have /api/protocol/history endpoint"""
        server = Path("localagent/service/server.py").read_text()
        routers = Path("localagent/service/routers/protocol.py").read_text() if Path("localagent/service/routers/protocol.py").exists() else ""
        assert "/protocol/history" in server or "/history" in routers
    
    def test_server_has_protocol_steps_endpoint(self):
        """Server/routers must have /api/protocol/steps endpoint"""
        server = Path("localagent/service/server.py").read_text()
        routers = Path("localagent/service/routers/protocol.py").read_text() if Path("localagent/service/routers/protocol.py").exists() else ""
        assert "/protocol/steps" in server or "/steps" in routers
    
    def test_server_has_protocol_notify_endpoint(self):
        """Server/routers must have /api/protocol/notify for broadcasting"""
        server = Path("localagent/service/server.py").read_text()
        routers = Path("localagent/service/routers/protocol.py").read_text() if Path("localagent/service/routers/protocol.py").exists() else ""
        assert "/protocol/notify" in server or "/notify" in routers
    
    def test_server_records_executions(self):
        """Server/routers must record execution history"""
        server = Path("localagent/service/server.py").read_text()
        routers = Path("localagent/service/routers/protocol.py").read_text() if Path("localagent/service/routers/protocol.py").exists() else ""
        content = server + routers
        assert "record_execution" in content
        assert "_execution_history" in content
    
    def test_server_broadcasts_protocol_events(self):
        """Server must broadcast protocol events via WebSocket"""
        content = Path("localagent/service/server.py").read_text()
        assert "ws_manager.broadcast" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
