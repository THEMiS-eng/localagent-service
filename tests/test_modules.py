"""
Tests pour les modules non couverts:
- core/orchestrator.py
- core/release_listener.py
- core/release_publisher.py
- core/updater.py
- service/daemon.py
- connectors/llm.py
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestOrchestrator:
    """Tests pour localagent/core/orchestrator.py"""
    
    def test_import(self):
        """Le module doit être importable."""
        from localagent.core.orchestrator import (
            OrchestratorState,
            get_state,
            git_sync_to_remote,
            create_file,
            commit,
        )
    
    def test_orchestrator_state_class(self):
        """OrchestratorState doit avoir les attributs requis."""
        from localagent.core.orchestrator import OrchestratorState
        state = OrchestratorState(project="TEST")
        assert hasattr(state, 'project') or hasattr(state, 'status')
    
    def test_get_state(self):
        """get_state doit retourner un état."""
        from localagent.core.orchestrator import get_state
        state = get_state("TEST")
        assert state is not None
    
    def test_create_file(self):
        """create_file doit retourner un dict."""
        from localagent.core.orchestrator import create_file
        result = create_file("TEST", "test.txt", "content")
        assert isinstance(result, dict)
    
    def test_commit(self):
        """commit doit retourner un dict."""
        from localagent.core.orchestrator import commit
        result = commit("TEST", "test commit")
        assert isinstance(result, dict)


class TestReleaseListener:
    """Tests pour localagent/core/release_listener.py"""
    
    def test_import(self):
        """Le module doit être importable."""
        from localagent.core.release_listener import (
            fetch_latest_release,
            get_cached_release,
            check_for_update,
        )
    
    def test_get_cached_release(self):
        """get_cached_release doit retourner None ou un dict."""
        from localagent.core.release_listener import get_cached_release
        result = get_cached_release()
        assert result is None or isinstance(result, dict)
    
    def test_check_for_update(self):
        """check_for_update doit retourner un dict."""
        from localagent.core.release_listener import check_for_update
        result = check_for_update()
        assert isinstance(result, dict)
        assert "update_available" in result or "error" in result or "current" in result


class TestReleasePublisher:
    """Tests pour localagent/core/release_publisher.py"""
    
    def test_import(self):
        """Le module doit être importable."""
        from localagent.core.release_publisher import (
            get_github_token,
            has_github_token,
            verify_token,
            get_repo_config,
        )
    
    def test_get_github_token(self):
        """get_github_token doit retourner str ou None."""
        from localagent.core.release_publisher import get_github_token
        result = get_github_token()
        assert result is None or isinstance(result, str)
    
    def test_has_github_token(self):
        """has_github_token doit retourner bool."""
        from localagent.core.release_publisher import has_github_token
        result = has_github_token()
        assert isinstance(result, bool)
    
    def test_get_repo_config(self):
        """get_repo_config doit retourner un dict."""
        from localagent.core.release_publisher import get_repo_config
        result = get_repo_config()
        assert isinstance(result, dict)
    
    def test_verify_token_without_token(self):
        """verify_token sans token doit retourner erreur."""
        from localagent.core.release_publisher import verify_token
        result = verify_token()
        assert isinstance(result, dict)


class TestUpdater:
    """Tests pour localagent/core/updater.py"""
    
    def test_import(self):
        """Le module doit être importable."""
        from localagent.core.updater import (
            get_manifest,
            get_current_version,
            get_update_status,
            list_backups,
        )
    
    def test_get_manifest(self):
        """get_manifest doit retourner un dict."""
        from localagent.core.updater import get_manifest
        result = get_manifest()
        assert isinstance(result, dict)
    
    def test_get_current_version(self):
        """get_current_version doit retourner une string."""
        from localagent.core.updater import get_current_version
        result = get_current_version()
        assert isinstance(result, str)
    
    def test_get_update_status(self):
        """get_update_status doit retourner un dict."""
        from localagent.core.updater import get_update_status
        result = get_update_status()
        assert isinstance(result, dict)
    
    def test_list_backups(self):
        """list_backups doit retourner une liste."""
        from localagent.core.updater import list_backups
        result = list_backups()
        assert isinstance(result, list)


class TestDaemon:
    """Tests pour localagent/service/daemon.py"""
    
    def test_import(self):
        """Le module doit être importable."""
        from localagent.service.daemon import (
            get_pid,
            is_running,
            status,
        )
    
    def test_get_pid(self):
        """get_pid doit retourner int ou None."""
        from localagent.service.daemon import get_pid
        result = get_pid()
        assert result is None or isinstance(result, int)
    
    def test_is_running(self):
        """is_running doit retourner bool."""
        from localagent.service.daemon import is_running
        result = is_running()
        assert isinstance(result, bool)
    
    def test_status(self):
        """status doit retourner un dict."""
        from localagent.service.daemon import status
        result = status()
        assert isinstance(result, dict)
        assert "running" in result or "status" in result or "pid" in result


class TestLLMConnector:
    """Tests pour localagent/connectors/llm.py"""
    
    def test_import(self):
        """Le module doit être importable."""
        from localagent.connectors.llm import (
            get_api_key,
            set_api_key,
            has_api_key,
        )
    
    def test_get_api_key(self):
        """get_api_key doit retourner str ou None."""
        from localagent.connectors.llm import get_api_key
        result = get_api_key()
        assert result is None or isinstance(result, str)
    
    def test_has_api_key(self):
        """has_api_key doit retourner bool."""
        from localagent.connectors.llm import has_api_key
        result = has_api_key()
        assert isinstance(result, bool)
    
    def test_set_api_key(self):
        """set_api_key doit accepter une clé."""
        from localagent.connectors.llm import set_api_key, get_api_key
        # Sauvegarder l'ancienne clé
        old_key = get_api_key()
        # Tester set
        set_api_key("test-key-12345")
        assert get_api_key() == "test-key-12345"
        # Restaurer
        if old_key:
            set_api_key(old_key)
