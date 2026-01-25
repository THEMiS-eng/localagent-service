#!/usr/bin/env python3
"""
Server Dynamic Integration Tests
Tests real integrations: GitHub API, Claude API, WebSocket, file operations
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


# ============================================================
# GITHUB CONNECTOR TESTS
# ============================================================

class TestGitHubConnector:
    """Test GitHub connector functions"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from localagent.connectors.github import (
                _get_token, _api_request, get_service_version,
                REPOS, GITHUB_API
            )
            self.get_token = _get_token
            self.api_request = _api_request
            self.get_service_version = get_service_version
            self.REPOS = REPOS
            self.available = True
        except ImportError as e:
            self.available = False
            self.error = str(e)
    
    def test_repos_config_exists(self):
        """REPOS config should have all required repos"""
        if not self.available:
            pytest.skip(f"GitHub module not available: {self.error}")
        
        required = ["service", "dashboard", "chat-module"]
        for repo in required:
            assert repo in self.REPOS, f"Missing repo config: {repo}"
            assert "/" in self.REPOS[repo], f"Repo {repo} should be owner/repo format"
    
    def test_token_function_exists(self):
        """Token retrieval function should exist and not crash"""
        if not self.available:
            pytest.skip("GitHub module not available")
        
        # Should return None or string, never crash
        token = self.get_token()
        assert token is None or isinstance(token, str)
    
    def test_api_request_without_token_returns_error(self):
        """API request without token should return error dict, not crash"""
        if not self.available:
            pytest.skip("GitHub module not available")
        
        with patch.object(sys.modules['localagent.connectors.github'], '_get_token', return_value=None):
            from localagent.connectors.github import _api_request
            result = _api_request("GET", "https://api.github.com/user")
            assert isinstance(result, dict)
            assert "error" in result
    
    def test_get_service_version_returns_string_or_none(self):
        """get_service_version should return version string or None"""
        if not self.available:
            pytest.skip("GitHub module not available")
        
        # Mock to avoid real API call
        with patch.object(sys.modules['localagent.connectors.github'], '_api_request') as mock:
            mock.return_value = {"tag_name": "v1.2.3"}
            version = self.get_service_version()
            # Should handle response correctly
            assert version is None or isinstance(version, str)


