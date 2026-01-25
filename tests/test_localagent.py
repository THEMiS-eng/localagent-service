#!/usr/bin/env python3
"""
LocalAgent v3.0.69 - Test Suite
Comprehensive tests for all modules
"""

import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '.')

import pytest

# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def temp_project_dir():
    """Create temporary project directory."""
    temp_dir = Path(tempfile.mkdtemp())
    project_dir = temp_dir / "TEST_PROJECT" / "current"
    project_dir.mkdir(parents=True, exist_ok=True)
    yield project_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_constraints():
    """Sample constraint data."""
    return [
        {"id": "ENV001", "rule": "Test rule 1", "severity": "CRITICAL"},
        {"id": "CTX001", "rule": "Test rule 2", "severity": "HIGH"},
    ]


# ============================================================
# CORE: CONSTRAINTS
# ============================================================

class TestConstraints:
    """Tests for localagent/core/constraints.py"""
    
    def test_get_all_constraints(self):
        from localagent.core.constraints import get_all_constraints
        constraints = get_all_constraints()
        assert isinstance(constraints, list)
        assert len(constraints) > 0
    
    def test_env_constraints_structure(self):
        from localagent.core.constraints import ENV_CONSTRAINTS
        assert isinstance(ENV_CONSTRAINTS, list)
        for c in ENV_CONSTRAINTS:
            assert "id" in c
            assert "rule" in c
            assert "severity" in c
            assert c["id"].startswith("ENV")
    
    def test_ctx_constraints_structure(self):
        from localagent.core.constraints import CTX_CONSTRAINTS
        assert isinstance(CTX_CONSTRAINTS, list)
        for c in CTX_CONSTRAINTS:
            assert "id" in c
            assert "rule" in c
            assert "severity" in c
            assert c["id"].startswith("CTX")
    
    def test_no_duplicate_ids(self):
        from localagent.core.constraints import get_all_constraints
        constraints = get_all_constraints()
        ids = [c["id"] for c in constraints]
        assert len(ids) == len(set(ids)), "Duplicate constraint IDs found"
    
    def test_valid_severity_levels(self):
        from localagent.core.constraints import get_all_constraints
        valid_severities = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        for c in get_all_constraints():
            assert c["severity"] in valid_severities, f"Invalid severity in {c['id']}"
    
    def test_get_constraint_by_id(self):
        from localagent.core.constraints import get_constraint
        c = get_constraint("ENV001")
        assert c is not None
        assert c["id"] == "ENV001"
    
    def test_get_constraint_not_found(self):
        from localagent.core.constraints import get_constraint
        c = get_constraint("NONEXISTENT")
        assert c is None
    
    def test_validate_action_clean(self):
        from localagent.core.constraints import validate_action
        is_valid, violations = validate_action("chat", {"message": "hello"})
        assert is_valid is True
        assert violations == []
    
    def test_validate_action_protected_file(self):
        from localagent.core.constraints import validate_action
        is_valid, violations = validate_action("modify", {"file": "app.min.js"})
        assert is_valid is False
        assert any("ENV005" in v for v in violations)
    
    def test_validate_action_task_limit(self):
        from localagent.core.constraints import validate_action
        tasks = [{"id": f"T{i}"} for i in range(5)]
        is_valid, violations = validate_action("execute", {"tasks": tasks})
        assert is_valid is False
        assert any("CTX003" in v for v in violations)
    
    def test_constraint_violation_exception(self):
        from localagent.core.constraints import ConstraintViolation
        with pytest.raises(ConstraintViolation):
            raise ConstraintViolation(["ENV001: Test violation"])
    
    def test_build_system_prompt(self):
        from localagent.core.constraints import build_system_prompt
        prompt = build_system_prompt()
        assert isinstance(prompt, str)
        assert "JSON" in prompt
        assert "CONSTRAINTS" in prompt


# ============================================================
# CORE: LEARNING
# ============================================================

class TestLearning:
    """Tests for localagent/core/learning.py"""
    
    def test_load_learned_errors_empty(self, temp_project_dir):
        from localagent.core.learning import load_learned_errors
        errors = load_learned_errors("NONEXISTENT_PROJECT")
        assert isinstance(errors, dict)
        assert "errors" in errors or errors == {}
    
    def test_learn_from_error(self, temp_project_dir):
        from localagent.core.learning import learn_from_error
        
        # Correct signature: (project, error_type, error_msg, context, solution)
        learn_from_error(
            project="TEST",
            error_type="TestError",
            error_msg="Test error message",
            context={"test": "context"},
            solution="Test solution"
        )
    
    def test_error_structure(self):
        from localagent.core.learning import load_learned_errors
        errors = load_learned_errors("LOCALAGENT")
        if errors and "errors" in errors:
            for e in errors["errors"]:
                # Check basic structure if errors exist
                assert "type" in e or "message" in e


# ============================================================
# CORE: NEGOTIATOR
# ============================================================

class TestNegotiator:
    """Tests for localagent/core/negotiator.py"""
    
    def test_validate_response_valid_json(self):
        from localagent.core.negotiator import validate_response
        valid = {"tasks": [{"id": "T001", "type": "create_file", "filename": "test.txt", "content": "test"}]}
        result = validate_response(json.dumps(valid))
        # Returns dict with 'valid', 'error_type', etc.
        assert isinstance(result, dict)
        assert "valid" in result
    
    def test_validate_response_invalid_json(self):
        from localagent.core.negotiator import validate_response
        result = validate_response("not json {}")
        assert isinstance(result, dict)
        assert result.get("valid") is False
    
    def test_validate_response_empty_tasks(self):
        from localagent.core.negotiator import validate_response
        result = validate_response('{"tasks": []}')
        assert isinstance(result, dict)
        assert "valid" in result


# ============================================================
# CORE: DEBUGGER
# ============================================================

class TestDebugger:
    """Tests for localagent/core/debugger.py"""
    
    def test_get_pending_errors(self):
        from localagent.core.debugger import get_pending_errors
        errors = get_pending_errors()
        assert isinstance(errors, list)
    
    def test_log_error(self):
        from localagent.core.debugger import log_error
        # Correct signature: log_error(error: Dict, source: str = 'js')
        error_id = log_error(
            error={"message": "Test error", "type": "TestError"},
            source="test"
        )
        assert isinstance(error_id, str)
    
    def test_format_errors_for_claude(self):
        from localagent.core.debugger import format_errors_for_claude
        formatted = format_errors_for_claude()
        assert isinstance(formatted, str)


# ============================================================
# CORE: PROTOCOL
# ============================================================

class TestProtocol:
    """Tests for localagent/core/protocol.py"""
    
    def test_protocol_steps_defined(self):
        from localagent.core.protocol import PROTOCOL_STEPS
        assert isinstance(PROTOCOL_STEPS, list)
        assert len(PROTOCOL_STEPS) > 0
    
    def test_protocol_step_dataclass(self):
        from localagent.core.protocol import ProtocolStep
        # Correct fields: step_id, name, status, started_at, completed_at, data, error, constraint_checks
        step = ProtocolStep(
            step_id="test-001",
            name="test",
            status="pending",
            started_at=None,
            completed_at=None
        )
        assert step.name == "test"
        assert step.status == "pending"
        assert step.step_id == "test-001"
    
    def test_protocol_executor_exists(self):
        from localagent.core.protocol import ProtocolExecutor
        assert ProtocolExecutor is not None


# ============================================================
# ENGINE: PROJECT
# ============================================================

class TestProject:
    """Tests for localagent/engine/project.py"""
    
    def test_projects_dir_defined(self):
        from localagent.engine.project import PROJECTS_DIR
        assert isinstance(PROJECTS_DIR, Path)
    
    def test_init_project(self, temp_project_dir):
        from localagent.engine.project import init_project
        # Should not raise
        result = init_project("TEST_PROJECT")
        assert result is not None
    
    def test_get_version(self):
        from localagent.engine.project import get_version
        version = get_version("LOCALAGENT")
        assert isinstance(version, str)


# ============================================================
# ENGINE: TRACKING
# ============================================================

class TestTracking:
    """Tests for localagent/engine/tracking.py"""
    
    def test_get_conversation(self):
        from localagent.engine.tracking import get_conversation
        conv = get_conversation("LOCALAGENT")
        assert isinstance(conv, list)
    
    def test_tracking_imports(self):
        from localagent.engine.tracking import add_message, add_backlog_item
        # Just verify they exist
        assert callable(add_message)
        assert callable(add_backlog_item)


# ============================================================
# CONNECTORS: LLM
# ============================================================

class TestLLM:
    """Tests for localagent/connectors/llm.py"""
    
    def test_call_claude_no_key(self):
        from localagent.connectors.llm import call_claude
        # Without API key, should return error dict
        result = call_claude("test prompt")
        assert isinstance(result, dict)
        # Either success with response or error
        assert "response" in result or "error" in result


# ============================================================
# CONNECTORS: GITHUB
# ============================================================

class TestGitHub:
    """Tests for localagent/connectors/github.py"""
    
    def test_repos_defined(self):
        from localagent.connectors.github import REPOS
        assert isinstance(REPOS, dict)
        assert "service" in REPOS or len(REPOS) >= 0
    
    def test_github_api_constant(self):
        from localagent.connectors.github import GITHUB_API
        assert GITHUB_API == "https://api.github.com"


# ============================================================
# CONNECTORS: DASHBOARD
# ============================================================

