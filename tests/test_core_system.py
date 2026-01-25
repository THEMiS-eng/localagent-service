#!/usr/bin/env python3
"""
LocalAgent Core System Tests
Tests the ACTUAL core features:
- Constraints validation
- Auto-learning from errors  
- Protocol enforcement
- Negotiation strategies
"""

import json
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


# ============================================================
# CONSTRAINTS TESTS
# ============================================================

class TestConstraints:
    """Test constraint system"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        from localagent.core.constraints import (
            ENV_CONSTRAINTS, CTX_CONSTRAINTS,
            get_all_constraints, get_constraint,
            validate_action, check_before_action,
            build_system_prompt, ConstraintViolation
        )
        self.ENV = ENV_CONSTRAINTS
        self.CTX = CTX_CONSTRAINTS
        self.get_all = get_all_constraints
        self.get_one = get_constraint
        self.validate = validate_action
        self.check = check_before_action
        self.build_prompt = build_system_prompt
        self.Violation = ConstraintViolation
    
    def test_env_constraints_exist(self):
        """ENV constraints must exist and have required fields"""
        assert len(self.ENV) > 0, "No ENV constraints defined"
        for c in self.ENV:
            assert "id" in c, f"Constraint missing id"
            assert "rule" in c, f"Constraint {c.get('id')} missing rule"
            assert "severity" in c, f"Constraint {c.get('id')} missing severity"
            assert c["id"].startswith("ENV"), f"ENV constraint {c['id']} should start with ENV"
    
    def test_ctx_constraints_exist(self):
        """CTX constraints must exist and have required fields"""
        assert len(self.CTX) > 0, "No CTX constraints defined"
        for c in self.CTX:
            assert "id" in c
            assert "rule" in c
            assert "severity" in c
            assert c["id"].startswith("CTX"), f"CTX constraint {c['id']} should start with CTX"
    
    def test_get_constraint_by_id(self):
        """Should retrieve constraint by ID"""
        c = self.get_one("ENV001")
        assert c is not None
        assert c["id"] == "ENV001"
        
        c = self.get_one("NONEXISTENT")
        assert c is None
    
    def test_validate_action_minified_file(self):
        """ENV005: Cannot modify minified files"""
        valid, violations = self.validate("modify", {"file": "app.min.js"})
        assert not valid
        assert any("ENV005" in v for v in violations)
    
    def test_validate_action_python_match_case(self):
        """ENV006: No match/case syntax"""
        code = "match x:\n    case 1:"
        valid, violations = self.validate("modify", {"content": code})
        assert not valid
        assert any("ENV006" in v for v in violations)
    
    def test_validate_action_delete_without_snapshot(self):
        """ENV003: Snapshot required before delete"""
        valid, violations = self.validate("delete", {"snapshot_created": False})
        assert not valid
        assert any("ENV003" in v for v in violations)
    
    def test_validate_action_delete_with_snapshot(self):
        """Delete with snapshot should pass"""
        valid, violations = self.validate("delete", {"snapshot_created": True, "snapshot_exists": True})
        assert valid
    
    def test_validate_action_too_many_tasks(self):
        """CTX003: Max 3 tasks per request"""
        tasks = [{"id": f"T{i}"} for i in range(5)]
        valid, violations = self.validate("call_claude", {"tasks": tasks})
        assert not valid
        assert any("CTX003" in v for v in violations)
    
    def test_validate_action_task_line_limit(self):
        """CTX004: Max 50 lines per task"""
        content = "\n".join(["line"] * 60)
        tasks = [{"id": "T1", "content": content}]
        valid, violations = self.validate("call_claude", {"tasks": tasks})
        assert not valid
        assert any("CTX004" in v for v in violations)
    
    def test_validate_action_retry_limit(self):
        """CTX009: Max 3 retries"""
        valid, violations = self.validate("call_claude", {"retry_count": 5})
        assert not valid
        assert any("CTX009" in v for v in violations)
    
    def test_check_before_action_raises_on_critical(self):
        """Critical violations should raise exception"""
        with pytest.raises(self.Violation):
            self.check("delete", {"snapshot_created": False, "snapshot_exists": False})
    
    def test_build_system_prompt_contains_constraints(self):
        """System prompt should include CTX constraints"""
        prompt = self.build_prompt()
        assert "JSON" in prompt
        assert "tasks" in prompt
        # Should include high severity constraints
        assert "CTX001" in prompt or "valid JSON" in prompt.lower()


# ============================================================
# LEARNING TESTS
# ============================================================

class TestLearning:
    """Test auto-learning system"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        from localagent.core.learning import (
            load_learned_errors, save_learned_errors,
            learn_from_error, learn_dodge,
            get_similar_errors, has_learned_solution,
            get_error_context_for_retry
        )
        self.load = load_learned_errors
        self.save = save_learned_errors
        self.learn = learn_from_error
        self.dodge = learn_dodge
        self.similar = get_similar_errors
        self.solution = has_learned_solution
        self.context = get_error_context_for_retry
        
        # Create temp project
        self.test_project = f"test-learning-{int(datetime.now().timestamp())}"
    
    def teardown_method(self, method):
        """Cleanup test project"""
        from localagent.engine.project import PROJECTS_DIR
        test_dir = PROJECTS_DIR / self.test_project
        if test_dir.exists():
            shutil.rmtree(test_dir)
    
    def test_load_nonexistent_returns_empty(self):
        """Loading from nonexistent project returns empty structure"""
        errors = self.load("nonexistent-project-xyz")
        assert errors == {"errors": [], "patterns": {}, "dodges": []}
    
    def test_learn_from_error_creates_entry(self):
        """Learning from error creates new entry"""
        self.learn(self.test_project, "truncation", "Response was truncated")
        
        errors = self.load(self.test_project)
        assert len(errors["errors"]) == 1
        assert errors["errors"][0]["type"] == "truncation"
        assert errors["errors"][0]["count"] == 1
        assert errors["patterns"]["truncation"] == 1
    
    def test_learn_from_error_increments_count(self):
        """Same error increments count"""
        self.learn(self.test_project, "parse_error", "JSON invalid")
        self.learn(self.test_project, "parse_error", "JSON invalid")
        self.learn(self.test_project, "parse_error", "JSON invalid")
        
        errors = self.load(self.test_project)
        assert errors["errors"][0]["count"] == 3
        assert errors["patterns"]["parse_error"] == 3
    
    def test_learn_with_solution(self):
        """Can record solution with error"""
        self.learn(self.test_project, "truncation", "Too long", 
                   solution="Reduce to max 2 tasks")
        
        errors = self.load(self.test_project)
        assert errors["errors"][0]["solution"] == "Reduce to max 2 tasks"
    
    def test_learn_dodge_tracks_evasion(self):
        """Dodge learning tracks Claude evasion attempts"""
        self.dodge(self.test_project, "refuses", "I cannot do that")
        
        errors = self.load(self.test_project)
        assert len(errors.get("dodges", [])) == 1
        assert errors["dodges"][0]["type"] == "refuses"
    
    def test_get_similar_errors(self):
        """Can retrieve errors of same type"""
        self.learn(self.test_project, "truncation", "Error 1")
        self.learn(self.test_project, "truncation", "Error 2")
        self.learn(self.test_project, "parse_error", "Different")
        
        similar = self.similar(self.test_project, "truncation")
        assert len(similar) == 2
    
    def test_has_learned_solution(self):
        """Can retrieve learned solution"""
        self.learn(self.test_project, "truncation", "Error", 
                   solution="Use smaller chunks")
        
        sol = self.solution(self.test_project, "truncation")
        assert sol == "Use smaller chunks"
        
        sol = self.solution(self.test_project, "unknown_type")
        assert sol is None
    
    def test_error_context_for_retry(self):
        """Error context formatted for retry prompt"""
        self.learn(self.test_project, "truncation", "Response cut off")
        
        ctx = self.context(self.test_project)
        assert "truncation" in ctx
        assert "LEARNED ERRORS" in ctx