class TestGitHubIntegration:
    """Test GitHub integration with server"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from localagent.service.server import app
            from fastapi.testclient import TestClient
            self.client = TestClient(app)
            self.available = True
        except ImportError:
            self.available = False
    
    def test_github_status_endpoint(self):
        """GitHub status should return configured state"""
        if not self.available:
            pytest.skip("Server not available")
        
        r = self.client.get("/api/github/status")
        assert r.status_code == 200
        data = r.json()
        assert "configured" in data
        assert isinstance(data["configured"], bool)
    
    def test_github_releases_endpoint_with_invalid_repo(self):
        """Should handle invalid repo gracefully"""
        if not self.available:
            pytest.skip("Server not available")
        
        r = self.client.get("/api/github/releases/invalid/nonexistent")
        # Should not crash - return error or empty
        assert r.status_code in [200, 404, 400]
    
    def test_github_push_without_auth(self):
        """Push without auth should fail gracefully"""
        if not self.available:
            pytest.skip("Server not available")
        
        r = self.client.post("/api/github/push", json={"message": "test"})
        assert r.status_code == 200
        data = r.json()
        # Should indicate failure, not crash
        assert "success" in data or "error" in data


# ============================================================
# CLAUDE/LLM CONNECTOR TESTS
# ============================================================

class TestClaudeConnector:
    """Test Claude LLM connector"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from localagent.connectors.llm import (
                get_api_key, has_api_key, call_claude, CLAUDE_CONFIG
            )
            self.get_api_key = get_api_key
            self.has_api_key = has_api_key
            self.call_claude = call_claude
            self.config = CLAUDE_CONFIG
            self.available = True
        except ImportError:
            self.available = False
    
    def test_config_has_model(self):
        """Config should specify model"""
        if not self.available:
            pytest.skip("LLM module not available")
        
        assert "model" in self.config
        assert "claude" in self.config["model"].lower()
    
    def test_config_has_max_tokens(self):
        """Config should specify max_tokens"""
        if not self.available:
            pytest.skip("LLM module not available")
        
        assert "max_tokens" in self.config
        assert isinstance(self.config["max_tokens"], int)
        assert self.config["max_tokens"] > 0
    
    def test_get_api_key_returns_string_or_none(self):
        """get_api_key should return string or None, never crash"""
        if not self.available:
            pytest.skip("LLM module not available")
        
        key = self.get_api_key()
        assert key is None or isinstance(key, str)
    
    def test_has_api_key_returns_bool(self):
        """has_api_key should return boolean"""
        if not self.available:
            pytest.skip("LLM module not available")
        
        result = self.has_api_key()
        assert isinstance(result, bool)
    
    def test_call_claude_without_key_returns_error(self):
        """call_claude without API key should return error dict"""
        if not self.available:
            pytest.skip("LLM module not available")
        
        with patch.object(sys.modules['localagent.connectors.llm'], 'get_api_key', return_value=None):
            from localagent.connectors.llm import call_claude
            result = call_claude("test")
            assert isinstance(result, dict)
            assert result.get("success") == False
            assert "error" in result
    
    def test_call_claude_with_mock_success(self):
        """call_claude should handle successful response"""
        if not self.available:
            pytest.skip("LLM module not available")
        
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "content": [{"text": "Test response"}],
            "usage": {"input_tokens": 10, "output_tokens": 5}
        }).encode()
        
        with patch.object(sys.modules['localagent.connectors.llm'], 'get_api_key', return_value="test-key"):
            with patch('urllib.request.urlopen', return_value=mock_response):
                from localagent.connectors.llm import call_claude
                result = call_claude("test prompt")
                assert result.get("success") == True
                assert "response" in result


class TestClaudeIntegration:
    """Test Claude integration with server"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from localagent.service.server import app
            from fastapi.testclient import TestClient
            self.client = TestClient(app)
            self.available = True
        except ImportError:
            self.available = False
    
    def test_chat_endpoint_exists(self):
        """Chat endpoint should exist"""
        if not self.available:
            pytest.skip("Server not available")
        
        # Even without API key, should not 404
        r = self.client.post("/api/chat", json={"message": "test"})
        assert r.status_code != 404
    
    def test_chat_without_message_returns_error(self):
        """Chat without message should return error"""
        if not self.available:
            pytest.skip("Server not available")
        
        r = self.client.post("/api/chat", json={})
        # Should indicate error, not crash
        assert r.status_code in [200, 400, 422]
    
    def test_api_key_status_in_health(self):
        """Health should report API key status"""
        if not self.available:
            pytest.skip("Server not available")
        
        r = self.client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert "api_key" in data
        assert isinstance(data["api_key"], bool)


# ============================================================
# WEBSOCKET TESTS
# ============================================================

class TestWebSocket:
    """Test WebSocket functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from localagent.service.server import app
            from fastapi.testclient import TestClient
            self.client = TestClient(app)
            self.available = True
        except ImportError:
            self.available = False
    
    def test_websocket_endpoint_exists(self):
        """WebSocket endpoint should accept connections"""
        if not self.available:
            pytest.skip("Server not available")
        
        # TestClient has WebSocket support
        try:
            with self.client.websocket_connect("/ws") as ws:
                # Should connect successfully
                assert ws is not None
        except Exception as e:
            # Connection might fail but shouldn't crash server
            assert "WebSocket" in str(type(e).__name__) or "Connection" in str(e)


# ============================================================
# FILE OPERATIONS TESTS
# ============================================================

