# LocalAgent Service Worker

[![Tests](https://github.com/THEMiS-eng/localagent-service/actions/workflows/tests.yml/badge.svg)](https://github.com/THEMiS-eng/localagent-service/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

API service for AI-assisted code generation with constraints, learning, and negotiation.

## Installation

```bash
./INSTALL.command
```

Or manually:
```bash
pip3 install -e . --break-system-packages
python3 -m localagent.service.server
```

## API Endpoints

### Core
- `GET /api/health` - Service status
- `POST /api/chat` - Chat with Claude (negotiated)
- `POST /api/claude/complete` - Direct Claude call with full protocol

### Linter
- `POST /api/lint` - Analyze prompt quality
- `POST /api/lint/optimize` - Optimize prompt

### Constraints
- `GET /api/constraints` - Get all constraints (ENV + CTX)
- `POST /api/constraints/validate` - Validate action

### Project Data
- `GET /api/backlog` - Get backlog items
- `GET /api/todo` - Get TODO items
- `GET /api/changelog` - Get changelog
- `GET /api/outputs` - Get generated files
- `GET /outputs/{filename}` - Serve generated file

### Debug
- `POST /api/debug/console-error` - Report console error (queued to backlog)
- `GET /api/debug/errors` - Get pending errors

### GitHub
- `GET /api/github/status` - GitHub configuration
- `POST /api/github/sync` - Sync with GitHub

## Configuration

API key: `~/.localagent-dev/api_key`

## Architecture

```
Service Worker (port 9998)
    ├── /api/* endpoints
    ├── Orchestrator (coordinates all operations)
    ├── Negotiator (validates Claude responses)
    ├── Constraints (ENV + CTX rules)
    ├── Learning (error tracking)
    └── Debugger (console error capture)
```

## Used By
- LocalAgent Dashboard
- THEMIS-QS
- Any app via HTTP API