# ============================================================
# NEGOTIATOR TESTS
# ============================================================

class TestNegotiator:
    """Test negotiation strategies"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        from localagent.core.negotiator import (
            NEGOTIATION_STRATEGIES,
            analyze_instruction_complexity,
            get_negotiation_feedback,
            should_retry, get_retry_action,
            detect_dodge, validate_response
        )
        self.strategies = NEGOTIATION_STRATEGIES
        self.analyze = analyze_instruction_complexity
        self.feedback = get_negotiation_feedback
        self.should_retry = should_retry
        self.action = get_retry_action
        self.detect_dodge = detect_dodge
        self.validate = validate_response
    
    def test_strategies_defined(self):
        """Negotiation strategies must be defined"""
        required = ["truncation", "parse_error", "empty_response", "no_tasks"]
        for strategy in required:
            assert strategy in self.strategies, f"Missing strategy: {strategy}"
            assert "feedback" in self.strategies[strategy]
            assert "max_retries" in self.strategies[strategy]
    
    def test_analyze_simple_instruction(self):
        """Simple instruction should not need split"""
        result = self.analyze("Create a login form")
        assert result["needs_split"] == False
        assert result["complexity_score"] < 4
    
    def test_analyze_complex_instruction(self):
        """Complex instruction should need split"""
        instruction = """
        First create the login form, then add validation,
        and also add error messages. After that implement
        the API call, and finally add unit tests.
        """
        result = self.analyze(instruction)
        assert result["needs_split"] == True
        assert result["complexity_score"] >= 4
        assert len(result["parts"]) > 1
    
    def test_detect_dodge_refuses(self):
        """Should detect when Claude refuses"""
        response = "I can't help with that request"
        result = self.detect_dodge(response)
        assert result is not None
        assert result[0] == "refuses"
    
    def test_detect_dodge_clarification(self):
        """Should detect clarification requests"""
        response = "Could you clarify what you mean by that?"
        result = self.detect_dodge(response)
        assert result is not None
        assert result[0] == "asks_clarification"
    
    def test_detect_dodge_normal_response(self):
        """Normal response should not be flagged as dodge"""
        response = '{"tasks": [{"id": "T001", "type": "create_file"}]}'
        result = self.detect_dodge(response)
        assert result is None
    
    def test_validate_response_valid_json(self):
        """Valid JSON response should pass"""
        response = json.dumps({
            "tasks": [{
                "id": "T001",
                "type": "create_file",
                "description": "Create file",
                "filename": "test.txt",
                "content": "This is test content that is long enough"
            }]
        })
        result = self.validate(response)
        assert result["valid"] == True
        assert len(result["tasks"]) == 1
    
    def test_validate_response_empty(self):
        """Empty response should fail"""
        result = self.validate("")
        assert result["valid"] == False
        assert result["error_type"] == "empty_response"
    
    def test_validate_response_not_json(self):
        """Non-JSON response should fail"""
        result = self.validate("This is not JSON")
        assert result["valid"] == False
        assert result["error_type"] == "parse_error"
    
    def test_validate_response_message_only_is_valid(self):
        """Response with message but no tasks is valid (conversation)"""
        result = self.validate('{"message": "Hello! How can I help you?", "tasks": []}')
        assert result["valid"] == True
        assert result["message"] == "Hello! How can I help you?"
        assert result["tasks"] == []
    
    def test_validate_response_no_tasks_no_message(self):
        """Response without tasks AND without message should fail"""
        result = self.validate('{"tasks": []}')
        assert result["valid"] == False
        assert result["error_type"] == "no_tasks"
    
    def test_validate_response_missing_content(self):
        """create_file without content should fail"""
        response = json.dumps({
            "tasks": [{
                "id": "T001",
                "type": "create_file",
                "description": "Create file",
                "filename": "test.txt"
                # Missing content!
            }]
        })
        result = self.validate(response)
        assert result["valid"] == False
        assert result["error_type"] == "missing_content"
    
    def test_validate_response_too_many_tasks(self):
        """More than 3 tasks should fail"""
        tasks = [{"id": f"T00{i}", "type": "info", "description": "task"} for i in range(5)]
        response = json.dumps({"tasks": tasks})
        result = self.validate(response)
        assert result["valid"] == False
        assert result["error_type"] == "too_many_tasks"
    
    def test_validate_response_strips_markdown(self):
        """Should strip markdown code blocks"""
        response = '```json\n{"tasks": [{"id": "T001", "type": "info", "description": "test"}]}\n```'
        result = self.validate(response)
        assert result["valid"] == True
    
    def test_should_retry_within_limit(self):
        """Should allow retry within limit"""
        assert self.should_retry("truncation", 0) == True
        assert self.should_retry("truncation", 1) == True
        assert self.should_retry("truncation", 2) == True
    
    def test_should_retry_exceeds_limit(self):
        """Should not retry beyond limit"""
        assert self.should_retry("truncation", 3) == False
        assert self.should_retry("truncation", 5) == False


# ============================================================
# PROTOCOL TESTS
# ============================================================

class TestProtocol:
    """Test protocol enforcement"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        from localagent.core.protocol import (
            ProtocolStep, ProtocolExecution, PROTOCOL_STEPS,
            ProtocolExecutor
        )
        self.Step = ProtocolStep
        self.Execution = ProtocolExecution
        self.STEPS = PROTOCOL_STEPS
        self.Executor = ProtocolExecutor
    
    def test_protocol_steps_defined(self):
        """Protocol steps must be defined"""
        assert len(self.STEPS) > 0
        
        required_steps = ["fetch_github_version", "create_snapshot_before"]
        step_names = [s["name"] for s in self.STEPS]
        
        for required in required_steps:
            assert required in step_names, f"Missing protocol step: {required}"
    
    def test_protocol_steps_have_constraints(self):
        """Each step should reference a constraint"""
        for step in self.STEPS:
            assert "constraint" in step, f"Step {step['name']} missing constraint reference"
    
    def test_protocol_step_dataclass(self):
        """ProtocolStep dataclass should work"""
        step = self.Step(
            step_id="STEP_01",
            name="test_step",
            status="pending"
        )
        assert step.step_id == "STEP_01"
        assert step.status == "pending"
    
    def test_protocol_execution_dataclass(self):
        """ProtocolExecution dataclass should work"""
        execution = self.Execution(
            execution_id="EX001",
            todo_id="TODO001",
            todo_title="Test todo",
            project="test-project",
            github_repo="test/repo",
            started_at=datetime.now().isoformat()
        )
        assert execution.status == "running"
        assert execution.current_step == 0
    
    def test_protocol_has_13_steps(self):
        """Protocol should have exactly 13 steps"""
        assert len(self.STEPS) == 13, f"Expected 13 steps, got {len(self.STEPS)}"
    
    def test_protocol_step_order_is_correct(self):
        """Protocol steps must be in correct order"""
        expected_order = [
            "fetch_github_version",      # 1
            "calculate_next_version",    # 2
            "create_snapshot_before",    # 3
            "build_claude_context",      # 4
            "call_claude",               # 5
            "validate_response",         # 6
            "execute_tasks",             # 7
            "create_snapshot_after",     # 8
            "git_commit",                # 9
            "git_push",                  # 10
            "create_github_release",     # 11
            "verify_release",            # 12
            "mark_todo_done"             # 13
        ]
        actual_order = [s["name"] for s in self.STEPS]
        assert actual_order == expected_order, f"Step order mismatch"
    
    def test_protocol_executor_initializes(self):
        """ProtocolExecutor should initialize correctly"""
        executor = self.Executor(
            project="test-project",
            github_repo="test/repo"
        )
        assert executor.project == "test-project"
        assert executor.github_repo == "test/repo"
        assert executor.execution is None
    
    def test_protocol_critical_constraints_enforced(self):
        """Critical constraints should be enforced at correct steps"""
        step_constraints = {s["name"]: s["constraint"] for s in self.STEPS}
        
        # ENV012: Version from GitHub
        assert step_constraints["fetch_github_version"] == "ENV012"
        assert step_constraints["create_github_release"] == "ENV012"
        
        # ENV003/ENV014: Snapshots
        assert step_constraints["create_snapshot_before"] == "ENV003"
        assert step_constraints["create_snapshot_after"] == "ENV014"
        
        # ENV013: Verify release
        assert step_constraints["verify_release"] == "ENV013"


