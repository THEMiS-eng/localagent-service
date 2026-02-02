# THEMIS-QS Architecture Document

## Current State Analysis

### File Inventory

| Category | Files | Lines | Notes |
|----------|-------|-------|-------|
| Python Backend | 45 | 20,940 | localagent/ |
| HTML Frontend | 3 | 16,460 | Monolithic |
| JavaScript | 4 | ~2,500 | Modules |
| **Total** | **71** | **~40,000** | |

### Current Structure
```
localagent_v10.3.0/
├── themis_react_no_jsx.html     # 13,282 lines - MONOLITHIC FRONTEND
├── dashboard/
│   └── index.html               # 1,140 lines - Admin Dashboard
├── modules/
│   ├── ai-chat-module-pro/
│   │   ├── chat-pro-standalone.html  # 2,038 lines
│   │   ├── PromptLinter.js
│   │   ├── PromptLinter.bundle.js
│   │   └── ClaudeContextOptimizer.js
│   └── whisper-module/
│       └── WhisperTranscriber.js
├── localagent/                  # Python Backend
│   ├── core/
│   │   ├── orchestrator.py
│   │   ├── negotiator.py
│   │   ├── protocol.py
│   │   ├── learning.py
│   │   ├── constraints.py
│   │   ├── case_context.py
│   │   ├── chat_handler.py
│   │   ├── debugger.py
│   │   ├── updater.py
│   │   ├── release_publisher.py
│   │   └── release_listener.py
│   ├── service/
│   │   ├── server.py
│   │   ├── daemon.py
│   │   └── routers/
│   │       ├── themis.py        # Main THEMIS routes
│   │       ├── github.py
│   │       ├── releases.py
│   │       ├── skills.py
│   │       ├── protocol.py
│   │       ├── learning.py
│   │       ├── llm.py
│   │       ├── config.py
│   │       ├── todo.py
│   │       ├── bugfix.py
│   │       ├── debug.py
│   │       ├── snapshots.py
│   │       └── modules.py
│   ├── connectors/
│   │   ├── github.py
│   │   ├── mlx_ai.py
│   │   ├── llm_providers.py
│   │   ├── spotlight.py
│   │   ├── dashboard.py
│   │   └── themis_connector.py
│   ├── engine/
│   │   ├── tracking.py
│   │   ├── project.py
│   │   └── cache.py
│   └── skills/
│       ├── __init__.py
│       └── scripts/
├── default_skills/              # ADR Skills
│   ├── delay-expert/
│   ├── quantum-expert/
│   ├── contract-analyst/
│   ├── claims-advocate/
│   ├── arbitration-support/
│   ├── mediation-support/
│   ├── adjudication-support/
│   └── expert-determination/
└── tests/
```

---

## Target Modular Architecture

### Module Definitions

#### 1. THEMIS-FRONTEND (themis-ui)
**Current:** `themis_react_no_jsx.html` (13,282 lines monolithic)
**Target:** Split into components

```
themis-ui/
├── package.json
├── VERSION                      # e.g., 1.0.0
├── CHANGELOG.md
├── src/
│   ├── index.html
│   ├── App.jsx
│   ├── context/
│   │   └── AppContext.jsx       # State management
│   ├── components/
│   │   ├── LeftPane.jsx         # Vault navigation
│   │   ├── CenterPane.jsx       # Analysis/Search
│   │   ├── RightPane.jsx        # QS Toolbox
│   │   ├── Header.jsx
│   │   ├── Footer.jsx
│   │   ├── Modals/
│   │   │   ├── LandingModal.jsx
│   │   │   ├── FileManager.jsx
│   │   │   ├── PublishModal.jsx
│   │   │   └── PreviewModal.jsx
│   │   └── shared/
│   │       ├── Item.jsx
│   │       ├── Icons.jsx
│   │       └── Badge.jsx
│   ├── hooks/
│   │   ├── useWebSocket.js
│   │   ├── useSearch.js
│   │   └── useEvidence.js
│   └── styles/
│       ├── base.css
│       ├── components.css
│       └── themes.css
└── dist/
    └── themis.bundle.js         # Built output
```

**GitHub Repo:** `THEMiS-eng/themis-ui`
**Version:** Start at `1.0.0`

---

#### 2. AI-CHAT-MODULE (chat-module)
**Current:** `modules/ai-chat-module-pro/`
**Status:** Already modular, needs cleanup

```
ai-chat-module-pro/
├── package.json
├── VERSION                      # Currently 1.2.0
├── CHANGELOG.md
├── chat-pro-standalone.html     # 2,038 lines
├── PromptLinter.js
├── PromptLinter.bundle.js
├── ClaudeContextOptimizer.js
└── README.md
```

**GitHub Repo:** `THEMiS-eng/ai-chat-module-pro` (EXISTS)
**Version:** `1.2.0` → `1.3.0`

---

#### 3. PROMPT-LINTER (linter)
**Current:** Inside ai-chat-module-pro
**Target:** Separate module

```
prompt-linter/
├── package.json
├── VERSION                      # 1.0.0
├── CHANGELOG.md
├── src/
│   ├── PromptLinter.js
│   ├── rules/
│   │   ├── skillMatching.js
│   │   ├── triggerWeights.js
│   │   └── rewriteTemplates.js
│   └── index.js
├── dist/
│   └── PromptLinter.bundle.js
└── README.md
```

