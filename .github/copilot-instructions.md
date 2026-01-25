# Copilot Instructions for LocalAgent

## Project Context
LocalAgent is a Python service worker that orchestrates AI-powered development workflows.
- Framework: FastAPI (async)
- Architecture: Service + Routers + Engine + Connectors
- Tests: pytest (448+ tests required to pass)

## Code Style
- Python 3.10+ with type hints
- Async/await for I/O operations
- No print() - use logger
- Max function length: 50 lines
- Docstrings for public functions

## File Structure
```
localagent/
├── service/          # HTTP API (FastAPI)
│   ├── server.py     # Main app
│   └── routers/      # Modular endpoints
├── engine/           # Core logic
│   ├── project.py    # Project management
│   └── tracking.py   # TODO/Backlog/Bugfix
├── connectors/       # External services
│   ├── github.py     # GitHub API
│   └── llm.py        # Claude API
└── core/             # Business logic
    ├── constraints.py
    └── protocol.py
```

## Key Patterns
1. **Cache**: Use TTLCache for frequent reads
2. **Routers**: New endpoints go in routers/, not server.py
3. **Tracking**: All state in JSON files under ~/.localagent/projects/

## Testing
- Run: `python -m pytest tests/ -q`
- All 448 tests must pass before commit
- New features need tests in tests/test_*.py

## Don't
- Don't add console.log in dashboard JS
- Don't hardcode versions (use VERSION file)
- Don't skip cache invalidation after mutations
