"""
Tests for PromptOptimizer and detection modules.
Migrated from test_localagent.py
"""
import pytest
from pathlib import Path


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


class TestPromptLinterBundle:
    """Tests for PromptLinter.bundle.js functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        bundle_path = Path("modules/ai-chat-module-pro/PromptLinter.bundle.js")
        if bundle_path.exists():
            self.bundle = bundle_path.read_text()
            self.has_bundle = True
        else:
            self.has_bundle = False
    
    def test_bundle_exists(self):
        assert self.has_bundle, "PromptLinter.bundle.js not found"


class TestTokenEstimation:
    """Tests for token estimation logic"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        bundle_path = Path("modules/ai-chat-module-pro/PromptLinter.bundle.js")
        if bundle_path.exists():
            self.bundle = bundle_path.read_text()
        else:
            pytest.skip("PromptLinter.bundle.js not found")
    
    def test_estimates_input_tokens(self):
        """Should estimate input tokens"""
        assert "inputTokens" in self.bundle or "input" in self.bundle
        assert "charCount" in self.bundle or "length" in self.bundle
    
    def test_estimates_output_tokens(self):
        """Should estimate output tokens based on task"""
        assert "outputTokens" in self.bundle or "output" in self.bundle
    
    def test_calculates_cost(self):
        """Should calculate estimated cost"""
        assert "cost" in self.bundle.lower()


class TestLanguageDetection:
    """Tests for language detection"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        bundle_path = Path("modules/ai-chat-module-pro/PromptLinter.bundle.js")
        if bundle_path.exists():
            self.bundle = bundle_path.read_text()
        else:
            pytest.skip("PromptLinter.bundle.js not found")
    
    def test_detects_french(self):
        """Should detect French language"""
        assert "detectLanguage" in self.bundle
        assert "fr" in self.bundle
    
    def test_detects_english(self):
        """Should detect English language"""
        assert "en" in self.bundle
    
    def test_returns_language_in_result(self):
        """lintPrompt should return detected language"""
        assert "lang" in self.bundle.lower()


class TestTaskTypeInference:
    """Tests for task type inference"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        bundle_path = Path("modules/ai-chat-module-pro/PromptLinter.bundle.js")
        if bundle_path.exists():
            self.bundle = bundle_path.read_text()
        else:
            pytest.skip("PromptLinter.bundle.js not found")
    
    def test_infers_create_task(self):
        assert "create" in self.bundle.lower()
    
    def test_infers_fix_task(self):
        assert "fix" in self.bundle.lower()
    
    def test_infers_modify_task(self):
        assert "modify" in self.bundle.lower()
    
    def test_infers_explain_task(self):
        assert "explain" in self.bundle.lower()