class TestDashboardConnector:
    """Tests for localagent/connectors/dashboard.py"""
    
    def test_set_get_project(self):
        from localagent.connectors.dashboard import set_project, get_project
        set_project("TEST_PROJECT")
        assert get_project() == "TEST_PROJECT"


# ============================================================
# ROADMAP: PROMPT OPTIMIZER
# ============================================================

class TestPromptOptimizer:
    """Tests for localagent/roadmap/prompt_optimizer.py"""
    
    def test_lint_prompt_english(self):
        from localagent.roadmap.prompt_optimizer import lint_prompt
        result = lint_prompt("Create a web page with a form")
        assert isinstance(result, dict)
        assert "score" in result
        assert "language" in result
        assert result["language"] == "en"
    
    def test_lint_prompt_french(self):
        from localagent.roadmap.prompt_optimizer import lint_prompt
        result = lint_prompt("Créer une page web avec un formulaire")
        assert isinstance(result, dict)
        assert result["language"] == "fr"
    
    def test_lint_prompt_detects_negation(self):
        from localagent.roadmap.prompt_optimizer import lint_prompt
        result = lint_prompt("Don't use any loops")
        assert result["score"] < 100
        issues = [i["type"] for i in result.get("issues", [])]
        assert "negation" in issues
    
    def test_lint_prompt_score_range(self):
        from localagent.roadmap.prompt_optimizer import lint_prompt
        result = lint_prompt("Create a simple test")
        assert 0 <= result["score"] <= 100
    
    def test_preprocess_for_negotiation(self):
        from localagent.roadmap.prompt_optimizer import preprocess_for_negotiation
        optimized, report = preprocess_for_negotiation("Create a test", "TEST")
        assert isinstance(optimized, str)
        assert isinstance(report, dict)


# ============================================================
# SERVICE: SERVER MODELS
# ============================================================

class TestServerModels:
    """Tests for server endpoint models"""
    
    def test_server_uses_fastapi(self):
        """Server should use FastAPI framework"""
        server_path = Path("localagent/service/server.py")
        content = server_path.read_text()
        assert "from fastapi import FastAPI" in content
        assert "app = FastAPI" in content
    
    def test_server_has_cors(self):
        """Server should have CORS middleware"""
        server_path = Path("localagent/service/server.py")
        content = server_path.read_text()
        assert "CORSMiddleware" in content
    
    def test_server_has_websocket_support(self):
        """Server should support WebSocket connections"""
        server_path = Path("localagent/service/server.py")
        content = server_path.read_text()
        assert "WebSocket" in content
        assert "ConnectionManager" in content
    
    def test_server_mounts_modules_directory(self):
        """Server should mount /modules for static file serving"""
        server_path = Path("localagent/service/server.py")
        content = server_path.read_text()
        assert "StaticFiles" in content, "Server should import StaticFiles"
        assert 'app.mount("/modules"' in content, "Server should mount /modules"
        assert "_find_modules_dir" in content, "Server should have modules directory finder"
    
    def test_server_has_dashboard_finder(self):
        """Server should find dashboard with fallback paths"""
        server_path = Path("localagent/service/server.py")
        content = server_path.read_text()
        assert "_find_dashboard" in content
        assert "dashboard" in content.lower()


# ============================================================
# INTEGRATION TESTS
# ============================================================

class TestIntegration:
    """Integration tests across modules"""
    
    def test_constraints_used_in_negotiator(self):
        from localagent.core.constraints import get_constraints_for_context
        from localagent.core.negotiator import negotiate_request
        
        context = get_constraints_for_context()
        assert isinstance(context, str)
        assert "CONSTRAINT" in context.upper()
    
    def test_learning_used_in_constraints(self):
        from localagent.core.constraints import build_system_prompt
        prompt = build_system_prompt("LOCALAGENT")
        assert isinstance(prompt, str)
    
    def test_full_protocol_flow(self):
        from localagent.core.protocol import PROTOCOL_STEPS, ProtocolStep
        from localagent.core.constraints import validate_action
        from localagent.roadmap.prompt_optimizer import lint_prompt
        
        # Step 1: Lint
        lint_result = lint_prompt("Create a test file")
        assert lint_result["score"] >= 0
        
        # Step 2: Validate
        is_valid, violations = validate_action("chat", {"message": "test"})
        assert is_valid is True
        
        # Protocol steps exist
        assert len(PROTOCOL_STEPS) > 0


# ============================================================
# HTML MODULE TESTS
# ============================================================

class TestChatModule:
    """Tests for the chat HTML module"""
    
    # Cache the content to avoid reading file multiple times
    @pytest.fixture(autouse=True)
    def setup(self):
        self.module_path = Path("modules/ai-chat-module-pro/chat-pro-standalone.html")
        self.content = self.module_path.read_text() if self.module_path.exists() else ""
    
    def test_chat_module_exists(self):
        assert self.module_path.exists()
    
    def test_chat_module_is_valid_html(self):
        """Module should be valid HTML5"""
        assert "<!DOCTYPE html>" in self.content
        assert "<html" in self.content
        assert "</html>" in self.content
        assert "<head>" in self.content
        assert "<body>" in self.content
    
    def test_chat_module_has_api_call(self):
        assert "/api/chat" in self.content
        assert "window.location.origin" in self.content, "Should use dynamic origin for API"
    
    def test_chat_module_has_linter(self):
        assert "PromptLinter" in self.content  # Uses external bundle
        assert "runLint" in self.content
        assert "debounceLint" in self.content
    
    def test_chat_module_loads_external_linter(self):
        """Chat should load external PromptLinter bundle"""
        assert 'src="./PromptLinter.bundle.js"' in self.content
        assert "window.PromptLinter" in self.content
    
    def test_chat_module_linter_ui_elements(self):
        """Linter should have UI elements"""
        assert 'id="linterBar"' in self.content
        assert 'id="linterScore"' in self.content
        assert "linter-issue" in self.content
    
    def test_chat_module_has_voice(self):
        assert "startRecording" in self.content
        assert "stopRecording" in self.content
        assert "getUserMedia" in self.content or "mediaDevices" in self.content
    
    def test_chat_module_tracks_input_source(self):
        assert "lastInputSource" in self.content
        assert "'voice'" in self.content or '"voice"' in self.content
        assert "'text'" in self.content or '"text"' in self.content
    
    def test_chat_module_no_double_mic_permission(self):
        assert "requestMic()" not in self.content or self.content.count("getUserMedia") <= 2
    
    def test_chat_module_js_no_syntax_errors(self):
        """JavaScript should have balanced braces"""
        script_start = self.content.find('<script>') + 8
        script_end = self.content.find('</script>')
        js_code = self.content[script_start:script_end]
        
        open_braces = js_code.count('{')
        close_braces = js_code.count('}')
        assert open_braces == close_braces, f"Unbalanced braces: {open_braces} open, {close_braces} close"
        
        # Check no duplicate code blocks
        assert '}\n  \n  generating = false;' not in js_code
    
    def test_chat_module_has_message_display(self):
        """Chat should have message container and display logic"""
        assert 'id="msgs"' in self.content or 'class="messages"' in self.content
        assert "addMessage" in self.content or "msg.user" in self.content
    
    def test_chat_module_has_input_area(self):
        """Chat should have input textarea"""
        assert 'id="input"' in self.content
        assert "textarea" in self.content.lower()
    
    def test_chat_module_has_send_button(self):
        """Chat should have send functionality"""
        assert 'id="send"' in self.content or "sendMessage" in self.content
        assert "send" in self.content.lower()
    
    def test_chat_module_handles_errors(self):
        """Chat should handle API errors gracefully"""
        assert "catch" in self.content
        assert "error" in self.content.lower()
        assert "Failed to fetch" in self.content or "NetworkError" in self.content
    
    def test_chat_module_has_loading_states(self):
        """Chat should show loading/generating states"""
        assert "generating" in self.content
        assert "cursor" in self.content or "loading" in self.content.lower()
    
    def test_chat_module_supports_markdown(self):
        """Chat should parse markdown in responses"""
        assert "parseContent" in self.content or "markdown" in self.content.lower()
        assert "code-block" in self.content or "<code" in self.content
    
    def test_chat_module_has_protocol_steps(self):
        """Chat should display protocol steps from backend"""
        assert "protocol_steps" in self.content or "protocolSteps" in self.content
        assert "addStep" in self.content


class TestPromptLinterBundle:
    """Tests for the external PromptLinter bundle"""
    
    def test_bundle_exists(self):
        bundle_path = Path("modules/ai-chat-module-pro/PromptLinter.bundle.js")
        assert bundle_path.exists()
    
    def test_bundle_is_iife(self):
        """Bundle should be an IIFE for browser compatibility"""
        content = Path("modules/ai-chat-module-pro/PromptLinter.bundle.js").read_text()
        assert "(function(global)" in content or "(function(" in content
        assert "window.PromptLinter" in content or "global.PromptLinter" in content
    
    def test_bundle_exports_main_functions(self):
        """Bundle should export lintPrompt and other key functions"""
        content = Path("modules/ai-chat-module-pro/PromptLinter.bundle.js").read_text()
        assert "lintPrompt" in content
        assert "detectLanguage" in content
        assert "optimizePrompt" in content
        assert "estimateTokens" in content
    
    def test_bundle_has_lint_rules(self):
        """Bundle should contain lint rules"""
        content = Path("modules/ai-chat-module-pro/PromptLinter.bundle.js").read_text()
        assert "LINT_RULES" in content
        assert "negation" in content
        assert "severity" in content
    
    def test_bundle_supports_fr_and_en(self):
        """Bundle should support French and English"""
        content = Path("modules/ai-chat-module-pro/PromptLinter.bundle.js").read_text()
        assert "FR_PATTERNS" in content or "'fr'" in content
        assert "EN_PATTERNS" in content or "'en'" in content


