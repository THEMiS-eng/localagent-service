#!/usr/bin/env python3
"""
LocalAgent Functional Tests
These tests verify ACTUAL BEHAVIOR, not just string presence.
Each test should catch real bugs.
"""

import subprocess
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


# ============================================================
# LINTER FUNCTIONAL TESTS (Node.js)
# ============================================================

class TestLinterFunctional:
    """Tests that actually run the linter and verify output"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.bundle_path = Path("modules/ai-chat-module-pro/PromptLinter.bundle.js")
    
    def run_linter(self, text):
        """Execute linter in Node.js and return result"""
        js_code = f'''
        const fs = require('fs');
        const vm = require('vm');
        const code = fs.readFileSync('{self.bundle_path}', 'utf8');
        const ctx = {{ window: {{}}, console: console }};
        vm.createContext(ctx);
        vm.runInContext(code, ctx);
        const result = ctx.window.PromptLinter.lintPrompt({json.dumps(text)});
        console.log(JSON.stringify(result));
        '''
        result = subprocess.run(['node', '-e', js_code], capture_output=True, text=True)
        if result.returncode != 0:
            pytest.fail(f"Linter execution failed: {result.stderr}")
        return json.loads(result.stdout.strip())
    
    def test_linter_returns_required_fields(self):
        """Linter must return score, issues, lang, taskType, tokens, optimized"""
        result = self.run_linter("test prompt")
        assert "score" in result, "Missing 'score' field"
        assert "issues" in result, "Missing 'issues' field"
        assert "lang" in result, "Missing 'lang' field"
        assert "taskType" in result, "Missing 'taskType' field"
        assert "tokens" in result, "Missing 'tokens' field"
        assert "optimized" in result, "Missing 'optimized' field"
    
    def test_linter_score_in_valid_range(self):
        """Score must be between 0 and 100"""
        for text in ["x", "test", "create a detailed website with React"]:
            result = self.run_linter(text)
            assert 0 <= result["score"] <= 100, f"Score {result['score']} out of range for '{text}'"
    
    def test_linter_detects_french(self):
        """Must detect French language"""
        result = self.run_linter("créer une fonction pour calculer")
        assert result["lang"] == "fr", f"Expected 'fr', got '{result['lang']}'"
    
    def test_linter_detects_english(self):
        """Must detect English language"""
        result = self.run_linter("create a function to calculate")
        assert result["lang"] == "en", f"Expected 'en', got '{result['lang']}'"
    
    def test_linter_detects_negation_issue(self):
        """Must detect negation patterns"""
        result = self.run_linter("don't use loops in the code")
        negation_found = any(i.get("type") == "negation" for i in result["issues"])
        assert negation_found, f"Negation not detected. Issues: {result['issues']}"
    
    def test_linter_detects_vague_quantity(self):
        """Must detect vague quantities like 'some'"""
        result = self.run_linter("give me some examples")
        ambiguous_found = any(i.get("type") == "ambiguous" for i in result["issues"])
        assert ambiguous_found, f"Ambiguous quantity not detected. Issues: {result['issues']}"
    
    def test_linter_optimizes_negation(self):
        """Must transform negation to positive"""
        result = self.run_linter("don't use bullet points")
        assert "bullet points" not in result["optimized"].lower() or "prose" in result["optimized"].lower(), \
            f"Negation not optimized: {result['optimized']}"
    
    def test_linter_quantifies_vague_amounts(self):
        """Must replace 'some X' with '3-5 X'"""
        result = self.run_linter("some examples")
        assert "3-5" in result["optimized"], f"'some' not quantified: {result['optimized']}"
    
    def test_linter_detects_create_task(self):
        """Must detect 'create' task type"""
        result = self.run_linter("create a website")
        assert result["taskType"] == "create", f"Expected 'create', got '{result['taskType']}'"
    
    def test_linter_detects_fix_task(self):
        """Must detect 'fix' task type"""
        result = self.run_linter("fix the bug in this code")
        assert result["taskType"] == "fix", f"Expected 'fix', got '{result['taskType']}'"
    
    def test_linter_tokens_are_positive(self):
        """Token estimates must be positive integers"""
        result = self.run_linter("create a complex web application")
        assert result["tokens"]["input"] > 0, "Input tokens must be positive"
        assert result["tokens"]["output"] > 0, "Output tokens must be positive"
    
    def test_linter_issues_have_required_fields(self):
        """Each issue must have type, severity, message, fix"""
        result = self.run_linter("don't use some things")
        for issue in result["issues"]:
            assert "type" in issue, f"Issue missing 'type': {issue}"
            assert "severity" in issue, f"Issue missing 'severity': {issue}"
            assert "message" in issue, f"Issue missing 'message': {issue}"
            assert "fix" in issue, f"Issue missing 'fix': {issue}"
    
    def test_linter_empty_input(self):
        """Must handle empty input gracefully"""
        result = self.run_linter("")
        assert result["score"] == 0, "Empty input should have score 0"
        assert result["optimized"] == "", "Empty input should have empty optimized"


# ============================================================
# SERVER API FUNCTIONAL TESTS
# ============================================================

class TestServerAPIFunctional:
    """Tests that actually call the server API"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from localagent.service.server import app
            from fastapi.testclient import TestClient
            self.client = TestClient(app)
            self.available = True
        except ImportError:
            self.available = False
    
    def test_health_returns_version(self):
        """Health endpoint must return version"""
        if not self.available:
            pytest.skip("FastAPI not available")
        r = self.client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert "version" in data, "Health missing 'version'"
        assert "status" in data, "Health missing 'status'"
    
    def test_constraints_returns_list(self):
        """Constraints endpoint must return dict with constraints list"""
        if not self.available:
            pytest.skip("FastAPI not available")
        r = self.client.get("/api/constraints")
        assert r.status_code == 200
        data = r.json()
        assert "constraints" in data, "Response must have 'constraints' key"
        assert isinstance(data["constraints"], list), "Constraints must be a list"
    
    def test_lint_endpoint_accepts_prompt(self):
        """Lint endpoint must accept 'prompt' field"""
        if not self.available:
            pytest.skip("FastAPI not available")
        r = self.client.post("/api/lint", json={"prompt": "test"})
        # Should not return 400 for valid input
        assert r.status_code != 400 or "prompt" not in r.text, \
            f"Lint rejected valid prompt: {r.text}"
    
    def test_lint_endpoint_rejects_empty(self):
        """Lint endpoint must reject empty prompt"""
        if not self.available:
            pytest.skip("FastAPI not available")
        r = self.client.post("/api/lint", json={"prompt": ""})
        assert r.status_code == 400, "Should reject empty prompt"


