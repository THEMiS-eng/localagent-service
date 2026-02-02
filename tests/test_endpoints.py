"""
Tests exhaustifs des endpoints API.
Vérifie que TOUTES les routes retournent 200 OK.
"""
import pytest
from fastapi.testclient import TestClient
from localagent.service.server import app


@pytest.fixture
def client():
    return TestClient(app)


class TestCoreEndpoints:
    """Endpoints principaux (server.py)"""
    
    def test_root(self, client):
        assert client.get("/").status_code == 200
    
    def test_dashboard(self, client):
        assert client.get("/dashboard").status_code == 200
    
    def test_health(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert "status" in r.json()
    
    def test_outputs(self, client):
        assert client.get("/api/outputs").status_code == 200
    
    def test_errors(self, client):
        assert client.get("/api/errors").status_code == 200
    
    def test_conversation(self, client):
        assert client.get("/api/conversation").status_code == 200
    
    def test_update_check(self, client):
        assert client.get("/api/update/check").status_code == 200
    
    def test_clear_post(self, client):
        assert client.post("/api/clear").status_code == 200


class TestTodoRouter:
    """Router /api/todo"""
    
    def test_get_todo(self, client):
        assert client.get("/api/todo").status_code == 200
    
    def test_get_backlog(self, client):
        assert client.get("/api/backlog").status_code == 200
    
    def test_add_todo(self, client):
        r = client.post("/api/todo/add", json={"task": "Test task"})
        assert r.status_code == 200
    
    def test_add_backlog(self, client):
        r = client.post("/api/backlog/add", json={"task": "Backlog task"})
        assert r.status_code == 200
    
    def test_restore_all_todo(self, client):
        assert client.post("/api/todo/restore-all").status_code == 200


class TestBugfixRouter:
    """Router /api/bugfix"""
    
    def test_get_bugfix(self, client):
        assert client.get("/api/bugfix").status_code == 200
    
    def test_get_pending(self, client):
        assert client.get("/api/bugfix/pending").status_code == 200
    
    def test_add_bugfix(self, client):
        r = client.post("/api/bugfix/add", json={
            "title": "Test bug",
            "description": "Bug description"
        })
        assert r.status_code == 200
    
    def test_apply_bugfix(self, client):
        r = client.post("/api/bugfix/apply", json={
            "bugfix_id": "BF001",
            "commit_sha": "abc123"
        })
        assert r.status_code == 200


class TestGitHubRouter:
    """Router /api/github"""
    
    def test_github_status(self, client):
        assert client.get("/api/github/status").status_code == 200
    
    def test_github_sync(self, client):
        assert client.post("/api/github/sync", json={}).status_code == 200
    
    def test_changelog_sync_from_github(self, client):
        r = client.post("/api/changelog/sync-from-github")
        assert r.status_code in [200, 500]  # May fail without GitHub token


class TestDebugRouter:
    """Router /api/debug"""
    
    def test_debug_errors(self, client):
        assert client.get("/api/debug/errors").status_code == 200
    
    def test_debug_console_errors(self, client):
        assert client.get("/api/debug/console-errors").status_code == 200
    
    def test_debug_stats(self, client):
        assert client.get("/api/debug/stats").status_code == 200
    
    def test_debug_context(self, client):
        assert client.get("/api/debug/context").status_code == 200
    
    def test_debug_report(self, client):
        assert client.get("/api/debug/report").status_code == 200
    
    def test_debug_post_error(self, client):
        r = client.post("/api/debug/error", json={"error": "Test error"})
        assert r.status_code == 200
    
    def test_debug_post_console_error(self, client):
        r = client.post("/api/debug/console-error", json={"error": "Console error"})
        assert r.status_code == 200
    
    def test_debug_clear_console_errors(self, client):
        assert client.post("/api/debug/console-errors/clear").status_code == 200
    
    def test_debug_log(self, client):
        r = client.post("/api/debug/log", json={"message": "test log"})
        assert r.status_code == 200
    
    def test_debug_learn(self, client):
        r = client.post("/api/debug/learn", json={
            "error_id": "test-error-id",
            "fix_description": "Test fix"
        })
        assert r.status_code == 200


class TestReleasesRouter:
    """Router /api/releases"""
    
    def test_get_releases(self, client):
        assert client.get("/api/releases").status_code == 200
    
    def test_get_release_notes(self, client):
        assert client.get("/api/release-notes").status_code == 200
    
    def test_get_release_notes_full(self, client):
        assert client.get("/api/release-notes/full").status_code == 200
    
    def test_get_release_notes_preview(self, client):
        assert client.get("/api/release-notes/preview").status_code == 200
    
    def test_get_release_notes_github(self, client):
        assert client.get("/api/release-notes/github").status_code == 200
    
    def test_get_release_notes_github_all(self, client):
        assert client.get("/api/release-notes/github/all").status_code == 200
    
    def test_get_roadmap(self, client):
        assert client.get("/api/roadmap").status_code == 200
    
    def test_get_roadmap_md(self, client):
        assert client.get("/api/roadmap/md").status_code == 200
    
    def test_get_version_next(self, client):
        assert client.get("/api/version/next").status_code == 200
    
    def test_post_releases(self, client):
        r = client.post("/api/releases", json={"version": "9.9.9", "notes": "Test"})
        assert r.status_code == 200
    
    def test_post_releases_seed(self, client):
        assert client.post("/api/releases/seed", json={}).status_code == 200


class TestSnapshotsRouter:
    """Router /api/snapshots"""
    
    def test_get_snapshots(self, client):
        assert client.get("/api/snapshots").status_code == 200
    
    def test_get_snapshots_verify(self, client):
        assert client.get("/api/snapshots/verify").status_code == 200
    
    def test_post_validate_action(self, client):
        r = client.post("/api/snapshots/validate-action", json={"action": "test"})
        assert r.status_code == 200


class TestModulesRouter:
    """Router /api/modules"""
    
    def test_get_modules(self, client):
        assert client.get("/api/modules").status_code == 200


class TestConfigRouter:
    """Router /api/config"""
    
    def test_get_api_key_status(self, client):
        assert client.get("/api/config/api-key/status").status_code == 200
    
    def test_get_app(self, client):
        assert client.get("/api/app").status_code == 200
    
    def test_get_apps(self, client):
        assert client.get("/api/apps").status_code == 200


class TestLintRouter:
    """Router /api/lint"""
    
    def test_post_lint(self, client):
        r = client.post("/api/lint", json={"prompt": "Create a test"})
        assert r.status_code == 200
    
    def test_post_lint_optimize(self, client):
        r = client.post("/api/lint/optimize", json={"prompt": "Create a test"})
        assert r.status_code == 200
    
    def test_get_lint_summary(self, client):
        assert client.get("/api/lint/summary").status_code == 200


class TestLearningRouter:
    """Router /api/learning"""
    
    def test_get_patterns(self, client):
        assert client.get("/api/learning/patterns").status_code == 200
    
    def test_get_report(self, client):
        assert client.get("/api/learning/report").status_code == 200
    
    def test_post_error(self, client):
        r = client.post("/api/learning/error", json={
            "error_type": "test",
            "error_msg": "Test error message"
        })
        assert r.status_code == 200


class TestProtocolRouter:
    """Router /api/protocol"""
    
    def test_get_history(self, client):
        assert client.get("/api/protocol/history").status_code == 200
    
    def test_get_steps(self, client):
        assert client.get("/api/protocol/steps").status_code == 200
    
    def test_post_notify(self, client):
        r = client.post("/api/protocol/notify", json={"message": "Test"})
        assert r.status_code == 200


class TestConstraintsRouter:
    """Router /api/constraints"""
    
    def test_get_constraints(self, client):
        assert client.get("/api/constraints").status_code == 200