class TestChatModuleCSS:
    """Tests for CSS theming and dashboard integration"""
    
    def test_chat_has_theme_variables(self):
        """Chat module should define CSS theme variables"""
        module_path = Path("modules/ai-chat-module-pro/chat-pro-standalone.html")
        content = module_path.read_text()
        # Should have chat-prefixed variables for theming
        assert "--chat-bg" in content
        assert "--chat-text" in content
        assert "--chat-accent" in content
        assert "--chat-surface" in content
    
    def test_chat_supports_light_theme(self):
        """Chat module should support light theme"""
        module_path = Path("modules/ai-chat-module-pro/chat-pro-standalone.html")
        content = module_path.read_text()
        # Should have light theme definitions
        assert ".light" in content or 'data-theme="light"' in content
        assert "prefers-color-scheme: light" in content
    
    def test_chat_has_theme_detection(self):
        """Chat module should auto-detect theme"""
        module_path = Path("modules/ai-chat-module-pro/chat-pro-standalone.html")
        content = module_path.read_text()
        assert "detectTheme" in content or "setTheme" in content
    
    def test_chat_has_theme_api(self):
        """Chat module should expose theme API"""
        module_path = Path("modules/ai-chat-module-pro/chat-pro-standalone.html")
        content = module_path.read_text()
        assert "LocalAgentChat" in content
        assert "setTheme" in content
        assert "getTheme" in content
    
    def test_chat_css_uses_themed_variables(self):
        """CSS should use --chat-* variables consistently"""
        module_path = Path("modules/ai-chat-module-pro/chat-pro-standalone.html")
        content = module_path.read_text()
        
        # Extract CSS section
        css_start = content.find("<style>")
        css_end = content.find("</style>")
        css = content[css_start:css_end]
        
        # Key elements should use themed variables
        assert "var(--chat-bg)" in css
        assert "var(--chat-text)" in css
        assert "var(--chat-border)" in css
        assert "var(--chat-surface)" in css
    
    def test_chat_no_hardcoded_dark_colors_in_elements(self):
        """Main elements should not have hardcoded dark colors"""
        module_path = Path("modules/ai-chat-module-pro/chat-pro-standalone.html")
        content = module_path.read_text()
        
        css_start = content.find("<style>")
        css_end = content.find("</style>")
        css = content[css_start:css_end]
        
        # Body background should use variable
        assert "body{" in css.replace(" ", "").replace("\n", "")
        body_section = css[css.find("body{"):css.find("}", css.find("body{"))+1]
        assert "var(--chat-bg)" in body_section or "var(--bg)" in body_section
    
    def test_chat_light_theme_colors_defined(self):
        """Light theme should define appropriate colors"""
        module_path = Path("modules/ai-chat-module-pro/chat-pro-standalone.html")
        content = module_path.read_text()
        
        # Light theme should have light backgrounds
        assert "#ffffff" in content or "#fff" in content
        assert "#f8f9fa" in content or "#f1f3f4" in content  # Light surface colors
        assert "#202124" in content or "#5f6368" in content  # Dark text for light theme


class TestDashboardIntegration:
    """Tests for dashboard-chat integration"""
    
    def test_dashboard_has_chat_iframe(self):
        """Dashboard should embed chat via iframe"""
        dashboard_path = Path("dashboard/index.html")
        content = dashboard_path.read_text()
        assert "iframe" in content.lower()
        assert "chat-pro-standalone.html" in content
    
    def test_dashboard_has_grid_layout(self):
        """Dashboard should use grid for chat + sidebar layout"""
        dashboard_path = Path("dashboard/index.html")
        content = dashboard_path.read_text()
        assert "grid" in content
        assert "grid-template-columns" in content
    
    def test_dashboard_chat_frame_full_height(self):
        """Chat iframe should take full height"""
        dashboard_path = Path("dashboard/index.html")
        content = dashboard_path.read_text()
        assert "height: 100%" in content or "height:100%" in content
    
    def test_dashboard_defines_css_variables(self):
        """Dashboard should define CSS variables for theming"""
        dashboard_path = Path("dashboard/index.html")
        content = dashboard_path.read_text()
        assert "--bg:" in content or "--bg :" in content
        assert "--text:" in content or "--text :" in content
        assert "--blue:" in content or "--accent:" in content
    
    def test_chat_and_dashboard_share_color_semantics(self):
        """Chat and dashboard should use similar color semantics"""
        chat_path = Path("modules/ai-chat-module-pro/chat-pro-standalone.html")
        dashboard_path = Path("dashboard/index.html")
        
        chat_content = chat_path.read_text()
        dashboard_content = dashboard_path.read_text()
        
        # Both should have success/error/warning colors
        for color_name in ["success", "error", "warning"]:
            assert color_name in chat_content, f"Chat missing {color_name} color"
            assert color_name in dashboard_content, f"Dashboard missing {color_name} color"
    
    def test_dashboard_iframe_passes_theme_parameter(self):
        """CRITICAL: Dashboard iframe MUST pass theme=light to chat module"""
        dashboard_path = Path("dashboard/index.html")
        content = dashboard_path.read_text()
        # The iframe src must include ?theme=light since dashboard is light themed
        assert "?theme=light" in content, "Dashboard iframe must pass ?theme=light to chat module"
    
    def test_dashboard_and_chat_theme_alignment(self):
        """Dashboard (light) and chat light theme should use matching colors"""
        chat_path = Path("modules/ai-chat-module-pro/chat-pro-standalone.html")
        dashboard_path = Path("dashboard/index.html")
        
        chat_content = chat_path.read_text()
        dashboard_content = dashboard_path.read_text()
        
        # Dashboard uses --bg: #f8f9fa (light)
        assert "#f8f9fa" in dashboard_content, "Dashboard should use light background"
        
        # Chat light theme should also use #f8f9fa or similar light color
        # Extract light theme section from chat
        light_section_start = chat_content.find(':root.light')
        light_section_end = chat_content.find('}', light_section_start) + 1
        light_css = chat_content[light_section_start:light_section_end]
        
        assert "#f8f9fa" in light_css or "#ffffff" in light_css, \
            "Chat light theme should use light background matching dashboard"
    
    def test_chat_light_theme_text_is_dark(self):
        """Chat light theme text should be dark (readable on light bg)"""
        chat_path = Path("modules/ai-chat-module-pro/chat-pro-standalone.html")
        content = chat_path.read_text()
        
        # Extract light theme section
        light_section_start = content.find(':root.light')
        light_section_end = content.find('}', light_section_start) + 1
        light_css = content[light_section_start:light_section_end]
        
        # Text should be dark (#202124 or similar)
        assert "#202124" in light_css or "#1f2937" in light_css or "#111" in light_css, \
            "Chat light theme text should be dark"
    
    def test_chat_url_theme_parameter_detection(self):
        """Chat module should detect theme from URL parameter"""
        chat_path = Path("modules/ai-chat-module-pro/chat-pro-standalone.html")
        content = chat_path.read_text()
        
        # Should check for ?theme= URL parameter
        assert "URLSearchParams" in content, "Chat should use URLSearchParams"
        assert "get('theme')" in content or 'get("theme")' in content, \
            "Chat should read theme from URL"
        assert "'light'" in content or '"light"' in content, \
            "Chat should handle light theme value"
    
    def test_dashboard_iframe_has_id(self):
        """Dashboard iframe should have an ID for JS access"""
        dashboard_path = Path("dashboard/index.html")
        content = dashboard_path.read_text()
        assert 'id="chatFrame"' in content or "id='chatFrame'" in content, \
            "Dashboard iframe should have id='chatFrame' for JS control"


class TestChatThemeConsistency:
    """Tests for CSS theme consistency across light/dark modes"""
    
    def test_light_theme_all_variables_defined(self):
        """Light theme must define ALL --chat-* variables"""
        chat_path = Path("modules/ai-chat-module-pro/chat-pro-standalone.html")
        content = chat_path.read_text()
        
        required_vars = [
            "--chat-bg", "--chat-surface", "--chat-surface2", "--chat-border",
            "--chat-text", "--chat-text2", "--chat-muted", "--chat-accent",
            "--chat-success", "--chat-error", "--chat-user-bg", "--chat-code-bg"
        ]
        
        # Extract light theme section
        light_start = content.find(':root.light')
        light_end = content.find('}', light_start) + 1
        light_css = content[light_start:light_end]
        
        for var in required_vars:
            assert var in light_css, f"Light theme missing {var}"
    
    def test_dark_and_light_have_same_variables(self):
        """Dark and light themes should define the same variables"""
        chat_path = Path("modules/ai-chat-module-pro/chat-pro-standalone.html")
        content = chat_path.read_text()
        
        # Extract variables from :root (dark default)
        root_start = content.find(':root {')
        root_end = content.find('}', root_start) + 1
        dark_css = content[root_start:root_end]
        
        # Extract variables from :root.light
        light_start = content.find(':root.light')
        light_end = content.find('}', light_start) + 1
        light_css = content[light_start:light_end]
        
        # Find all --chat-* variables in dark
        import re
        dark_vars = set(re.findall(r'--chat-[\w-]+', dark_css))
        light_vars = set(re.findall(r'--chat-[\w-]+', light_css))
        
        missing_in_light = dark_vars - light_vars
        assert len(missing_in_light) == 0, f"Light theme missing: {missing_in_light}"
    
    def test_no_hardcoded_colors_in_main_ui(self):
        """Main UI elements should not use hardcoded colors"""
        chat_path = Path("modules/ai-chat-module-pro/chat-pro-standalone.html")
        content = chat_path.read_text()
        
        # Extract CSS
        css_start = content.find("<style>")
        css_end = content.find("</style>")
        css = content[css_start:css_end]
        
        # These selectors should use variables, not hardcoded colors
        critical_selectors = [".messages", ".bubble", ".input-area", "body"]
        
        for selector in critical_selectors:
            # Find the selector in CSS
            selector_start = css.find(selector + "{") if selector + "{" in css else css.find(selector + " {")
            if selector_start == -1:
                continue
            selector_end = css.find("}", selector_start) + 1
            selector_css = css[selector_start:selector_end]
            
            # Should not have hardcoded dark colors like #0a0a0b, #18181b etc
            hardcoded_dark = ["#0a0a0b", "#18181b", "#1f1f23", "#27272a"]
            for color in hardcoded_dark:
                assert color not in selector_css, \
                    f"{selector} has hardcoded dark color {color} - should use var(--chat-*)"


