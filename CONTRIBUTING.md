# Contributing to LocalAgent

## Setup Development Environment

```bash
# Clone
git clone https://github.com/THEMiS-eng/localagent-service.git
cd localagent-service

# Install
pip install -e .
pip install pytest pytest-asyncio httpx black isort flake8

# Pre-commit hooks (optional but recommended)
pip install pre-commit
pre-commit install
```

## Code Style

### Python
- **Formatter**: Black (line-length=100)
- **Import sorting**: isort (profile=black)
- **Linting**: flake8
- **Type hints**: Required for public functions

### Example
```python
from typing import Dict, List, Optional

async def get_items(project: str, limit: int = 10) -> List[Dict]:
    """
    Get items from project.
    
    Args:
        project: Project name
        limit: Maximum items to return
        
    Returns:
        List of item dictionaries
    """
    # Implementation
    pass
```

## Architecture

```
localagent/
├── service/server.py    # FastAPI app (don't add endpoints here)
├── service/routers/     # Add new endpoints here
├── engine/              # Core logic (project, tracking)
├── connectors/          # External APIs (github, llm)
└── core/                # Business logic
```

### Adding a New Endpoint

1. Create or edit a router in `service/routers/`
2. Import and include in `server.py`
3. Add tests in `tests/`

```python
# service/routers/myfeature.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/myfeature", tags=["myfeature"])

@router.get("")
async def get_myfeature():
    return {"status": "ok"}
```

## Testing

```bash
# Run all tests
pytest tests/ -q

# Run specific test
pytest tests/test_server_integration.py -v

# Run with coverage
pytest tests/ --cov=localagent
```

### Test Requirements
- All 448+ tests must pass
- New features need tests
- No `console.log` in JS, no `print()` in Python

## Git Workflow

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes, run tests
pytest tests/ -q

# Commit with descriptive message
git commit -m "Add: my feature description"

# Push and create PR
git push origin feature/my-feature
```

### Commit Message Format
- `Add:` New feature
- `Fix:` Bug fix
- `Refactor:` Code improvement
- `Docs:` Documentation
- `Test:` Tests only

## Release Process

1. Update VERSION file
2. Run tests: `pytest tests/ -q`
3. Push to GitHub
4. GitHub Actions runs tests
5. If tests pass, TODOs are auto-completed