**GitHub Repo:** `THEMiS-eng/prompt-linter`
**Version:** `1.0.0`

---

#### 4. WHISPER-MODULE (whisper)
**Current:** `modules/whisper-module/`
**Status:** Minimal, needs expansion

```
whisper-module/
├── package.json
├── VERSION                      # 1.0.0
├── CHANGELOG.md
├── WhisperTranscriber.js
├── SKILL.md
└── README.md
```

**GitHub Repo:** `THEMiS-eng/whisper-module`
**Version:** `1.0.0`

---

#### 5. LOCALAGENT-BACKEND (backend)
**Current:** `localagent/`
**Status:** Well-structured, needs version alignment

```
localagent-backend/
├── setup.py
├── VERSION                      # 3.3.6 on GitHub
├── CHANGELOG.md
├── localagent/
│   ├── __init__.py
│   ├── main.py
│   ├── core/                    # Business logic
│   ├── service/                 # FastAPI server
│   ├── connectors/              # External integrations
│   ├── engine/                  # Project management
│   └── skills/                  # Skill engine
└── tests/
```

**GitHub Repo:** `THEMiS-eng/localagent-service` (EXISTS)
**Version:** `3.3.6` → `3.3.7`

---

#### 6. LOCALAGENT-DASHBOARD (dashboard)
**Current:** `dashboard/`
**Status:** Standalone, functional

```
localagent-dashboard/
├── package.json
├── VERSION                      # 3.0.68 on GitHub
├── CHANGELOG.md
├── index.html                   # 1,140 lines
├── manifest.json
└── README.md
```

**GitHub Repo:** `THEMiS-eng/localagent-dashboard` (EXISTS)
**Version:** `3.0.68` → `3.0.69`

---

#### 7. SKILLS-ENGINE (skills)
**Current:** `localagent/skills/` + `default_skills/`
**Target:** Separate package

```
skills-engine/
├── package.json
├── VERSION                      # 1.0.0
├── CHANGELOG.md
├── engine/
│   ├── __init__.py
│   ├── loader.py
│   ├── validator.py
│   └── executor.py
├── default_skills/
│   ├── delay-expert/
│   ├── quantum-expert/
│   ├── contract-analyst/
│   ├── claims-advocate/
│   ├── arbitration-support/
│   ├── mediation-support/
│   ├── adjudication-support/
│   └── expert-determination/
└── README.md
```

**GitHub Repo:** `THEMiS-eng/skills-engine`
**Version:** `1.0.0`

---

## GitHub Repositories Summary

| Module | Repo | Current | Target |
|--------|------|---------|--------|
| Backend | THEMiS-eng/localagent-service | 3.3.6 | 3.3.7 |
| Dashboard | THEMiS-eng/localagent-dashboard | 3.0.68 | 3.0.69 |
| Chat Module | THEMiS-eng/ai-chat-module-pro | 1.2.0 | 1.3.0 |
| THEMIS UI | THEMiS-eng/themis-ui | NEW | 1.0.0 |
| Prompt Linter | THEMiS-eng/prompt-linter | NEW | 1.0.0 |
| Whisper | THEMiS-eng/whisper-module | NEW | 1.0.0 |
| Skills Engine | THEMiS-eng/skills-engine | NEW | 1.0.0 |

---

## Migration Plan

### Phase 1: Document & Validate
- [x] Create ARCHITECTURE.md
- [ ] Validate with user
- [ ] Map dependencies between modules

### Phase 2: Extract Modules
- [ ] Extract prompt-linter from chat-module
- [ ] Create skills-engine package
- [ ] Create themis-ui from monolithic HTML

### Phase 3: Create Repositories
- [ ] Create new GitHub repos
- [ ] Setup CI/CD for each
- [ ] Configure inter-module dependencies

### Phase 4: Version Alignment
- [ ] Align all versions with GitHub
- [ ] Setup automated changelog generation
- [ ] Configure release workflows

---

## Dependencies Graph

```
themis-ui
├── ai-chat-module-pro
│   └── prompt-linter
├── localagent-backend
│   ├── skills-engine
│   └── connectors (github, mlx, llm)
└── localagent-dashboard
```

---

## API Endpoints by Module

### localagent-backend (service)
- `/api/health`
- `/api/version`
- `/api/github/*`
- `/api/releases/*`
- `/api/skills/*`
- `/api/protocol/*`
- `/api/learning/*`
- `/api/llm/*`
- `/api/config/*`
- `/api/todo/*`
- `/api/bugfix/*`
- `/api/snapshots/*`

### themis (frontend routes)
- `/themis` - Main UI
- `/themis/api/chat` - Chat endpoint
- `/themis/api/search` - Search endpoint
- `/themis/api/evidence/*` - Evidence management

### dashboard
- `/dashboard` - Admin UI

---

## Next Steps

1. **User validates this architecture**
2. **Create missing repos on GitHub**
3. **Split themis_react_no_jsx.html** into components
4. **Align versions** with existing GitHub repos
5. **Setup proper CI/CD** for each module
6. **Document API contracts** between modules

---

*Document created: 2026-01-31*
*Status: DRAFT - Pending validation*
