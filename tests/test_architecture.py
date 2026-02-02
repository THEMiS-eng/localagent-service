"""
Tests d'architecture v3.4.0
Vérifie que la nouvelle structure modulaire est correcte et isolée.
"""
import pytest
from pathlib import Path


class TestModuleStructure:
    """Vérifie que la structure des modules est correcte."""
    
    def test_server_is_thin_layer(self):
        """server.py doit être < 300 lignes (thin layer)."""
        server_path = Path(__file__).parent.parent / "localagent/service/server.py"
        lines = len(server_path.read_text().splitlines())
        assert lines < 300, f"server.py has {lines} lines, should be < 300"
    
    def test_all_routers_exist(self):
        """Tous les routers requis doivent exister."""
        routers_dir = Path(__file__).parent.parent / "localagent/service/routers"
        required_routers = [
            "todo.py", "bugfix.py", "github.py", "debug.py",
            "releases.py", "snapshots.py", "modules.py", "config.py",
            "lint.py", "learning.py", "protocol.py"
        ]
        for router in required_routers:
            assert (routers_dir / router).exists(), f"Router {router} missing"
    
    def test_chat_handler_exists(self):
        """chat_handler.py doit exister dans core/."""
        path = Path(__file__).parent.parent / "localagent/core/chat_handler.py"
        assert path.exists(), "chat_handler.py missing"
    
    def test_cache_module_exists(self):
        """cache.py doit exister dans engine/."""
        path = Path(__file__).parent.parent / "localagent/engine/cache.py"
        assert path.exists(), "cache.py missing"


class TestRouterIsolation:
    """Teste que chaque router fonctionne de manière isolée."""
    
    def test_todo_router_standalone(self):
        """Le router todo doit être importable seul."""
        from localagent.service.routers.todo import router
        assert router.prefix == "/api"
        routes = [r.path for r in router.routes]
        assert "/todo" in routes or any("/todo" in r for r in routes)
    
    def test_bugfix_router_standalone(self):
        """Le router bugfix doit être importable seul."""
        from localagent.service.routers.bugfix import router
        assert "/api" in router.prefix  # /api ou /api/bugfix
    
    def test_releases_router_standalone(self):
        """Le router releases doit être importable seul."""
        from localagent.service.routers.releases import router
        assert router.prefix == "/api"
    
    def test_config_router_standalone(self):
        """Le router config doit être importable seul."""
        from localagent.service.routers.config import router
        assert router.prefix == "/api"
    
    def test_modules_router_standalone(self):
        """Le router modules doit être importable seul."""
        from localagent.service.routers.modules import router
        assert router.prefix == "/api"
    
    def test_protocol_router_standalone(self):
        """Le router protocol doit être importable seul."""
        from localagent.service.routers.protocol import router
        assert router.prefix == "/api/protocol"