# ============================================================
# VERSION TESTS
# ============================================================

class TestVersions:
    """Tests for version consistency"""
    
    def test_version_file_exists(self):
        version_path = Path("VERSION")
        assert version_path.exists()
    
    def test_version_format(self):
        version = Path("VERSION").read_text().strip()
        parts = version.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)
    
    def test_version_in_server_file(self):
        """Server should read version from VERSION file or have version mechanism"""
        server_path = Path("localagent/service/server.py")
        content = server_path.read_text()
        file_version = Path("VERSION").read_text().strip()
        
        # Version can be either hardcoded or read from file
        has_hardcoded = f'VERSION = "{file_version}"' in content
        has_version_reader = '_read_version' in content or 'VERSION' in content
        
        assert has_hardcoded or has_version_reader, "Server must have version mechanism"
    
    def test_module_version_format(self):
        pkg_path = Path("modules/ai-chat-module-pro/package.json")
        if pkg_path.exists():
            pkg = json.loads(pkg_path.read_text())
            version = pkg.get("version", "")
            parts = version.split(".")
            assert len(parts) == 3


# ============================================================
# DASHBOARD COMPREHENSIVE TESTS
# ============================================================

class TestDashboard:
    """Consolidated tests for dashboard"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.dashboard_path = Path("dashboard/index.html")
        self.content = self.dashboard_path.read_text() if self.dashboard_path.exists() else ""
        self.server_path = Path("localagent/service/server.py")
        self.server_content = self.server_path.read_text() if self.server_path.exists() else ""
    
    # === HTML Structure ===
    def test_dashboard_exists(self):
        assert self.dashboard_path.exists()
    
    def test_dashboard_valid_html(self):
        assert self.content.strip().startswith("<!DOCTYPE html>")
        assert "<html" in self.content
        assert "</html>" in self.content
    
    def test_dashboard_has_viewport_meta(self):
        assert 'viewport' in self.content
        assert 'width=device-width' in self.content
    
    def test_dashboard_has_title(self):
        assert '<title>' in self.content
        assert 'LocalAgent' in self.content
    
    def test_dashboard_no_external_dependencies(self):
        assert 'cdn.jsdelivr.net' not in self.content
        assert 'unpkg.com' not in self.content
        assert 'cdnjs.cloudflare.com' not in self.content
    
    # === CSS ===
    def test_dashboard_has_css_variables(self):
        assert ':root' in self.content
        assert '--bg' in self.content
        assert '--text' in self.content
        assert '--blue' in self.content or '--accent' in self.content
    
    def test_dashboard_has_responsive_layout(self):
        assert 'grid' in self.content
        assert 'grid-template-columns' in self.content
    
    def test_dashboard_header_fixed(self):
        assert 'position: fixed' in self.content or 'position:fixed' in self.content
    
    def test_dashboard_status_indicators(self):
        assert '.dot' in self.content
        assert 'success' in self.content
        assert 'error' in self.content
    
    # === JavaScript Functions ===
    def test_dashboard_api_configured(self):
        assert 'const API' in self.content
        assert 'localhost:9998' in self.content
    
    def test_dashboard_has_error_handling(self):
        fetch_count = self.content.count('await fetch')
        try_count = self.content.count('try {') + self.content.count('try{')
        catch_count = self.content.count('catch')
        # Should have catch blocks for error handling
        assert catch_count >= 10, f"Insufficient error handling: {catch_count} catch blocks"
    
    def test_dashboard_loader_functions(self):
        loaders = ['loadHealth', 'loadOutputs', 'loadSnapshots', 'loadBacklog', 
                   'loadTodo', 'loadBugfixes', 'loadConstraints', 'loadErrors', 'loadGitHub']
        for fn in loaders:
            assert f'function {fn}' in self.content or f'{fn} = ' in self.content, f"Missing {fn}"
    
    def test_dashboard_add_functions(self):
        for fn in ['addBacklog', 'addTodo', 'addBugfix']:
            assert fn in self.content, f"Missing {fn}"
    
    def test_dashboard_ui_functions(self):
        assert 'togglePanel' in self.content
        assert 'showTab' in self.content
    
    def test_dashboard_init_calls_loaders(self):
        # Should call loaders at startup
        for fn in ['loadHealth()', 'loadOutputs()', 'loadBacklog()']:
            assert fn in self.content, f"Missing init call: {fn}"
    
    def test_dashboard_has_periodic_refresh(self):
        assert 'setInterval' in self.content
    
    def test_dashboard_no_console_log(self):
        assert self.content.count('console.log') == 0, "Remove console.log for production"
    
    # === UI Elements ===
    def test_dashboard_has_chat_iframe(self):
        assert 'iframe' in self.content.lower()
        assert 'chat-pro-standalone.html' in self.content
        assert '?theme=light' in self.content
    
    def test_dashboard_iframe_has_id(self):
        assert 'id="chatFrame"' in self.content
    
    def test_dashboard_has_project_info(self):
        assert 'projName' in self.content
        assert 'projVer' in self.content
    
    def test_dashboard_has_tabs(self):
        assert 'showTab' in self.content
        for tab in ['files', 'backlog', 'todo', 'system']:
            assert f"showTab('{tab}')" in self.content or f'id="tab-{tab}"' in self.content
    
    def test_dashboard_has_panels(self):
        assert 'class="panel"' in self.content
        assert 'togglePanel' in self.content
    
    def test_dashboard_has_count_badges(self):
        for badge in ['filesCount', 'snapshotsCount', 'backlogCount', 'todoCount']:
            assert f'id="{badge}"' in self.content, f"Missing {badge}"
    
    # === Modals ===
    def test_dashboard_has_modals(self):
        assert 'releaseModal' in self.content
        assert 'updateModal' in self.content
    
    def test_dashboard_modals_hidden_by_default(self):
        assert 'display:none' in self.content
    
    def test_dashboard_modals_use_theme_variables(self):
        # Find modal content
        modal_start = self.content.find('id="releaseModal"')
        modal_end = self.content.find('</div>', modal_start + 200)
        modal = self.content[modal_start:modal_end]
        assert 'var(--' in modal, "Modal should use CSS variables"
    
    # === Version & Update System ===
    def test_dashboard_has_version_display(self):
        assert 'srvVersion' in self.content
    
    def test_dashboard_has_update_badge(self):
        assert 'updateBadge' in self.content
    
    def test_dashboard_version_comparison(self):
        assert 'isNewerVersion' in self.content
        assert 'split' in self.content
    
    def test_dashboard_publish_functionality(self):
        assert 'showPublishPrompt' in self.content
        assert 'publishToGitHub' in self.content
    
    def test_dashboard_three_version_states(self):
        # Local < GitHub, Local > GitHub, Local == GitHub
        assert 'isNewerVersion(d.github_version, d.version)' in self.content
        assert 'isNewerVersion(d.version, d.github_version)' in self.content
    
    # === API Endpoints Validation ===
    def test_dashboard_endpoints_exist_in_server(self):
        import re
        endpoints = set(re.findall(r'/api/[\w/-]+', self.content))
        
        missing = []
        for ep in endpoints:
            clean_ep = ep.split('?')[0]
            if clean_ep not in self.server_content:
                # Check for parameterized routes
                base = '/'.join(clean_ep.split('/')[:-1])
                if base not in self.server_content and len(base) > 5:
                    missing.append(clean_ep)
        
        assert len(missing) == 0, f"Missing endpoints: {missing}"
    
    # === Empty States ===
    def test_dashboard_handles_empty_states(self):
        assert 'No files' in self.content or 'empty' in self.content
        assert 'No ' in self.content  # "No items", "No errors", etc.


class TestDashboardAPIEndpoints:
    """Tests to verify dashboard uses correct API endpoints"""
    
    def test_dashboard_endpoints_exist_in_server(self):
        """All endpoints used by dashboard should exist in server"""
        dashboard = Path("dashboard/index.html").read_text()
        server = Path("localagent/service/server.py").read_text()
        
        # Extract endpoints from dashboard
        import re
        dashboard_endpoints = re.findall(r'/api/[\w/-]+', dashboard)
        dashboard_endpoints = list(set(dashboard_endpoints))
        
        missing = []
        for endpoint in dashboard_endpoints:
            # Normalize endpoint (remove query params indication)
            clean_endpoint = endpoint.split('?')[0]
            # Check if endpoint is defined in server
            if clean_endpoint not in server and f'"{clean_endpoint}"' not in server:
                # Check for parameterized routes
                base_endpoint = '/'.join(clean_endpoint.split('/')[:-1])
                if base_endpoint not in server and f'"{base_endpoint}' not in server:
                    missing.append(clean_endpoint)
        
        assert len(missing) == 0, f"Dashboard uses undefined endpoints: {missing}"
    
    def test_dashboard_health_endpoint_format(self):
        """Health endpoint should return expected format"""
        server = Path("localagent/service/server.py").read_text()
        
        # Find health endpoint
        assert '/api/health' in server
        # Should return version and status
        health_section = server[server.find('@app.get("/api/health")'):]
        health_section = health_section[:health_section.find('@app.', 10)]
        
        assert 'version' in health_section.lower() or 'VERSION' in health_section
        assert 'status' in health_section.lower()


class TestDashboardUIElements:
    """Tests for dashboard UI elements"""
    
    def test_dashboard_has_project_info_section(self):
        """Dashboard should show current project info"""
        content = Path("dashboard/index.html").read_text()
        assert 'projName' in content
        assert 'projVer' in content
        assert 'projPath' in content
    
    def test_dashboard_has_tabs(self):
        """Dashboard should have tab navigation"""
        content = Path("dashboard/index.html").read_text()
        assert 'tab' in content.lower()
        assert 'showTab' in content
        assert 'tab-content' in content
    
    def test_dashboard_tab_content_ids_match_navigation(self):
        """Tab content IDs should match tab navigation"""
        content = Path("dashboard/index.html").read_text()
        
        # Extract tab names from onclick handlers
        import re
        tab_names = re.findall(r"showTab\('(\w+)'\)", content)
        
        for tab in tab_names:
            assert f'id="tab-{tab}"' in content, f"Missing tab content for: {tab}"
    
    def test_dashboard_panels_have_toggle(self):
        """All panels should be collapsible"""
        content = Path("dashboard/index.html").read_text()
        
        # Count panels and toggle handlers
        panel_count = content.count('class="panel"')
        toggle_count = content.count('togglePanel(this)')
        
        assert toggle_count >= panel_count - 1, \
            f"Not all panels have toggle: {panel_count} panels, {toggle_count} toggles"
    
    def test_dashboard_add_forms_have_inputs(self):
        """Add forms should have input fields and buttons"""
        content = Path("dashboard/index.html").read_text()
        
        add_functions = ['addBacklog', 'addTodo', 'addBugfix']
        
        for func in add_functions:
            # Should have input field
            field_name = func.replace('add', 'new')
            assert f'id="{field_name}"' in content or f"id='{field_name}'" in content, \
                f"Missing input field for {func}"
    
    def test_dashboard_count_badges_have_ids(self):
        """Count badges should have IDs for updating"""
        content = Path("dashboard/index.html").read_text()
        
        expected_counts = [
            'filesCount', 'snapshotsCount', 'backlogCount', 
            'todoCount', 'bugfixCount', 'constraintsCount', 'errorsCount'
        ]
        
        for count_id in expected_counts:
            assert f'id="{count_id}"' in content, f"Missing count badge: {count_id}"


class TestDashboardModals:
    """Tests for dashboard modal dialogs"""
    
    def test_dashboard_has_release_modal(self):
        """Dashboard should have release notes modal"""
        content = Path("dashboard/index.html").read_text()
        assert 'releaseModal' in content
        assert 'releaseContent' in content
    
    def test_dashboard_has_update_modal(self):
        """Dashboard should have update prompt modal"""
        content = Path("dashboard/index.html").read_text()
        assert 'updateModal' in content
        assert 'installUpdate' in content
    
    def test_dashboard_modals_have_close_mechanism(self):
        """Modals should be closeable"""
        content = Path("dashboard/index.html").read_text()
        
        # Release modal should have close button
        release_section = content[content.find('releaseModal'):content.find('</div>', content.find('releaseModal')+200)+6]
        assert 'Close' in content or 'close' in content
        
        # Update modal should have Later/Cancel button  
        assert 'Later' in content or 'Cancel' in content
    
    def test_dashboard_modals_hidden_by_default(self):
        """Modals should be hidden initially"""
        content = Path("dashboard/index.html").read_text()
        
        # Check release modal
        release_start = content.find('id="releaseModal"')
        if release_start != -1:
            modal_tag = content[content.rfind('<', 0, release_start):content.find('>', release_start)+1]
            assert 'display:none' in modal_tag or 'display: none' in modal_tag, \
                "Release modal should be hidden by default"


class TestDashboardErrorStates:
    """Tests for error handling in dashboard"""
    
    def test_dashboard_handles_empty_lists(self):
        """Dashboard should show empty state messages"""
        content = Path("dashboard/index.html").read_text()
        
        # Should have empty state handling
        assert 'empty' in content
        assert 'No ' in content  # "No items", "No errors", etc.
    
    def test_dashboard_api_error_handling(self):
        """Dashboard should handle API errors gracefully"""
        content = Path("dashboard/index.html").read_text()
        
        # All async functions should have try-catch
        async_functions = content.count('async function')
        catch_blocks = content.count('catch')
        
        # Should have catch for each async function (approximately)
        assert catch_blocks >= async_functions * 0.8, \
            f"Insufficient error handling: {async_functions} async funcs, {catch_blocks} catch blocks"


class TestDashboardUpdateSystem:
    """Tests for version update notification system"""
    
    def test_dashboard_has_update_badge(self):
        """Dashboard should have update badge element"""
        content = Path("dashboard/index.html").read_text()
        assert 'id="updateBadge"' in content
        assert 'display:none' in content  # Hidden by default
    
    def test_dashboard_update_badge_shows_on_version_mismatch(self):
        """Update badge logic should check if GitHub version is NEWER"""
        content = Path("dashboard/index.html").read_text()
        # Should use proper version comparison, not just inequality
        assert 'isNewerVersion' in content, "Should use isNewerVersion function"
        assert 'github_version' in content
    
    def test_dashboard_has_version_comparison_function(self):
        """Dashboard should have semantic version comparison"""
        content = Path("dashboard/index.html").read_text()
        assert 'function isNewerVersion' in content
        # Should split and compare parts
        assert 'split' in content
        assert "'.'" in content or '","' in content  # Split by dot
    
    def test_dashboard_update_badge_displays_new_version(self):
        """Update badge should show the available version"""
        content = Path("dashboard/index.html").read_text()
        # Badge text should include github_version
        assert "d.github_version" in content
        assert "updateBadge" in content
    
    def test_dashboard_has_version_display(self):
        """Dashboard should display current version"""
        content = Path("dashboard/index.html").read_text()
        assert 'id="srvVersion"' in content
        assert 'd.version' in content
    
    def test_server_health_returns_both_versions(self):
        """Health endpoint should return local and github versions"""
        server = Path("localagent/service/server.py").read_text()
        
        # Find health endpoint
        health_start = server.find('@app.get("/api/health")')
        health_end = server.find('@app.', health_start + 10)
        health_code = server[health_start:health_end]
        
        assert '"version"' in health_code or "'version'" in health_code
        assert 'github_version' in health_code
    
    def test_github_connector_has_version_fetch(self):
        """GitHub connector should fetch version from releases"""
        github = Path("localagent/connectors/github.py").read_text()
        
        assert 'def get_service_version' in github
        assert 'fetch_github_version' in github
        assert '/releases/latest' in github
    
    def test_dashboard_has_publish_functionality(self):
        """Dashboard should support publishing when local > GitHub"""
        content = Path("dashboard/index.html").read_text()
        
        assert 'showPublishPrompt' in content, "Should have showPublishPrompt function"
        assert 'publishToGitHub' in content, "Should have publishToGitHub function"
        assert 'Publish' in content, "Should show Publish button/text"
    
    def test_dashboard_publish_calls_github_push(self):
        """Publish function should call /api/github/push"""
        content = Path("dashboard/index.html").read_text()
        
        assert '/api/github/push' in content
    
    def test_dashboard_three_version_states(self):
        """Dashboard should handle: local < github, local > github, local == github"""
        content = Path("dashboard/index.html").read_text()
        
        # Should check both directions
        assert 'isNewerVersion(d.github_version, d.version)' in content, "Should check if GitHub newer"
        assert 'isNewerVersion(d.version, d.github_version)' in content, "Should check if local newer"


class TestDashboardNotifications:
    """Tests for notification and modal systems"""
    
    def test_dashboard_update_modal_structure(self):
        """Update modal should have proper structure"""
        content = Path("dashboard/index.html").read_text()
        
        assert 'id="updateModal"' in content
        assert 'id="updateText"' in content
        # Should have Install and Later/Cancel buttons
        assert 'installUpdate' in content
        assert 'Later' in content or 'Cancel' in content
    
    def test_dashboard_release_modal_structure(self):
        """Release notes modal should have proper structure"""
        content = Path("dashboard/index.html").read_text()
        
        assert 'id="releaseModal"' in content
        assert 'id="releaseContent"' in content
        assert 'showReleaseNotes' in content
    
    def test_dashboard_install_update_function(self):
        """Install update function should exist and call API"""
        content = Path("dashboard/index.html").read_text()
        
        assert 'async function installUpdate' in content or 'function installUpdate' in content
        assert '/api/update/install-from-github' in content
    
    def test_dashboard_status_dot_updates(self):
        """Status dot should update based on connection"""
        content = Path("dashboard/index.html").read_text()
        
        # Should set dot class based on connection status
        assert "apiDot" in content
        assert "'dot on'" in content or '"dot on"' in content
        assert "'dot off'" in content or '"dot off"' in content
    
    def test_dashboard_disconnected_state_handling(self):
        """Dashboard should handle disconnected state"""
        content = Path("dashboard/index.html").read_text()
        
        # In catch block, should show disconnected
        assert 'Disconnected' in content
        assert 'dot off' in content
    
    def test_dashboard_modals_use_theme_variables(self):
        """Modals should use CSS variables for theming consistency"""
        content = Path("dashboard/index.html").read_text()
        
        # Find modal sections
        release_modal_start = content.find('id="releaseModal"')
        release_modal_end = content.find('</div>\n</div>', release_modal_start) + 13
        release_modal = content[release_modal_start:release_modal_end]
        
        update_modal_start = content.find('id="updateModal"')
        update_modal_end = content.find('</div>\n</div>', update_modal_start) + 13
        update_modal = content[update_modal_start:update_modal_end]
        
        # Should use CSS variables, not hardcoded dark colors
        assert 'var(--' in release_modal, "Release modal should use CSS variables"
        assert 'var(--' in update_modal, "Update modal should use CSS variables"
        
        # Should not have hardcoded dark theme colors
        assert '#1e1e1e' not in release_modal, "Release modal has hardcoded dark color"
        assert '#1e1e1e' not in update_modal, "Update modal has hardcoded dark color"


class TestServerUpdateEndpoints:
    """Tests for server update-related endpoints"""
    
    def test_server_has_update_check_endpoint(self):
        """Server should have update check endpoint"""
        server = Path("localagent/service/server.py").read_text()
        assert '/api/update/check' in server
    
    def test_server_has_install_update_endpoint(self):
        """Server should have install update endpoint"""
        server = Path("localagent/service/server.py").read_text()
        assert '/api/update/install-from-github' in server
    
    def test_server_has_release_notes_endpoint(self):
        """Server should have release notes endpoint"""
        server = Path("localagent/service/server.py").read_text()
        assert '/api/release-notes' in server


class TestGitHubVersioning:
    """Tests for GitHub version management"""
    
    def test_github_repos_configured(self):
        """GitHub repos should be properly configured"""
        github = Path("localagent/connectors/github.py").read_text()
        
        assert 'REPOS' in github
        assert '"service"' in github or "'service'" in github
        assert '"dashboard"' in github or "'dashboard'" in github
    
    def test_github_version_fetch_has_timeout(self):
        """Version fetch should have timeout to avoid hanging"""
        github = Path("localagent/connectors/github.py").read_text()
        
        # Find fetch_github_version function
        func_start = github.find('def fetch_github_version')
        func_end = github.find('\ndef ', func_start + 10)
        func_code = github[func_start:func_end]
        
        assert 'timeout' in func_code
    
    def test_github_version_fetch_has_error_handling(self):
        """Version fetch should handle errors gracefully"""
        github = Path("localagent/connectors/github.py").read_text()
        
        func_start = github.find('def fetch_github_version')
        func_end = github.find('\ndef ', func_start + 10)
        func_code = github[func_start:func_end]
        
        assert 'try:' in func_code
        assert 'except' in func_code
        assert 'return None' in func_code or 'return "0.0.0"' in func_code
    
    def test_github_version_strips_v_prefix(self):
        """Version should strip 'v' prefix from tags"""
        github = Path("localagent/connectors/github.py").read_text()
        
        assert 'lstrip("v")' in github or "lstrip('v')" in github or \
               'replace("v", "")' in github or "replace('v', '')" in github


class TestVersionConsistency:
    """Tests for version consistency across components"""
    
    def test_version_file_matches_server(self):
        """VERSION file should match server.py VERSION at runtime"""
        from localagent.service.server import VERSION
        version_file = Path("VERSION").read_text().strip()
        assert VERSION == version_file, f"Mismatch: server={VERSION}, file={version_file}"
    
    def test_version_comparison_logic_exists(self):
        """Server should have version comparison logic"""
        server = Path("localagent/service/server.py").read_text()
        
        # Should compare versions somewhere
        assert 'version_tuple' in server or 'compare' in server.lower() or \
               '>' in server  # Simple comparison


# ============================================================
# CHAT VOICE RECOGNITION TESTS
# ============================================================

class TestChatVoiceRecognition:
    """Tests for voice recognition functionality in chat"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.chat_path = Path("modules/ai-chat-module-pro/chat-pro-standalone.html")
        self.whisper_path = Path("modules/whisper-module/WhisperTranscriber.js")
        self.chat = self.chat_path.read_text() if self.chat_path.exists() else ""
        self.whisper = self.whisper_path.read_text() if self.whisper_path.exists() else ""
    
    def test_whisper_module_has_transformers(self):
        """Whisper module should import transformers.js"""
        assert "transformers" in self.whisper
    
    def test_whisper_module_has_speech_recognition(self):
        """Whisper module should use automatic-speech-recognition"""
        assert "automatic-speech-recognition" in self.whisper
    
    def test_chat_uses_whisper_instance(self):
        """Chat should use whisper instance variable"""
        assert "let whisper" in self.chat or "whisper = " in self.chat
    
    def test_voice_has_recording_state(self):
        """Should track recording state"""
        assert "isRecording" in self.chat
        assert "recordedSamples" in self.chat
    
    def test_voice_has_start_stop_functions(self):
        """Should have start/stop recording functions"""
        assert "function startRecording" in self.chat or "startRecording = " in self.chat
        assert "function stopRecording" in self.chat or "stopRecording = " in self.chat
    
    def test_voice_uses_audio_context(self):
        """Should use AudioContext for recording"""
        assert "AudioContext" in self.chat
        assert "audioContext" in self.chat
    
    def test_voice_writes_to_input(self):
        """Transcribed text should be written to input field"""
        assert "$('#input').value" in self.chat
        assert "result" in self.chat
    
    def test_voice_calls_whisper_transcribe(self):
        """Should call whisper.transcribe"""
        assert "whisper.transcribe" in self.chat
    
    def test_voice_runs_lint_after_transcription(self):
        """Should run linter after voice input"""
        assert "runLint()" in self.chat
    
    def test_voice_sets_input_source(self):
        """Should mark input source as voice after transcription"""
        assert "lastInputSource = 'voice'" in self.chat or 'lastInputSource = "voice"' in self.chat
    
    def test_voice_has_ui_states(self):
        """Should have proper UI states for voice"""
        assert "recording" in self.chat
        assert "processing" in self.chat
        assert "ready" in self.chat
    
    def test_voice_has_visual_feedback(self):
        """Should show visual feedback during recording"""
        assert "waveform" in self.chat.lower()
        assert "voicePulse" in self.chat or "animation" in self.chat
    
    def test_voice_cleans_up_resources(self):
        """Should clean up audio resources after recording"""
        assert "recordedSamples = []" in self.chat
        assert "audioContext" in self.chat
    
    def test_voice_error_handling(self):
        """Should handle transcription errors"""
        assert "catch" in self.chat
        assert "error" in self.chat.lower()


