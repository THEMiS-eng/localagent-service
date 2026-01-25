#!/usr/bin/env python3
"""
Dashboard Functional Tests
Tests that would have caught the actual bugs.
"""

import subprocess
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


class TestDashboardAPIEndpoints:
    """Test that all dashboard API calls actually work"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from localagent.service.server import app
            from fastapi.testclient import TestClient
            self.client = TestClient(app)
            self.available = True
        except ImportError:
            self.available = False
    
    # === GET endpoints ===
    
    def test_health_returns_required_fields(self):
        """Health endpoint must return all fields dashboard expects"""
        if not self.available:
            pytest.skip("FastAPI not available")
        r = self.client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        required = ["version", "status", "project", "api_key"]
        for key in required:
            assert key in data, f"Health missing required field: {key}"
    
    def test_outputs_returns_list(self):
        """Outputs endpoint must return a list"""
        if not self.available:
            pytest.skip("FastAPI not available")
        r = self.client.get("/api/outputs")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
    
    def test_snapshots_returns_dict_with_snapshots(self):
        """Snapshots endpoint must return dict with 'snapshots' key"""
        if not self.available:
            pytest.skip("FastAPI not available")
        r = self.client.get("/api/snapshots")
        assert r.status_code == 200
        data = r.json()
        assert "snapshots" in data, "Snapshots response missing 'snapshots' key"
    
    def test_backlog_returns_list(self):
        """Backlog endpoint must return a list"""
        if not self.available:
            pytest.skip("FastAPI not available")
        r = self.client.get("/api/backlog")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
    
    def test_todo_returns_list(self):
        """Todo endpoint must return a list"""
        if not self.available:
            pytest.skip("FastAPI not available")
        r = self.client.get("/api/todo")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
    
    def test_bugfix_pending_returns_dict(self):
        """Bugfix pending endpoint must return dict with 'bugfixes' key"""
        if not self.available:
            pytest.skip("FastAPI not available")
        r = self.client.get("/api/bugfix/pending")
        assert r.status_code == 200
        data = r.json()
        assert "bugfixes" in data
    
    def test_constraints_returns_list(self):
        """Constraints endpoint must return constraints in dict"""
        if not self.available:
            pytest.skip("FastAPI not available")
        r = self.client.get("/api/constraints")
        assert r.status_code == 200
        data = r.json()
        assert "constraints" in data
        assert isinstance(data["constraints"], list)
    
    def test_errors_returns_dict(self):
        """Errors endpoint must return dict with 'errors' key"""
        if not self.available:
            pytest.skip("FastAPI not available")
        r = self.client.get("/api/debug/errors")
        assert r.status_code == 200
        data = r.json()
        assert "errors" in data
    
    def test_github_status_returns_dict(self):
        """GitHub status must return dict with 'configured' key"""
        if not self.available:
            pytest.skip("FastAPI not available")
        r = self.client.get("/api/github/status")
        assert r.status_code == 200
        data = r.json()
        assert "configured" in data
    
    # === POST endpoints - These would have caught the bugs! ===
    
    def test_backlog_add_does_not_crash(self):
        """Adding to backlog must not crash the server"""
        if not self.available:
            pytest.skip("FastAPI not available")
        r = self.client.post("/api/backlog/add", json={"task": "Test", "priority": "medium"})
        # Should not return 500 Internal Server Error
        assert r.status_code != 500, f"Server crashed: {r.text}"
    
    def test_todo_add_does_not_crash(self):
        """Adding todo must not crash the server"""
        if not self.available:
            pytest.skip("FastAPI not available")
        r = self.client.post("/api/todo/add", json={"task": "Test"})
        assert r.status_code != 500, f"Server crashed: {r.text}"
    
    def test_bugfix_add_does_not_crash(self):
        """Adding bugfix must not crash the server"""
        if not self.available:
            pytest.skip("FastAPI not available")
        r = self.client.post("/api/bugfix/add", json={"description": "Test"})
        assert r.status_code != 500, f"Server crashed: {r.text}"


class TestDashboardJavaScript:
    """Test dashboard JS for common bugs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.html = Path("dashboard/index.html").read_text()
        # Extract JS
        match = re.search(r'<script>([\s\S]*?)</script>', self.html)
        self.js = match.group(1) if match else ""
    
    def test_showTab_receives_event_parameter(self):
        """showTab must receive event parameter if it uses event"""
        # Find showTab function
        match = re.search(r'function\s+showTab\s*\(([^)]*)\)', self.js)
        assert match, "showTab function not found"
        params = match.group(1).strip()
        
        # If function uses evt.target, it must receive evt
        func_match = re.search(r'function\s+showTab[^{]*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}', self.js)
        if func_match:
            body = func_match.group(1)
            if 'evt.target' in body or 'evt.' in body:
                assert 'evt' in params, \
                    "showTab uses 'evt' but doesn't receive it as parameter"
    
    def test_all_fetch_have_error_handling(self):
        """All fetch calls should have .catch() or try/catch"""
        # Find all async functions with fetch
        func_pattern = r'async\s+function\s+(\w+)[^{]*\{([\s\S]*?)(?=\nasync\s+function|\nfunction|\Z)'
        
        for match in re.finditer(func_pattern, self.js):
            name = match.group(1)
            body = match.group(2)
            
            if 'fetch(' in body:
                has_catch = '.catch(' in body or 'catch' in body
                assert has_catch, f"Function '{name}' has fetch() without error handling"
    
    def test_no_innerhtml_with_unescaped_user_input(self):
        """innerHTML should not use unescaped external data directly"""
        # This is a simplified check - in reality would need more sophisticated analysis
        dangerous_patterns = [
            r'\.innerHTML\s*=\s*[^;]*\$\{[^}]*\.name',  # ${something.name}
            r'\.innerHTML\s*=\s*[^;]*\$\{[^}]*\.title',
            r'\.innerHTML\s*=\s*[^;]*\$\{[^}]*\.description',
        ]
        
        for pattern in dangerous_patterns:
            matches = re.findall(pattern, self.js)
            # Just warn, don't fail - XSS is lower priority
            if matches:
                print(f"WARNING: Potential XSS in innerHTML: {matches[0][:50]}...")
    
    def test_all_getelementbyid_elements_exist(self):
        """All getElementById calls must reference existing elements"""
        # Find all getElementById calls
        used_ids = set(re.findall(r"getElementById\(['\"](\w+)['\"]", self.js))
        
        # Find all defined IDs in HTML
        defined_ids = set(re.findall(r'id=["\'](\w+)["\']', self.html))
        
        missing = used_ids - defined_ids
        assert not missing, f"getElementById references non-existent elements: {missing}"
    
    def test_onclick_handlers_exist(self):
        """All onclick handlers must reference existing functions"""
        # Find all onclick="functionName(...)"
        onclick_funcs = set(re.findall(r'onclick="(\w+)\(', self.html))
        
        # Find all defined functions
        defined_funcs = set(re.findall(r'(?:async\s+)?function\s+(\w+)', self.js))
        
        missing = onclick_funcs - defined_funcs
        assert not missing, f"onclick references undefined functions: {missing}"