class TestCacheModule:
    """Tests pour le module cache centralisé."""
    
    def test_cache_import(self):
        """Le module cache doit être importable."""
        from localagent.engine.cache import TTLCache, get_cache, cached_get, invalidate
    
    def test_ttl_cache_basic(self):
        """TTLCache doit stocker et récupérer des valeurs."""
        from localagent.engine.cache import TTLCache
        cache = TTLCache(ttl_seconds=60)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
    
    def test_ttl_cache_miss(self):
        """TTLCache doit retourner None pour clé inexistante."""
        from localagent.engine.cache import TTLCache
        cache = TTLCache(ttl_seconds=60)
        assert cache.get("nonexistent") is None
    
    def test_ttl_cache_invalidate(self):
        """TTLCache.invalidate() doit vider le cache."""
        from localagent.engine.cache import TTLCache
        cache = TTLCache(ttl_seconds=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.invalidate()
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_global_cache_functions(self):
        """Les fonctions globales de cache doivent fonctionner."""
        from localagent.engine.cache import get_cache, invalidate
        # get_cache retourne le singleton
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2
        # invalidate ne doit pas lever d'exception
        invalidate()


class TestChatHandler:
    """Tests pour le module chat_handler."""
    
    def test_chat_handler_import(self):
        """chat_handler doit être importable."""
        from localagent.core.chat_handler import (
            detect_tracking_type,
            build_conversation_context
        )
    
    def test_detect_tracking_type_todo(self):
        """detect_tracking_type doit détecter les todos."""
        from localagent.core.chat_handler import detect_tracking_type
        # Messages avec mots-clés TODO - retourne (type, title)
        result, _ = detect_tracking_type("add a new feature")
        assert result == "TD"
        result, _ = detect_tracking_type("create new module")
        assert result == "TD"
    
    def test_detect_tracking_type_bugfix(self):
        """detect_tracking_type doit détecter les bugfix."""
        from localagent.core.chat_handler import detect_tracking_type
        # Messages avec mots-clés BUG - retourne (type, title)
        result, _ = detect_tracking_type("fix the bug in parser")
        assert result == "BF"
        result, _ = detect_tracking_type("error when clicking")
        assert result == "BF"
    
    def test_detect_tracking_type_none(self):
        """detect_tracking_type doit retourner None si pas de tracking."""
        from localagent.core.chat_handler import detect_tracking_type
        result, _ = detect_tracking_type("bonjour comment vas-tu")
        assert result is None
        result, _ = detect_tracking_type("explique moi python")
        assert result is None
    
    def test_build_conversation_context(self):
        """build_conversation_context doit formater l'historique."""
        from localagent.core.chat_handler import build_conversation_context
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
        context = build_conversation_context(history)
        assert "user:" in context.lower() or "Hello" in context


class TestRouterEndpoints:
    """Tests des endpoints via les routers."""
    
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from localagent.service.server import app
        return TestClient(app)
    
    # Todo router
    def test_get_todos(self, client):
        r = client.get("/api/todo")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data or isinstance(data, list)
    
    def test_get_backlog(self, client):
        r = client.get("/api/backlog")
        assert r.status_code == 200
    
    # Bugfix router
    def test_get_bugfix(self, client):
        r = client.get("/api/bugfix")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data or "bugfixes" in data or isinstance(data, list)
    
    # Releases router
    def test_get_releases(self, client):
        r = client.get("/api/releases")
        assert r.status_code == 200
        assert "releases" in r.json()
    
    # Config router
    def test_get_config_api_key_status(self, client):
        r = client.get("/api/config/api-key/status")
        assert r.status_code == 200
    
    # Modules router
    def test_get_modules(self, client):
        r = client.get("/api/modules")
        assert r.status_code == 200
    
    # Learning router
    def test_get_learning_patterns(self, client):
        r = client.get("/api/learning/patterns")
        assert r.status_code == 200
    
    # Protocol router
    def test_get_protocol_history(self, client):
        r = client.get("/api/protocol/history")
        assert r.status_code == 200
    
    def test_get_protocol_steps(self, client):
        r = client.get("/api/protocol/steps")
        assert r.status_code == 200
    
    # Health (server.py)
    def test_health(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestServerIntegration:
    """Tests que server.py intègre correctement tous les routers."""
    
    def test_all_routers_included(self):
        """Tous les routers doivent être inclus dans l'app."""
        from localagent.service.server import app
        routes = [r.path for r in app.routes]
        
        # Vérifier les préfixes des routers
        assert any("/api/todo" in str(r) for r in routes), "todo router missing"
        assert any("/api/bugfix" in str(r) for r in routes), "bugfix router missing"
        assert any("/api/releases" in str(r) for r in routes), "releases router missing"
        assert any("/api/config" in str(r) for r in routes), "config router missing"
        assert any("/api/protocol" in str(r) for r in routes), "protocol router missing"
    
    def test_static_mounts(self):
        """Les mounts statiques doivent être configurés."""
        from localagent.service.server import app
        routes = [r.path for r in app.routes]
        # /modules et /outputs doivent être montés
        route_paths = str(routes)
        assert "/modules" in route_paths or any("modules" in str(r) for r in app.routes)


class TestPerformanceBaseline:
    """Tests de performance baseline."""
    
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from localagent.service.server import app
        return TestClient(app)
    
    def test_health_response_time(self, client):
        """Health endpoint doit répondre en < 50ms."""
        import time
        times = []
        for _ in range(10):
            start = time.perf_counter()
            client.get("/api/health")
            times.append((time.perf_counter() - start) * 1000)
        avg = sum(times) / len(times)
        assert avg < 50, f"Health avg {avg:.1f}ms > 50ms"
    
    def test_todo_response_time(self, client):
        """Todo endpoint doit répondre en < 100ms."""
        import time
        times = []
        for _ in range(10):
            start = time.perf_counter()
            client.get("/api/todo")
            times.append((time.perf_counter() - start) * 1000)
        avg = sum(times) / len(times)
        assert avg < 100, f"Todo avg {avg:.1f}ms > 100ms"