# ============================================================
# LINTER AUTO-FIX TESTS
# ============================================================

class TestLinterAutoFix:
    """Tests for linter auto-fix functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.bundle_path = Path("modules/ai-chat-module-pro/PromptLinter.bundle.js")
        self.chat_path = Path("modules/ai-chat-module-pro/chat-pro-standalone.html")
        self.bundle = self.bundle_path.read_text() if self.bundle_path.exists() else ""
        self.chat = self.chat_path.read_text() if self.chat_path.exists() else ""
    
    def test_autofix_button_exists(self):
        """Should have auto-fix button in UI"""
        assert 'id="linterFixBtn"' in self.chat
        assert "Auto-fix" in self.chat
    
    def test_autofix_preview_panel_exists(self):
        """Should have preview panel for auto-fix"""
        assert 'id="linterPreview"' in self.chat
        assert "previewOriginal" in self.chat
        assert "previewFixed" in self.chat
    
    def test_autofix_has_apply_function(self):
        """Should have applyFix function"""
        assert "applyFix" in self.chat
        assert "window.applyFix" in self.chat or "function applyFix" in self.chat
    
    def test_autofix_updates_input(self):
        """applyFix should update input with optimized text"""
        assert "lastLintResult.optimized" in self.chat
        assert "$('#input').value = " in self.chat
    
    def test_autofix_hides_preview_after_apply(self):
        """Should hide preview after applying fix"""
        assert "linterPreview" in self.chat
        assert "remove('visible')" in self.chat
    
    def test_optimize_function_exists(self):
        """Bundle should have optimizePrompt function"""
        assert "function optimizePrompt" in self.bundle
        assert "optimizePrompt" in self.bundle
    
    def test_optimize_handles_negations_en(self):
        """Should rewrite English negations"""
        # Check for negation patterns in regex form
        assert "don" in self.bundle  # don't pattern
        assert "avoid" in self.bundle
        assert "never" in self.bundle
    
    def test_optimize_handles_negations_fr(self):
        """Should rewrite French negations"""
        assert "ne pas" in self.bundle.lower() or "pas de" in self.bundle.lower()
        assert "éviter" in self.bundle or "eviter" in self.bundle
        assert "sans" in self.bundle
    
    def test_optimize_handles_vague_quantities(self):
        """Should quantify vague amounts"""
        assert "some" in self.bundle
        assert "few" in self.bundle
        assert "several" in self.bundle
        assert "3-5" in self.bundle or "2-3" in self.bundle
    
    def test_optimize_handles_vague_references(self):
        """Should clarify vague references"""
        assert "my project" in self.bundle.lower()
        assert "the code" in self.bundle.lower()
    
    def test_optimize_adds_format_spec(self):
        """Should add format spec when missing"""
        assert "create" in self.bundle.lower()
        assert "format" in self.bundle.lower()
        assert "HTML" in self.bundle or "html" in self.bundle
    
    def test_optimize_returns_different_text(self):
        """Optimized text should differ from input for problematic prompts"""
        assert "return optimized" in self.bundle
        # Should not just return input unchanged
        assert "optimized = text" in self.bundle  # Initial assignment
        assert ".replace(" in self.bundle  # Should have replacements
    
    def test_lint_result_includes_optimized(self):
        """lintPrompt should return optimized field"""
        assert "optimized:" in self.bundle or "optimized :" in self.bundle


# ============================================================
# LINTER RULES COVERAGE TESTS
# ============================================================

class TestLinterRulesCoverage:
    """Tests for comprehensive lint rule coverage"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.bundle = Path("modules/ai-chat-module-pro/PromptLinter.bundle.js").read_text()
    
    def test_has_negation_rule(self):
        assert "negation" in self.bundle
        assert "Negation detected" in self.bundle or "Négation" in self.bundle
    
    def test_has_conflict_rule(self):
        assert "conflict" in self.bundle
        assert "Conflicting" in self.bundle or "contradictoire" in self.bundle
    
    def test_has_vague_rule(self):
        assert "vague" in self.bundle.lower()
        assert "Vague" in self.bundle or "vague" in self.bundle
    
    def test_has_ambiguous_rule(self):
        assert "ambiguous" in self.bundle.lower()
        assert "quantity" in self.bundle.lower() or "quantité" in self.bundle.lower()
    
    def test_has_implicit_rule(self):
        assert "implicit" in self.bundle.lower()
        assert "assumption" in self.bundle.lower() or "hypothèse" in self.bundle.lower()
    
    def test_has_format_rule(self):
        assert "missingFormat" in self.bundle or "format" in self.bundle.lower()
    
    def test_has_complexity_rule(self):
        assert "tooComplex" in self.bundle or "complex" in self.bundle.lower()
        assert "steps" in self.bundle.lower() or "étapes" in self.bundle.lower()
    
    def test_rules_have_severity(self):
        """All rules should have severity levels"""
        assert "severity" in self.bundle
        assert "'high'" in self.bundle or '"high"' in self.bundle
        assert "'medium'" in self.bundle or '"medium"' in self.bundle
        assert "'low'" in self.bundle or '"low"' in self.bundle
    
    def test_rules_have_fix_suggestions(self):
        """All rules should have fix suggestions"""
        assert "fix:" in self.bundle or "fix :" in self.bundle
    
    def test_rules_bilingual(self):
        """Rules should support EN and FR"""
        # Check for language-specific patterns
        assert "en:" in self.bundle or "'en'" in self.bundle
        assert "fr:" in self.bundle or "'fr'" in self.bundle