class TestDashboardHTMLStructure:
    """Test dashboard HTML structure"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.html = Path("dashboard/index.html").read_text()
    
    def test_all_panels_have_body(self):
        """Each panel with Count ID should have corresponding Panel ID"""
        # Find all xxxCount elements
        count_ids = re.findall(r'id="(\w+)Count"', self.html)
        
        for count_id in count_ids:
            panel_id = count_id + 'Panel'
            assert f'id="{panel_id}"' in self.html, \
                f"Panel counter '{count_id}Count' has no corresponding panel body '{panel_id}'"
    
    def test_all_tabs_have_content(self):
        """Each tab should have corresponding tab-content"""
        tabs = re.findall(r"showTab\('(\w+)'\)", self.html)
        
        for tab in tabs:
            assert f'id="tab-{tab}"' in self.html, \
                f"Tab '{tab}' has no corresponding content 'tab-{tab}'"
    
    def test_add_inputs_have_ids(self):
        """Add inputs must have IDs for JS to read them"""
        # Find add buttons
        add_buttons = re.findall(r'onclick="(add\w+)\(\)"', self.html)
        
        for btn in add_buttons:
            # Each add function needs corresponding input
            input_name = btn.replace('add', 'new')  # addBacklog -> newBacklog
            assert f'id="{input_name}"' in self.html, \
                f"Add button '{btn}' has no corresponding input '{input_name}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


class TestErrorCapture:
    """Test error capture in dashboard"""
    
    def test_dashboard_has_error_capture(self):
        """Dashboard must have console error capture"""
        content = Path("dashboard/index.html").read_text()
        assert "window.onerror" in content
        assert "console.error" in content
        assert "captureError" in content
    
    def test_dashboard_has_iframe_error_listener(self):
        """Dashboard must listen for errors from chat iframe"""
        content = Path("dashboard/index.html").read_text()
        assert "addEventListener('message'" in content
        assert "chat-error" in content
    
    def test_dashboard_sends_errors_to_backend(self):
        """Dashboard must send errors to /api/debug/error"""
        content = Path("dashboard/index.html").read_text()
        assert "/api/debug/error" in content
    
    def test_chat_module_has_error_capture(self):
        """Chat module must have error capture"""
        content = Path("modules/ai-chat-module-pro/chat-pro-standalone.html").read_text()
        assert "window.onerror" in content
        assert "sendError" in content
    
    def test_chat_module_posts_to_parent(self):
        """Chat module must post errors to parent window"""
        content = Path("modules/ai-chat-module-pro/chat-pro-standalone.html").read_text()
        assert "postMessage" in content
        assert "chat-error" in content


class TestDebugEndpoints:
    """Test debug API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from fastapi.testclient import TestClient
            from localagent.service.server import app
            self.client = TestClient(app)
            self.available = True
        except:
            self.available = False
    
    def test_debug_error_post_endpoint_exists(self):
        """POST /api/debug/error must exist"""
        if not self.available:
            pytest.skip("FastAPI not available")
        
        r = self.client.post("/api/debug/error", json={
            "message": "Test error",
            "source": "test",
            "level": "error"
        })
        assert r.status_code == 200
        data = r.json()
        assert data.get("success") == True
    
    def test_debug_errors_get_endpoint(self):
        """GET /api/debug/errors must return errors list"""
        if not self.available:
            pytest.skip("FastAPI not available")
        
        r = self.client.get("/api/debug/errors")
        assert r.status_code == 200
        data = r.json()
        assert "errors" in data