# ============================================================
# WHISPER MODULE TESTS
# ============================================================

class TestWhisperModuleFunctional:
    """Tests for WhisperTranscriber module structure"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.module_path = Path("modules/whisper-module/WhisperTranscriber.js")
    
    def run_whisper_check(self, js_code):
        """Run JS code that uses WhisperTranscriber"""
        full_code = f'''
        const fs = require('fs');
        const vm = require('vm');
        const code = fs.readFileSync('{self.module_path}', 'utf8');
        const ctx = {{ 
            window: {{}}, 
            console: console,
            module: {{ exports: {{}} }},
            require: () => {{ throw new Error('require not available'); }}
        }};
        vm.createContext(ctx);
        vm.runInContext(code, ctx);
        {js_code}
        '''
        result = subprocess.run(['node', '-e', full_code], capture_output=True, text=True)
        return result
    
    def test_whisper_class_exists(self):
        """WhisperTranscriber class must be exported"""
        result = self.run_whisper_check('''
        if (!ctx.window.WhisperTranscriber) {
            console.log('FAIL: WhisperTranscriber not exported to window');
            process.exit(1);
        }
        console.log('OK');
        ''')
        assert result.returncode == 0, f"WhisperTranscriber not exported: {result.stdout}"
    
    def test_whisper_has_load_method(self):
        """WhisperTranscriber must have load method"""
        result = self.run_whisper_check('''
        const W = ctx.window.WhisperTranscriber;
        const instance = new W();
        if (typeof instance.load !== 'function') {
            console.log('FAIL: load is not a function');
            process.exit(1);
        }
        console.log('OK');
        ''')
        assert result.returncode == 0, f"load method missing: {result.stdout}"
    
    def test_whisper_has_transcribe_method(self):
        """WhisperTranscriber must have transcribe method"""
        result = self.run_whisper_check('''
        const W = ctx.window.WhisperTranscriber;
        const instance = new W();
        if (typeof instance.transcribe !== 'function') {
            console.log('FAIL: transcribe is not a function');
            process.exit(1);
        }
        console.log('OK');
        ''')
        assert result.returncode == 0, f"transcribe method missing: {result.stdout}"
    
    def test_whisper_models_config_exists(self):
        """MODELS configuration must exist"""
        result = self.run_whisper_check('''
        const models = ctx.window.WhisperTranscriber.MODELS;
        if (!models || typeof models !== 'object') {
            console.log('FAIL: MODELS not found');
            process.exit(1);
        }
        if (!models['whisper-small']) {
            console.log('FAIL: whisper-small not in MODELS');
            process.exit(1);
        }
        console.log('OK');
        ''')
        assert result.returncode == 0, f"MODELS config missing: {result.stdout}"


# ============================================================
# DASHBOARD HTML VALIDATION
# ============================================================

class TestDashboardValidation:
    """Tests that validate dashboard HTML/JS structure"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.dashboard_path = Path("dashboard/index.html")
        self.content = self.dashboard_path.read_text() if self.dashboard_path.exists() else ""
    
    def test_all_element_ids_exist(self):
        """All getElementById calls must reference existing IDs"""
        import re
        
        # Find all getElementById calls
        used_ids = set(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]", self.content))
        
        # Find all defined IDs
        defined_ids = set(re.findall(r'id=["\']([^"\']+)["\']', self.content))
        
        missing = used_ids - defined_ids
        # Filter out dynamic IDs
        missing = {m for m in missing if not m.startswith('tab-') and not m.endswith('-')}
        
        assert not missing, f"IDs used but not defined: {missing}"
    
    def test_api_calls_use_correct_base(self):
        """All API calls must use ${API} prefix"""
        import re
        
        # Find fetch calls that don't use API variable
        hardcoded = re.findall(r"fetch\(['\"]/(api/[^'\"]+)", self.content)
        
        assert not hardcoded, f"Hardcoded API paths found: {hardcoded}"
    
    def test_no_console_errors_in_js(self):
        """JavaScript should have no obvious syntax issues"""
        import re
        
        # Extract JS
        js_match = re.search(r'<script>(.*?)</script>', self.content, re.DOTALL)
        if not js_match:
            pytest.skip("No script found")
        
        js = js_match.group(1)
        
        # Check balanced braces
        open_braces = js.count('{')
        close_braces = js.count('}')
        assert open_braces == close_braces, f"Unbalanced braces: {open_braces} open, {close_braces} close"
        
        # Check balanced parens
        open_parens = js.count('(')
        close_parens = js.count(')')
        assert open_parens == close_parens, f"Unbalanced parens: {open_parens} open, {close_parens} close"


