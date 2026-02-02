# LocalAgent v4.1.3 - Orchestrator with Full Themis Proxy

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│            LocalAgent Backend (port 9998)                       │
│                     ORCHESTRATOR                                │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  /dashboard          → Dashboard LocalAgent UI                  │
│  /themis             → Themis UI                                │
│  /themis/api/*       → Proxy 84 routes vers Themis BE (8765)   │
│  /api/*              → LocalAgent Core API                      │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
                              │
                              │ Proxy HTTP
                              ▼
┌────────────────────────────────────────────────────────────────┐
│            Themis Backend (port 8765)                           │
│                                                                 │
│  84 endpoints:                                                  │
│  • cases, evidence, tags, folders, search                      │
│  • analysis, outputs, settings, caselaw                        │
│  • mlx-feeder, chat, import, quarantine                        │
│  • scl, events, notices, ro-assessment, framework              │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

## Installation

```bash
cd ~/Downloads
unzip localagent_v4.1.3.zip
cd localagent_v4.1.3
pip install -e . --user
localagent stop
localagent start
```

## URLs

| URL | Description |
|-----|-------------|
| http://localhost:9998/dashboard | Dashboard LocalAgent |
| http://localhost:9998/themis | UI Themis |
| http://localhost:9998/themis/status | Status Themis Backend |
| http://localhost:9998/api/health | Health LocalAgent |

## Themis API Proxy

Toutes les routes Themis sont proxiées via `/themis/api/*`:

```
GET  /themis/api/cases          → localhost:8765/api/cases
POST /themis/api/chat           → localhost:8765/api/chat
GET  /themis/api/mlx-feeder/stats → localhost:8765/api/mlx-feeder/stats
...
```

Voir `THEMIS_10.1.9_API_REFERENCE.md` pour l'inventaire complet des 84 endpoints.

## Tests

```bash
python -m pytest tests/ -q
# 404 passed
```