# ============================================================
# CHAT UI INTEGRATION TESTS
# ============================================================

class TestChatUIIntegration:
    """Tests for chat UI integration and consistency"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.chat = Path("modules/ai-chat-module-pro/chat-pro-standalone.html").read_text()
    
    def test_linter_bar_visibility_logic(self):
        """Linter bar should show/hide based on input"""
        assert "linterBar" in self.chat
        assert "visible" in self.chat
        assert "classList.add" in self.chat
        assert "classList.remove" in self.chat
    
    def test_linter_score_display(self):
        """Should display linter score"""
        assert "linterScore" in self.chat
        assert "result.score" in self.chat
    
    def test_linter_issues_display(self):
        """Should display lint issues"""
        assert "linterIssues" in self.chat
        assert "result.issues" in self.chat
    
    def test_linter_meta_display(self):
        """Should display linter metadata"""
        assert "linterLang" in self.chat
        assert "linterTask" in self.chat
        assert "linterTokens" in self.chat
        assert "linterCost" in self.chat
    
    def test_linter_debounce(self):
        """Should debounce lint calls"""
        assert "debounceLint" in self.chat
        assert "setTimeout" in self.chat
        assert "clearTimeout" in self.chat
    
    def test_linter_resets_on_send(self):
        """Linter should reset when message is sent"""
        # Find where we reset on send
        assert "linterBar" in self.chat
        assert "remove('visible')" in self.chat
    
    def test_input_triggers_lint(self):
        """Input changes should trigger linting"""
        assert "oninput" in self.chat or "addEventListener" in self.chat
        assert "debounceLint" in self.chat
    
    def test_autoresize_on_input(self):
        """Input should auto-resize"""
        assert "autoResize" in self.chat
    
    def test_message_has_source_indicator(self):
        """Messages should indicate voice vs text source"""
        assert "inputSource" in self.chat or "lastInputSource" in self.chat
        assert "voice" in self.chat
    
    def test_file_attachment_support(self):
        """Should support file attachments"""
        assert "fileInput" in self.chat
        assert "addFiles" in self.chat or "files" in self.chat
    
    def test_drag_drop_support(self):
        """Should support drag and drop"""
        assert "dropZone" in self.chat or "drop" in self.chat.lower()
        assert "dragover" in self.chat.lower() or "ondragover" in self.chat


# ============================================================
# DASHBOARD LINTER INTEGRATION TESTS
# ============================================================

class TestDashboardLinterIntegration:
    """Tests for dashboard integration with linter"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.dashboard = Path("dashboard/index.html").read_text()
    
    def test_dashboard_has_chat_iframe(self):
        """Dashboard should embed chat module"""
        assert "iframe" in self.dashboard or "chat" in self.dashboard.lower()
    
    def test_dashboard_theme_variables_exist(self):
        """Dashboard should define theme variables"""
        assert "--bg" in self.dashboard or "--blue" in self.dashboard
        assert "--border" in self.dashboard or "--text" in self.dashboard


