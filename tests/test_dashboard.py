"""
Tests for LocalAgent Dashboard v4.0.5
"""
import pytest
from pathlib import Path
import re


class TestDashboardExists:
    """Test dashboard file exists and is valid HTML"""
    
    def test_dashboard_file_exists(self):
        assert Path("dashboard/index.html").exists()
    
    def test_dashboard_is_html(self):
        content = Path("dashboard/index.html").read_text()
        assert "<!DOCTYPE html>" in content
        assert "<html" in content
        assert "</html>" in content


class TestDashboardLayout:
    """Test dashboard layout structure"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.html = Path("dashboard/index.html").read_text()
    
    def test_has_header(self):
        assert "header" in self.html
        assert "LocalAgent" in self.html
    
    def test_has_chat_panel(self):
        assert "chat-panel" in self.html
        assert "chatMessages" in self.html
        assert "chatInput" in self.html
    
    def test_has_sidebar(self):
        assert "sidebar" in self.html
    
    def test_has_project_card(self):
        assert "project-card" in self.html
        assert "projectName" in self.html
        assert "projectVersion" in self.html
    
    def test_has_apps_card(self):
        assert "apps-card" in self.html
        assert "appsList" in self.html
        assert "appsCount" in self.html
    
    def test_has_todo_panel(self):
        assert "todoPanel" in self.html
        assert "todoList" in self.html
        assert "todoCount" in self.html
    
    def test_has_bugfix_panel(self):
        assert "bugfixPanel" in self.html
        assert "bugfixList" in self.html
        assert "bugfixCount" in self.html
    
    def test_has_releases_panel(self):
        assert "releasesPanel" in self.html
        assert "releasesList" in self.html
        assert "releasesCount" in self.html


class TestDashboardFeatures:
    """Test dashboard features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.html = Path("dashboard/index.html").read_text()
    
    def test_has_lint_feedback(self):
        """Dashboard must have lint feedback area"""
        assert "lintFeedback" in self.html
        assert "lintInput" in self.html
    
    def test_has_mic_button(self):
        """Dashboard must have whisper mic button"""
        assert "micBtn" in self.html
        assert "toggleRecording" in self.html
    
    def test_has_send_button(self):
        """Dashboard must have send button"""
        assert "sendBtn" in self.html
        assert "sendMessage" in self.html
    
    def test_has_status_indicators(self):
        """Dashboard must show connection status"""
        assert "statusDot" in self.html
        assert "statusText" in self.html
        assert "versionBadge" in self.html
    
    def test_has_api_key_status(self):
        """Dashboard must show API key status"""
        assert "apiKeyStatus" in self.html


class TestDashboardJavaScript:
    """Test dashboard JavaScript"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.html = Path("dashboard/index.html").read_text()
        # Extract script content
        match = re.search(r'<script>(.*?)</script>', self.html, re.DOTALL)
        self.js = match.group(1) if match else ""
    
    def test_has_api_constant(self):
        assert "const API" in self.js
        assert "localhost:9998" in self.js
    
    def test_has_check_health(self):
        assert "checkHealth" in self.js
        assert "/api/health" in self.js
    
    def test_has_load_todos(self):
        assert "loadTodos" in self.js
        assert "/api/todo" in self.js
    
    def test_has_load_bugfixes(self):
        assert "loadBugfixes" in self.js
        assert "/api/bugfix" in self.js
    
    def test_has_load_releases(self):
        assert "loadReleases" in self.js
        assert "/api/releases" in self.js
    
    def test_has_load_apps(self):
        assert "loadApps" in self.js
        assert "/api/apps" in self.js
    
    def test_has_send_message(self):
        assert "sendMessage" in self.js
        assert "/api/chat" in self.js
    
    def test_has_lint_input(self):
        assert "lintInput" in self.js
        assert "/api/lint" in self.js
    
    def test_has_add_functions(self):
        assert "addTodo" in self.js
        assert "addBugfix" in self.js
    
    def test_has_toggle_recording(self):
        assert "toggleRecording" in self.js
        assert "mediaRecorder" in self.js


class TestDashboardAPICalls:
    """Test dashboard makes correct API calls"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.html = Path("dashboard/index.html").read_text()
    
    def test_calls_health_endpoint(self):
        assert "/api/health" in self.html
    
    def test_calls_todo_endpoints(self):
        assert "/api/todo" in self.html
        assert "/api/todo/add" in self.html
        assert "/api/todo/complete" in self.html
    
    def test_calls_bugfix_endpoints(self):
        assert "/api/bugfix/pending" in self.html
        assert "/api/bugfix/add" in self.html
    
    def test_calls_releases_endpoint(self):
        assert "/api/releases" in self.html
    
    def test_calls_apps_endpoint(self):
        assert "/api/apps" in self.html
    
    def test_calls_chat_endpoint(self):
        assert "/api/chat" in self.html
    
    def test_calls_lint_endpoint(self):
        assert "/api/lint" in self.html
    
    def test_calls_whisper_endpoint(self):
        assert "/api/whisper/transcribe" in self.html
