# THEMIS 10.1.9 - API Reference

## Overview

- **Total Routes**: 84 endpoints
- **Themis Backend**: localhost:8765
- **Service Worker** (LocalAgent): localhost:9998

---

## THEMIS BACKEND (localhost:8765)

### HEALTH
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/health | Health check |

### SERVICE
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/service/status | Service status |
| POST | /api/service/control | Start/stop/restart |
| GET | /api/service/logs?lines= | Get logs |

### CASES
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/cases | List all cases |
| POST | /api/cases | Create case |
| GET | /api/cases/{id} | Get case |
| PUT | /api/cases/{id} | Update case |
| DELETE | /api/cases/{id} | Archive case |
| POST | /api/cases/{id}/open | Open case |
| POST | /api/cases/{id}/close | Close case |
| POST | /api/cases/search?q= | Search cases |

### EVIDENCE
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/evidence?case_id= | List evidence |
| GET | /api/evidence/{id} | Get evidence |
| POST | /api/evidence/upload | Upload evidence |
| POST | /api/evidence/{id}/validate | Validate evidence |
| DELETE | /api/evidence/{id} | Remove evidence |
| GET | /api/evidence/{id}/content | Download content |
| GET | /api/evidence/{id}/provenance | Get provenance |

### TAGS (macOS Native)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/tags/{evidenceId} | Get tags |
| POST | /api/tags/{evidenceId}?namespace=&value= | Add tag |
| DELETE | /api/tags/{evidenceId}/{namespace}/{value} | Remove tag |

### FRAMEWORKS
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/frameworks | List frameworks |
| GET | /api/frameworks/{id} | Get framework |
| GET | /api/frameworks/{id}/folders | Get folders |

### FRAMEWORK (Extended)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/framework/supported | Supported frameworks |
| GET | /api/framework/document-types?framework= | Document types |
| GET | /api/framework/delay-methods?methodology= | Delay methods |
| GET | /api/framework/delay-methods/cross-reference | Cross reference |
| POST | /api/framework/detect | Detect framework |
| POST | /api/framework/validate-method | Validate method |

### FOLDERS (SmartFolders)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/folders?case_id= | Get folder tree |
| GET | /api/folders/{path} | Get folder contents |
| POST | /api/folders/{path}/add | Add to folder |
| POST | /api/folders/{path}/remove | Remove from folder |
| GET | /api/folders/search?q=&case_id= | Search folders |

### SEARCH (Spotlight)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/search/evidence?q=&case_id= | Search evidence |
| GET | /api/search/tag?namespace=&value=&case_id= | Search by tag |
| GET | /api/search/type?type=&case_id= | Search by type |
| GET | /api/search/validation?status=&case_id= | Search by validation |
| POST | /api/search/track | Track search |
| GET | /api/search/history/{hash} | Get history |
| DELETE | /api/search/history/{hash} | Clear history |

### CONTEXT
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/context/conversation | Create context |
| GET | /api/context/conversation/{id} | Get context |
| POST | /api/context/conversation/{id}/add | Add to context |

### ANALYSIS
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/analysis/extract | Extract facts |
| GET | /api/analysis/facts?case_id= | Get facts |
| GET | /api/analysis/chronology?case_id= | Get chronology |
| POST | /api/analysis/delay | Analyze delay |
| POST | /api/analysis/methods | Get methods |
| POST | /api/analysis/concurrency?case_id= | Analyze concurrency |

### OUTPUTS
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/outputs/generate | Generate output |
| POST | /api/outputs?case_id= | Create output |
| GET | /api/outputs/{id} | Get output |
| GET | /api/outputs/{id}/download | Download output |
| GET | /api/outputs/{id}/provenance | Get provenance |

### SETTINGS
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/settings | Get settings |
| PUT | /api/settings | Update settings |
| GET | /api/settings/modules | Get modules |
| PUT | /api/settings/modules/{name} | Toggle module |

### CASELAW
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/caselaw/search?q= | Search caselaw |
| GET | /api/caselaw/{ref} | Get citation |
| GET | /api/caselaw/precedents?case_id= | Get precedents |

### MLX (AI Classification)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/mlx-feeder/stats | Get stats |
| GET | /api/mlx-feeder/consent | Get consent |
| POST | /api/mlx-feeder/consent | Grant consent |

### CHAT
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/chat | Send message |
| GET | /api/chat/history?case_id= | Get history |

### IMPORT (Zero Trust)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/import/files?case_id=&vault_id= | Import files |
| GET | /api/import/{id} | Get status |
| GET | /api/import/{id}/progress | Get progress |
| DELETE | /api/import/{id} | Cancel import |
| GET | /api/import/config?case_id= | Get config |
| PUT | /api/import/config?case_id= | Update config |

### QUARANTINE
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/quarantine | List quarantine |
| GET | /api/quarantine/{id} | Get item |
| DELETE | /api/quarantine/{id} | Delete item |
| POST | /api/quarantine/{id}/retry | Retry item |

### SCL (Society of Construction Law)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/scl/principles | Get principles |
| GET | /api/scl/principles/{number} | Get principle |
| GET | /api/scl/compliance? | Check compliance |
| GET | /api/scl/record-categories | Get categories |
| GET | /api/scl/record-categories/suggest?document_type= | Suggest category |

### EVENTS (Risk)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/events?case_id= | Create event |
| GET | /api/events?case_id= | List events |
| GET | /api/events/classify?description=&source= | Classify event |
| GET | /api/events/concurrent?case_id= | Get concurrent |

### NOTICES
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/notices?case_id= | Create notice |
| GET | /api/notices?case_id=&status=&notice_type= | List notices |
| GET | /api/notices/overdue?case_id= | Get overdue |
| GET | /api/notices/upcoming?case_id= | Get upcoming |

### RO-ASSESSMENT
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/ro-assessment?case_id= | Create assessment |
| GET | /api/ro-assessment/{id} | Get assessment |

---

## SERVICE WORKER → LOCALAGENT (localhost:9998)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/health | Health check |
| GET | /api/github/releases/{owner}/{repo} | Get releases |
| GET | /api/update/check?app_id=&current_version= | Check update |
| POST | /api/update/install | Install update |

---

## WEBSOCKET

| Endpoint | Description |
|----------|-------------|
| ws://localhost:8765/ws?case_id= | Themis WebSocket |

### WebSocket Events
- folder.update
- chat.chunk
- chat.complete
- evidence.added
- evidence.validated