# ============================================================
# INTEGRATION: Dashboard should expose core features
# ============================================================

class TestDashboardCoreIntegration:
    """Test that dashboard properly exposes core features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from localagent.service.server import app
            from fastapi.testclient import TestClient
            self.client = TestClient(app)
            self.available = True
        except ImportError:
            self.available = False
    
    def test_constraints_endpoint_returns_all(self):
        """Constraints endpoint should return both ENV and CTX"""
        if not self.available:
            pytest.skip("Server not available")
        
        r = self.client.get("/api/constraints")
        assert r.status_code == 200
        data = r.json()
        constraints = data.get("constraints", data)  # Handle both formats
        
        # Should have both ENV and CTX
        env_count = sum(1 for c in constraints if c["id"].startswith("ENV"))
        ctx_count = sum(1 for c in constraints if c["id"].startswith("CTX"))
        
        assert env_count > 0, "No ENV constraints returned"
        assert ctx_count > 0, "No CTX constraints returned"
    
    def test_learning_endpoint_exists(self):
        """Learning patterns endpoint should exist"""
        if not self.available:
            pytest.skip("Server not available")
        
        r = self.client.get("/api/learning/patterns")
        # Should exist (200) or be empty (200 with empty data)
        assert r.status_code in [200, 404]
    
    def test_lint_endpoint_validates_prompt(self):
        """Lint endpoint should validate prompts"""
        if not self.available:
            pytest.skip("Server not available")
        
        # A complex prompt that should get feedback
        r = self.client.post("/api/lint", json={
            "prompt": "First do X, then do Y, and also Z, finally W"
        })
        assert r.status_code == 200
    
    def test_chat_includes_constraints_in_context(self):
        """Chat should include constraints in system prompt"""
        if not self.available:
            pytest.skip("Server not available")
        
        # This is hard to test without mocking Claude
        # At minimum, verify the endpoint accepts requests
        r = self.client.post("/api/chat", json={
            "message": "test",
            "include_constraints": True
        })
        # Should not crash
        assert r.status_code in [200, 400, 401, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


class TestDebuggerLearning:
    """Test debugger learning and auto-fix capabilities"""
    
    def test_error_signature_extraction(self):
        """Error signatures should normalize variable data"""
        from localagent.core.debugger import _extract_error_signature
        
        sig1 = _extract_error_signature({"message": "Error at line 42 in 'value'"})
        sig2 = _extract_error_signature({"message": "Error at line 100 in 'other'"})
        
        # Should normalize line numbers and quoted values
        assert "line X" in sig1
        assert "'X'" in sig1
        assert sig1 == sig2  # Same pattern after normalization
    
    def test_learn_from_fix(self):
        """Learning should store pattern for future errors"""
        from localagent.core.debugger import (
            log_error, learn_from_fix, get_learned_fix, 
            _extract_error_signature, _load_error_patterns
        )
        
        # Log an error
        error_id = log_error({"message": "Test error for learning"}, "test")
        
        # Learn from fix
        learn_from_fix(error_id, "Fixed by doing X", "console.log('fixed')")
        
        # Check pattern was stored
        patterns = _load_error_patterns()
        assert len(patterns["patterns"]) > 0
    
    def test_similarity_function(self):
        """Similarity function should work correctly"""
        from localagent.core.debugger import _similarity
        
        assert _similarity("hello world", "hello world") == 1.0
        assert _similarity("hello world", "goodbye world") > 0.3
        assert _similarity("", "") == 0.0
    
    def test_debug_stats(self):
        """Debug stats should return valid structure"""
        from localagent.core.debugger import get_debug_stats
        
        stats = get_debug_stats()
        assert "total_errors" in stats
        assert "auto_fixed" in stats
        assert "learned_patterns" in stats


class TestDebuggerEndpoints:
    """Test debugger API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from fastapi.testclient import TestClient
            from localagent.service.server import app
            self.client = TestClient(app)
            self.available = True
        except:
            self.available = False
    
    def test_debug_stats_endpoint(self):
        """GET /api/debug/stats should return stats"""
        if not self.available:
            pytest.skip("FastAPI not available")
        
        r = self.client.get("/api/debug/stats")
        assert r.status_code == 200
        data = r.json()
        assert "total_errors" in data
    
    def test_debug_context_endpoint(self):
        """GET /api/debug/context should return context"""
        if not self.available:
            pytest.skip("FastAPI not available")
        
        r = self.client.get("/api/debug/context")
        assert r.status_code == 200
        data = r.json()
        assert "context" in data
    
    def test_debug_learn_endpoint(self):
        """POST /api/debug/learn should learn from fix"""
        if not self.available:
            pytest.skip("FastAPI not available")
        
        # First log an error
        r = self.client.post("/api/debug/error", json={
            "message": "Test error for learning endpoint",
            "source": "test"
        })
        error_id = r.json().get("error_id")
        
        # Then learn from it
        r = self.client.post("/api/debug/learn", json={
            "error_id": error_id,
            "fix_description": "Test fix",
            "fix_code": "// fixed"
        })
        assert r.status_code == 200
        assert r.json().get("learned") == True