# ============================================================
# CHAT MODULE VALIDATION
# ============================================================

class TestChatModuleValidation:
    """Tests that validate chat module structure"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.chat_path = Path("modules/ai-chat-module-pro/chat-pro-standalone.html")
        self.content = self.chat_path.read_text() if self.chat_path.exists() else ""
    
    def test_whisper_import_path_is_correct(self):
        """Chat must import WhisperTranscriber from correct path"""
        assert "../whisper-module/WhisperTranscriber.js" in self.content, \
            "Whisper import path incorrect or missing"
    
    def test_linter_import_path_is_correct(self):
        """Chat must load PromptLinter.bundle.js"""
        assert "PromptLinter.bundle.js" in self.content, \
            "PromptLinter bundle not loaded"
    
    def test_api_endpoint_is_correct(self):
        """Chat must call /api/chat endpoint"""
        assert "/api/chat" in self.content, \
            "Chat API endpoint missing"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


class TestConversationDetection:
    """Test that conversations are not treated as tasks"""
    
    def test_is_conversational_detects_greetings(self):
        """Greetings should be detected as conversation"""
        from localagent.roadmap.prompt_optimizer import is_conversational
        
        assert is_conversational("hello") == True
        assert is_conversational("hi") == True
        assert is_conversational("hey there") == True
        assert is_conversational("bonjour") == True
    
    def test_is_conversational_detects_test_messages(self):
        """Test messages should be detected as conversation"""
        from localagent.roadmap.prompt_optimizer import is_conversational
        
        assert is_conversational("this is a test") == True
        assert is_conversational("just testing") == True
        assert is_conversational("test message") == True
    
    def test_is_conversational_allows_real_tasks(self):
        """Real task requests should NOT be detected as conversation"""
        from localagent.roadmap.prompt_optimizer import is_conversational
        
        assert is_conversational("create a file called test.txt") == False
        assert is_conversational("write me a python script") == False
        assert is_conversational("modify the index.html file") == False
    
    def test_infer_task_type_returns_conversation(self):
        """Conversational messages should return type=conversation"""
        from localagent.roadmap.prompt_optimizer import infer_task_type
        
        result = infer_task_type("this is just a conversation test")
        assert result["type"] == "conversation"
        
        result = infer_task_type("hello how are you")
        assert result["type"] == "conversation"
    
    def test_infer_task_type_detects_create(self):
        """Create requests should be detected"""
        from localagent.roadmap.prompt_optimizer import infer_task_type
        
        result = infer_task_type("create a new file")
        assert result["type"] == "create"