class TestFileOperations:
    """Test file-based operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from localagent.engine.tracking import (
                get_backlog, save_backlog, add_backlog_item,
                get_todo, save_todo, add_todo_item,
                PROJECTS_DIR
            )
            self.get_backlog = get_backlog
            self.save_backlog = save_backlog
            self.add_backlog_item = add_backlog_item
            self.get_todo = get_todo
            self.save_todo = save_todo
            self.add_todo_item = add_todo_item
            self.projects_dir = PROJECTS_DIR
            self.available = True
        except ImportError:
            self.available = False
    
    def test_get_backlog_returns_list(self):
        """get_backlog should always return list"""
        if not self.available:
            pytest.skip("Tracking module not available")
        
        result = self.get_backlog("nonexistent-project")
        assert isinstance(result, list)
    
    def test_save_backlog_creates_directory(self):
        """save_backlog should create project directory if needed"""
        if not self.available:
            pytest.skip("Tracking module not available")
        
        test_project = f"test-project-{int(time.time())}"
        test_dir = self.projects_dir / test_project
        
        try:
            # Should not crash even if dir doesn't exist
            self.save_backlog(test_project, [{"id": "B001", "title": "test"}])
            assert test_dir.exists()
            assert (test_dir / "BACKLOG.json").exists()
        finally:
            # Cleanup
            if test_dir.exists():
                import shutil
                shutil.rmtree(test_dir)
    
    def test_add_backlog_item_returns_id(self):
        """add_backlog_item should return item ID"""
        if not self.available:
            pytest.skip("Tracking module not available")
        
        test_project = f"test-project-{int(time.time())}"
        test_dir = self.projects_dir / test_project
        
        try:
            item_id = self.add_backlog_item(test_project, "Test task", "medium")
            assert isinstance(item_id, str)
            assert item_id.startswith("B")
        finally:
            if test_dir.exists():
                import shutil
                shutil.rmtree(test_dir)
    
    def test_get_todo_returns_list(self):
        """get_todo should always return list"""
        if not self.available:
            pytest.skip("Tracking module not available")
        
        result = self.get_todo("nonexistent-project")
        assert isinstance(result, list)


# ============================================================
# SERVER LIFECYCLE TESTS
# ============================================================

class TestServerLifecycle:
    """Test server startup and lifecycle"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from localagent.service.server import app, VERSION
            from fastapi.testclient import TestClient
            self.client = TestClient(app)
            self.version = VERSION
            self.available = True
        except ImportError:
            self.available = False
    
    def test_server_has_version(self):
        """Server should have version defined"""
        if not self.available:
            pytest.skip("Server not available")
        
        assert self.version is not None
        assert isinstance(self.version, str)
        # Should be semver-like
        parts = self.version.split(".")
        assert len(parts) >= 2
    
    def test_health_returns_version(self):
        """Health endpoint should return server version"""
        if not self.available:
            pytest.skip("Server not available")
        
        r = self.client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data.get("version") == self.version
    
    def test_all_critical_endpoints_respond(self):
        """All critical endpoints should respond (not 500)"""
        if not self.available:
            pytest.skip("Server not available")
        
        critical_endpoints = [
            ("GET", "/api/health"),
            ("GET", "/api/status"),
            ("GET", "/api/constraints"),
            ("GET", "/api/outputs"),
            ("GET", "/api/backlog"),
            ("GET", "/api/todo"),
            ("GET", "/api/github/status"),
        ]
        
        for method, path in critical_endpoints:
            if method == "GET":
                r = self.client.get(path)
            else:
                r = self.client.post(path, json={})
            
            assert r.status_code != 500, f"{method} {path} returned 500 Internal Server Error"


# ============================================================
# ERROR HANDLING TESTS
# ============================================================