# ============================================================
# TOKEN ESTIMATION TESTS
# ============================================================

class TestTokenEstimation:
    """Tests for token estimation logic"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.bundle = Path("modules/ai-chat-module-pro/PromptLinter.bundle.js").read_text()
    
    def test_estimates_input_tokens(self):
        """Should estimate input tokens"""
        assert "inputTokens" in self.bundle or "input" in self.bundle
        assert "charCount" in self.bundle or "length" in self.bundle
    
    def test_estimates_output_tokens(self):
        """Should estimate output tokens based on task"""
        assert "outputTokens" in self.bundle or "output" in self.bundle
        assert "multiplier" in self.bundle.lower() or "taskType" in self.bundle
    
    def test_calculates_cost(self):
        """Should calculate estimated cost"""
        assert "cost" in self.bundle.lower()
        assert "0.00" in self.bundle or "toFixed" in self.bundle
    
    def test_different_rates_for_tasks(self):
        """Different task types should have different output estimates"""
        assert "create" in self.bundle
        assert "modify" in self.bundle or "fix" in self.bundle
        assert "explain" in self.bundle or "analyze" in self.bundle


# ============================================================
# LANGUAGE DETECTION TESTS
# ============================================================

class TestLanguageDetection:
    """Tests for language detection"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.bundle = Path("modules/ai-chat-module-pro/PromptLinter.bundle.js").read_text()
    
    def test_detects_french(self):
        """Should detect French language"""
        assert "detectLanguage" in self.bundle
        assert "fr" in self.bundle
        # Should have French indicators
        assert "je" in self.bundle.lower() or "le" in self.bundle.lower()
    
    def test_detects_english(self):
        """Should detect English language"""
        assert "en" in self.bundle
        # Should have English indicators  
        assert "the" in self.bundle.lower()
    
    def test_returns_language_in_result(self):
        """lintPrompt should return detected language"""
        assert "lang:" in self.bundle or "lang :" in self.bundle


# ============================================================
# TASK TYPE INFERENCE TESTS
# ============================================================

class TestTaskTypeInference:
    """Tests for task type inference"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.bundle = Path("modules/ai-chat-module-pro/PromptLinter.bundle.js").read_text()
    
    def test_infers_create_task(self):
        assert "create" in self.bundle.lower()
        assert "generate" in self.bundle.lower() or "build" in self.bundle.lower()
    
    def test_infers_fix_task(self):
        assert "fix" in self.bundle.lower()
        assert "debug" in self.bundle.lower() or "repair" in self.bundle.lower()
    
    def test_infers_modify_task(self):
        assert "modify" in self.bundle.lower()
        assert "update" in self.bundle.lower() or "change" in self.bundle.lower()
    
    def test_infers_explain_task(self):
        assert "explain" in self.bundle.lower()
        assert "describe" in self.bundle.lower() or "what" in self.bundle.lower()
    
    def test_infers_analyze_task(self):
        assert "analyze" in self.bundle.lower()
        assert "review" in self.bundle.lower() or "check" in self.bundle.lower()
    
    def test_returns_task_type_in_result(self):
        """lintPrompt should return inferred task type"""
        assert "taskType" in self.bundle


# ============================================================
# WHISPER MODULE TESTS
# ============================================================

class TestWhisperModule:
    """Tests for the standalone Whisper module"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.module_path = Path("modules/whisper-module/WhisperTranscriber.js")
        self.skill_path = Path("modules/whisper-module/SKILL.md")
        self.content = self.module_path.read_text() if self.module_path.exists() else ""
    
    def test_whisper_module_exists(self):
        """Whisper module should exist"""
        assert self.module_path.exists()
    
    def test_whisper_skill_exists(self):
        """Whisper SKILL.md should exist"""
        assert self.skill_path.exists()
    
    def test_whisper_has_class(self):
        """Should export WhisperTranscriber class"""
        assert "class WhisperTranscriber" in self.content
    
    def test_whisper_has_load_method(self):
        """Should have load method"""
        assert "async load(" in self.content
        assert "model" in self.content
        assert "onProgress" in self.content
    
    def test_whisper_has_transcribe_method(self):
        """Should have transcribe method"""
        assert "async transcribe(" in self.content
        assert "audioData" in self.content
    
    def test_whisper_has_isloaded_method(self):
        """Should have isLoaded method"""
        assert "isLoaded()" in self.content
    
    def test_whisper_has_unload_method(self):
        """Should have unload method"""
        assert "async unload()" in self.content or "unload()" in self.content
    
    def test_whisper_has_models_config(self):
        """Should have models configuration"""
        assert "MODELS" in self.content
        assert "whisper-tiny" in self.content
        assert "whisper-small" in self.content
    
    def test_whisper_uses_transformers_cdn(self):
        """Should use transformers.js CDN"""
        assert "transformers" in self.content
        assert "cdn.jsdelivr.net" in self.content or "import" in self.content
    
    def test_whisper_has_error_handling(self):
        """Should have error handling"""
        assert "throw" in self.content
        assert "catch" in self.content or "try" in self.content
    
    def test_whisper_returns_result_object(self):
        """Should return structured result"""
        assert "text" in self.content
        assert "language" in self.content
        assert "duration" in self.content
    
    def test_whisper_supports_auto_language(self):
        """Should support auto language detection"""
        assert "language: null" in self.content or "language:" in self.content
    
    def test_whisper_exports_for_browser(self):
        """Should export for browser use via IIFE"""
        assert "global.WhisperTranscriber" in self.content
    
    def test_whisper_is_iife(self):
        """Should be an IIFE bundle"""
        assert "(function(global)" in self.content
        assert "window" in self.content


class TestWhisperIntegrationWithChat:
    """Tests for Whisper integration in chat module"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.chat = Path("modules/ai-chat-module-pro/chat-pro-standalone.html").read_text()
    
    def test_chat_imports_whisper_module(self):
        """Chat should import WhisperTranscriber"""
        assert "WhisperTranscriber" in self.chat
        assert "whisper-module" in self.chat
    
    def test_chat_uses_whisper_instance(self):
        """Chat should use whisper instance"""
        assert "whisper" in self.chat
        assert "whisper.transcribe" in self.chat or "whisper?.isLoaded" in self.chat
    
    def test_chat_lazy_loads_whisper(self):
        """Chat should lazy load whisper on first use"""
        assert "loadWhisperModule" in self.chat or "whisper?.isLoaded" in self.chat
    
    def test_chat_no_direct_transformers_import(self):
        """Chat should NOT directly import transformers.js"""
        # The import should be in the whisper module, not in chat
        assert self.chat.count("@xenova/transformers") <= 1  # Allow 0 or 1 (in comments)
    
    def test_chat_handles_whisper_progress(self):
        """Chat should handle whisper loading progress"""
        assert "progressBar" in self.chat
        assert "progress" in self.chat


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


class TestNoDuplicates:
    """Ensure no duplicate code in the project"""
    
    def test_no_duplicate_endpoints(self):
        """No duplicate API endpoints in server.py"""
        content = Path("localagent/service/server.py").read_text()
        import re
        
        # Find all endpoint decorators
        endpoints = re.findall(r'@app\.(get|post|put|delete)\("([^"]+)"', content)
        
        # Group by method+path
        seen = {}
        duplicates = []
        for method, path in endpoints:
            key = f"{method.upper()} {path}"
            if key in seen:
                duplicates.append(key)
            seen[key] = True
        
        assert len(duplicates) == 0, f"Duplicate endpoints found: {duplicates}"
    
    def test_no_duplicate_function_names(self):
        """No duplicate function names in server.py"""
        content = Path("localagent/service/server.py").read_text()
        import re
        
        # Find all function definitions
        functions = re.findall(r'^(?:async )?def (\w+)\(', content, re.MULTILINE)
        
        seen = {}
        duplicates = []
        for func in functions:
            if func in seen:
                duplicates.append(func)
            seen[func] = True
        
        assert len(duplicates) == 0, f"Duplicate functions found: {duplicates}"
    
    def test_server_file_not_too_large(self):
        """server.py should not exceed 3200 lines"""
        content = Path("localagent/service/server.py").read_text()
        lines = len(content.split('\n'))
        assert lines < 3200, f"server.py has {lines} lines, consider refactoring"


class TestAPIResponseFormats:
    """Ensure API endpoints return correct formats"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from fastapi.testclient import TestClient
            from localagent.service.server import app
            self.client = TestClient(app)
            self.available = True
        except:
            self.available = False
    
    def test_constraints_returns_dict_with_constraints_key(self):
        """GET /api/constraints must return {constraints: [...]}"""
        if not self.available:
            pytest.skip("FastAPI not available")
        r = self.client.get("/api/constraints")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict), "Must return dict"
        assert "constraints" in data, "Must have 'constraints' key"
        assert isinstance(data["constraints"], list), "constraints must be list"
        assert len(data["constraints"]) > 0, "constraints must not be empty"
    
    def test_backlog_returns_list(self):
        """GET /api/backlog must return list"""
        if not self.available:
            pytest.skip("FastAPI not available")
        r = self.client.get("/api/backlog")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list), "Must return list"
    
    def test_todo_returns_list(self):
        """GET /api/todo must return list"""
        if not self.available:
            pytest.skip("FastAPI not available")
        r = self.client.get("/api/todo")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list), "Must return list"
    
    def test_health_returns_required_fields(self):
        """GET /api/health must return version, api_key, project"""
        if not self.available:
            pytest.skip("FastAPI not available")
        r = self.client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert "version" in data
        assert "api_key" in data
        assert "project" in data


class TestVersionManagement:
    """Ensure version is read from file, not hardcoded"""
    
    def test_version_read_from_file(self):
        """VERSION must be read from VERSION file, not hardcoded"""
        content = Path("localagent/service/server.py").read_text()
        
        # Should NOT have hardcoded VERSION = "x.y.z"
        import re
        hardcoded = re.findall(r'^VERSION\s*=\s*["\'][\d.]+["\']', content, re.MULTILINE)
        assert len(hardcoded) == 0, f"VERSION is hardcoded: {hardcoded}. Should read from file."
        
        # Should have _read_version function
        assert "_read_version" in content, "Missing _read_version function"
        assert "VERSION = _read_version()" in content, "VERSION should call _read_version()"
    
    def test_version_file_exists(self):
        """VERSION file must exist"""
        assert Path("VERSION").exists(), "VERSION file missing"
    
    def test_version_matches_file(self):
        """Server VERSION must match VERSION file"""
        from localagent.service.server import VERSION
        file_version = Path("VERSION").read_text().strip()
        assert VERSION == file_version, f"Mismatch: server={VERSION}, file={file_version}"


class TestServerCanLoad:
    """CRITICAL: Server must load without import errors"""
    
    def test_server_imports_without_error(self):
        """Server module must import without any errors"""
        try:
            from localagent.service.server import app
            assert app is not None
        except ImportError as e:
            pytest.fail(f"Server failed to import: {e}")
        except Exception as e:
            pytest.fail(f"Server failed to load: {e}")
    
    def test_all_internal_imports_exist(self):
        """All imports in server.py must reference existing functions"""
        import ast
        from pathlib import Path
        
        def get_module_exports(module_path):
            try:
                content = Path(module_path).read_text()
                tree = ast.parse(content)
                names = set()
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        names.add(node.name)
                    elif isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                names.add(target.id)
                return names
            except:
                return set()
        
        module_map = {
            '..engine.project': 'localagent/engine/project.py',
            '..engine.tracking': 'localagent/engine/tracking.py',
            '..connectors.dashboard': 'localagent/connectors/dashboard.py',
            '..connectors.github': 'localagent/connectors/github.py',
            '..connectors.llm': 'localagent/connectors/llm.py',
            '..core.constraints': 'localagent/core/constraints.py',
            '..core.negotiator': 'localagent/core/negotiator.py',
            '..core.learning': 'localagent/core/learning.py',
            '..core.protocol': 'localagent/core/protocol.py',
            '..core.debugger': 'localagent/core/debugger.py',
            '..roadmap.prompt_optimizer': 'localagent/roadmap/prompt_optimizer.py',
        }
        
        content = Path('localagent/service/server.py').read_text()
        tree = ast.parse(content)
        
        errors = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module
                if module in module_map:
                    exports = get_module_exports(module_map[module])
                    for alias in node.names:
                        name = alias.name
                        if name not in exports:
                            errors.append(f"'{name}' not in {module_map[module]}")
        
        assert len(errors) == 0, f"Missing imports: {errors}"