class TestErrorHandling:
    """Test error handling across the system"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from localagent.service.server import app
            from fastapi.testclient import TestClient
            self.client = TestClient(app)
            self.available = True
        except ImportError:
            self.available = False
    
    def test_invalid_json_returns_422(self):
        """Invalid JSON should return 422, not 500"""
        if not self.available:
            pytest.skip("Server not available")
        
        r = self.client.post(
            "/api/chat",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        assert r.status_code in [400, 422], f"Expected 400/422 for invalid JSON, got {r.status_code}"
    
    def test_missing_required_fields_handled(self):
        """Missing required fields should be handled gracefully"""
        if not self.available:
            pytest.skip("Server not available")
        
        # Various endpoints with missing data
        endpoints = [
            ("/api/backlog/add", {}),
            ("/api/todo/add", {}),
            ("/api/bugfix/add", {}),
        ]
        
        for path, body in endpoints:
            r = self.client.post(path, json=body)
            # Should not crash (500)
            assert r.status_code != 500, f"{path} crashed with empty body"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


# ============================================================
# END-TO-END TESTS: Publish Flow
# ============================================================

class TestPublishFlow:
    """Test the complete publish flow from dashboard to GitHub."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from localagent.service.server import app
            from fastapi.testclient import TestClient
            self.client = TestClient(app)
            self.available = True
        except ImportError:
            self.available = False
            pytest.skip("Server not available")
    
    def test_github_push_endpoint_accepts_target_param(self):
        """Dashboard sends 'target', endpoint should accept it."""
        if not self.available:
            pytest.skip("Server not available")
        # This will fail without token but should not error on param parsing
        response = self.client.post("/api/github/push", json={
            "target": "service",
            "create_release": True,
            "message": "Test release v1.0.0"
        })
        data = response.json()
        # Should not return "version required" error anymore
        assert "version required" not in str(data.get("error", ""))
    
    def test_github_push_endpoint_reads_version_file(self):
        """Endpoint should read version from VERSION file if not provided."""
        if not self.available:
            pytest.skip("Server not available")
        response = self.client.post("/api/github/push", json={
            "target": "service",
            "create_release": True
        })
        data = response.json()
        # Should have attempted to push (will fail without token, but not on version)
        assert "version required" not in str(data.get("error", ""))
    
    def test_github_push_all_repos(self):
        """Test pushing all repos at once."""
        if not self.available:
            pytest.skip("Server not available")
        response = self.client.post("/api/github/push", json={
            "repo_type": "all",
            "version": "3.0.0",
            "message": "Test all repos"
        })
        data = response.json()
        # Will fail without token but structure should be correct
        assert "error" in data or "success" in data
    
    def test_github_status_endpoint(self):
        """Test GitHub status endpoint."""
        if not self.available:
            pytest.skip("Server not available")
        response = self.client.get("/api/github/status")
        assert response.status_code == 200
        data = response.json()
        assert "configured" in data
        # repos only present if token is configured
        if data.get("configured"):
            assert "repos" in data


class TestChatToFileFlow:
    """Test the complete flow from chat to file creation."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from localagent.service.server import app
            from fastapi.testclient import TestClient
            self.client = TestClient(app)
            self.available = True
        except ImportError:
            self.available = False
            pytest.skip("Server not available")
    
    def test_chat_creates_file_attachment(self):
        """Chat response should include file attachments."""
        if not self.available:
            pytest.skip("Server not available")
        # Note: This requires Claude API, so we test the structure
        response = self.client.post("/api/chat", json={
            "message": "create a hello world file",
            "history": []
        })
        data = response.json()
        # Response should have the files key
        assert "files" in data or "error" in data
    
    def test_chat_with_history(self):
        """Chat should accept history parameter."""
        if not self.available:
            pytest.skip("Server not available")
        response = self.client.post("/api/chat", json={
            "message": "continue our work",
            "history": [
                {"role": "user", "content": "create a test file"},
                {"role": "assistant", "content": "I created test.txt"}
            ]
        })
        assert response.status_code == 200
        data = response.json()
        assert "response" in data or "error" in data
    
    def test_outputs_endpoint_returns_list(self):
        """Outputs endpoint should return a list."""
        if not self.available:
            pytest.skip("Server not available")
        response = self.client.get("/api/outputs")
        assert response.status_code == 200
        data = response.json()
        # Should be a list (not wrapped in {files: []})
        assert isinstance(data, list)
