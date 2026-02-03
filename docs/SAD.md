# Software Architecture Document (SAD)
## LocalAgent Service v3.3.x

---
**Version:** 0.1.0
**Date:** 2026-02-03
**Auteur:** Claude Code
**Derniere modification:** 2026-02-03 10:45
**Changelog:**
- 0.1.0 (2026-02-03): Creation initiale + Section 0 Chemins Critiques
---

**Base sur:** Analyse du code source existant

---

## 0. CHEMINS CRITIQUES (SOURCE DE VERITE)

| Chemin | Type | Role | Git |
|--------|------|------|-----|
| `~/localagent_v3` | REPO DEV | Code source, seul endroit pour modifier le code | THEMiS-eng/localagent-service |
| `~/Downloads/localagent-service X` | BUILD/COPIE | Exports, NE PAS MODIFIER | Non |
| `~/.localagent/` | RUNTIME | Donnees utilisateur, config, modules installes | Non |
| `~/.localagent-dev/` | DEV CONFIG | Tokens, config dev | Non |

### REGLE ABSOLUE

```
+------------------------------------------------------------------+
|                                                                  |
|   Toute modification de code DOIT etre faite dans               |
|   ~/localagent_v3 et poussee via git.                           |
|                                                                  |
|   Les autres chemins sont des COPIES ou du RUNTIME.             |
|   Ne JAMAIS modifier directement ~/Downloads/* ou ~/.localagent |
|                                                                  |
+------------------------------------------------------------------+
```

### Sous-chemins importants

| Chemin | Contenu |
|--------|---------|
| `~/localagent_v3/localagent/` | Code Python du service |
| `~/localagent_v3/dashboard/` | Dashboard DEV (non distribue) |
| `~/localagent_v3/scripts/` | Scripts DEV (non distribues) |
| `~/localagent_v3/docs/` | Documentation |
| `~/.localagent/modules/` | Modules installes (runtime) |
| `~/.localagent/BUILD` | Version build installee |
| `~/.localagent-dev/github_token` | Token GitHub (DEV only) |

---

## 1. ARCHITECTURE PRODUIT

### 1.1 Vue d'Ensemble

```
+---------------------------------------------------------------------+
|                    ENVIRONNEMENT PUBLIC                              |
|                      (100% OFFLINE)                                  |
|                                                                      |
|  +-------------------------------------------------------------+    |
|  |                    THEMIS-QS                                 |    |
|  |              (Application Publique)                          |    |
|  +-------------------------------------------------------------+    |
|                          |                                           |
|                          v                                           |
|  +-------------------------------------------------------------+    |
|  |               LocalAgent Service                             |    |
|  |                  (Backend)                                   |    |
|  +-------------------------------------------------------------+    |
|                          |                                           |
|         +----------------+----------------+                          |
|         v                v                v                          |
|  +-----------+    +-----------+    +-----------+                    |
|  | themis-ui |    |  prompt-  |    |  whisper- |                    |
|  |  (local)  |    |  linter   |    |  module   |                    |
|  +-----------+    +-----------+    +-----------+                    |
|                                                                      |
|  X AUCUN ACCES GITHUB                                               |
|  X AUCUN TOKEN REQUIS                                               |
|  X AUCUNE CONNEXION INTERNET REQUISE                                |
+---------------------------------------------------------------------+

+---------------------------------------------------------------------+
|                    ENVIRONNEMENT DEV                                 |
|                   (Connexion GitHub)                                 |
|                                                                      |
|  +-------------+    +-------------+    +-------------+              |
|  |  Dashboard  |    |   Scripts   |    |  GitHub API |              |
|  |  (dev UI)   |    |  (build)    |    |  (push/pull)|              |
|  +-------------+    +-------------+    +-------------+              |
|                                                                      |
|  [OK] Token GitHub requis                                           |
|  [OK] Endpoints /api/github/*                                       |
|  [OK] Push/Pull/Releases                                            |
+---------------------------------------------------------------------+
```

---

## 2. ENVIRONNEMENT PUBLIC (Utilisateur Final)

### 2.1 Caracteristiques

| Propriete | Valeur |
|-----------|--------|
| **Mode** | 100% OFFLINE |
| **GitHub** | AUCUN ACCES |
| **Token** | NON REQUIS |
| **Internet** | NON REQUIS (apres installation) |
| **Installation** | Telechargement unique d'une release |

### 2.2 Contenu du Build Public

```
THEMIS-QS-v3.3.035/
|-- localagent/              # LocalAgent Service
|   |-- core/
|   |-- connectors/
|   |   |-- llm.py           # [OK] Claude API (optionnel)
|   |   |-- mlx_ai.py        # [OK] MLX local (macOS)
|   |   |-- spotlight.py     # [OK] Spotlight (macOS)
|   |   +-- github.py        # [X] DESACTIVE en prod
|   |-- engine/
|   |-- service/
|   |   +-- routers/
|   |       |-- themis.py    # [OK] ACTIF
|   |       |-- github.py    # [X] DEV ONLY
|   |       +-- ...
|   +-- skills/
|
|-- modules/                  # Modules locaux (pre-installes)
|   |-- themis-ui/
|   |-- prompt-linter/
|   +-- whisper-module/
|
|-- VERSION
+-- manifest.json
```

### 2.3 Endpoints ACTIFS en Production

| Route | Disponible | Description |
|-------|------------|-------------|
| `/themis/*` | OUI | API THEMIS-QS complete |
| `/api/health` | OUI | Health check |
| `/api/chat` | OUI | Chat IA |
| `/api/skills/*` | OUI | Gestion skills |
| `/api/llm/*` | OUI | LLM local/Claude |
| `/api/github/*` | NON | DEV ONLY |
| `/api/releases/*` | NON | DEV ONLY |
| `/api/modules/push` | NON | DEV ONLY |
| `/connector/dashboard/*` | NON | DEV ONLY |

### 2.4 Flux Utilisateur Final

```
1. Telecharge release (une fois)
         |
         v
2. Installe localement
         |
         v
3. Lance THEMIS-QS
         |
         v
4. Utilise 100% offline
   (aucune connexion GitHub)
```

---

## 3. ENVIRONNEMENT DEV (Developpeur)

### 3.1 Caracteristiques

| Propriete | Valeur |
|-----------|--------|
| **Mode** | Connecte |
| **GitHub** | REQUIS |
| **Token** | `~/.localagent-dev/github_token` |
| **Internet** | REQUIS |

### 3.2 Composants DEV Only

| Composant | Chemin | Role |
|-----------|--------|------|
| Dashboard | `dashboard/` | Interface dev |
| Scripts | `scripts/` | Build, versioning |
| Tests | `tests/` | Tests unitaires |
| GitHub connector | `connectors/github.py` | Push/Pull |

### 3.3 Endpoints DEV Only

| Route | Role |
|-------|------|
| `GET /api/github/status` | Etat connexion GitHub |
| `POST /api/github/push` | Push vers repos |
| `POST /api/github/sync` | Sync repos |
| `GET /api/github/releases/*` | Liste releases |
| `POST /api/github/create-repo` | Creer repo |
| `GET /api/github/workflow-status` | Status CI/CD |
| `GET /api/releases/*` | Gestion releases |
| `POST /api/changelog/*` | Sync changelog |
| `GET /api/build/check` | Check updates (dev) |
| `GET /` | Dashboard dev |
| `/connector/dashboard/*` | WebSocket dashboard |

### 3.4 Repos GitHub (DEV Only)

| Repo | Role | Acces |
|------|------|-------|
| `THEMiS-eng/localagent-service` | Code source | DEV |
| `THEMiS-eng/localagent-builds` | Builds packages | DEV -> PUBLIC (releases) |
| `THEMiS-eng/localagent-dashboard` | Dashboard dev | DEV |
| `THEMiS-eng/themis-ui` | UI source | DEV |
| `THEMiS-eng/prompt-linter` | Module source | DEV |

### 3.5 Flux Developpeur

```
1. Clone depuis GitHub
         |
         v
2. Developpe localement
         |
         v
3. bump_version.py (incremente versions)
         |
         v
4. push_build.py (push vers GitHub)
         |
         v
5. GitHub Actions (CI/CD)
         |
         v
6. Release publique (telechargeable)
         |
         v
7. Utilisateur final telecharge
   (fin de l'interaction GitHub)
```

---

## 4. THEMIS-QS (Produit Principal)

### 4.1 Fonctionnement

```
THEMIS-QS (100% Offline)
         |
         |-- UI: themis-ui (pre-installe localement)
         |       +-- ~/.localagent/modules/themis-ui/
         |
         |-- Backend: LocalAgent Service
         |       +-- Route /themis/* (84 endpoints)
         |
         |-- IA: MLX local (macOS) ou Claude API (optionnel)
         |
         +-- Storage: ~/.localagent/themis/
                 +-- Donnees 100% locales
```

### 4.2 Connexions Reseau (Prod)

| Service | Requis | Usage |
|---------|--------|-------|
| GitHub | NON | Jamais en prod |
| Claude API | OPTIONNEL | Chat IA (si configure) |
| Internet | NON | Fonctionne offline |

---

## 5. MODULES

### 5.1 Modules Distribues (Build Public)

| Module | Role | Stockage |
|--------|------|----------|
| `themis-ui` | Interface principale THEMIS-QS | `~/.localagent/modules/themis-ui/` |
| `prompt-linter` | Linting des prompts | `~/.localagent/modules/prompt-linter/` |
| `whisper-module` | Transcription vocale | `~/.localagent/modules/whisper-module/` |
| `skills-engine` | Moteur de skills | `~/.localagent/modules/skills-engine/` |

### 5.2 Chargement des Modules

**En Production (PUBLIC):**
```
1. Charge depuis ~/.localagent/modules/<module>/
2. Pas de fallback GitHub (offline)
```

**En Developpement (DEV):**
```
1. Charge depuis ~/.localagent/modules/<module>/
2. Fallback: raw.githubusercontent.com/THEMiS-eng/<module>/
```

---

## 6. VERSIONING

### 6.1 En Production (Public)

| Fichier | Contenu | Modifiable |
|---------|---------|------------|
| `VERSION` | Version installee | Lecture seule |
| `manifest.json` | Modules installes | Lecture seule |

### 6.2 En Developpement

| Fichier | Contenu | Modifiable |
|---------|---------|------------|
| `~/.localagent/BUILD` | Build global | Via scripts |
| `~/.localagent/modules/*/VERSION` | Par module | Via scripts |
| `~/.localagent/manifest.json` | Manifest | Via scripts |

### 6.3 Modules Versionnes

| Module | Chemin VERSION |
|--------|----------------|
| `core` | `~/.localagent/modules/core/VERSION` |
| `engine` | `~/.localagent/modules/engine/VERSION` |
| `connectors` | `~/.localagent/modules/connectors/VERSION` |
| `skills` | `~/.localagent/modules/skills/VERSION` |
| `roadmap` | `~/.localagent/modules/roadmap/VERSION` |

### 6.4 Flux de Versioning (DEV Only)

```
bump_version.py <module>
         |
         |-- ~/.localagent/modules/<module>/VERSION ++
         |-- ~/.localagent/BUILD ++
         +-- ~/.localagent/manifest.json (update)
         |
         v
push_build.py
         |
         +-- git commit + push -> GitHub
         |
         v
GitHub Release
         |
         +-- Utilisateur telecharge (offline apres)
```

---

## 7. ENDPOINTS API

### 7.1 Endpoints THEMIS-QS (Production)

| Categorie | Route | Description |
|-----------|-------|-------------|
| Health | `GET /themis/api/health` | Status service |
| Cases | `GET/POST /themis/api/cases` | Gestion dossiers |
| Evidence | `GET/POST /themis/api/evidence` | Pieces justificatives |
| Chat | `POST /themis/api/chat` | Chat IA avec skills |
| Search | `GET /themis/api/search/*` | Recherche Spotlight |
| Tags | `GET/POST /themis/api/tags/*` | Tags macOS natifs |
| Frameworks | `GET /themis/api/frameworks` | RICS, SCL, FAR |
| Analysis | `GET /themis/api/analysis/*` | Analyses juridiques |
| Folders | `GET /themis/api/folders` | Navigation dossiers |
| SCL | `GET /themis/api/scl/*` | Protocol SCL |
| MLX | `GET /themis/api/mlx-feeder/*` | Classification IA |

### 7.2 Endpoints LocalAgent (Production)

| Route | Description |
|-------|-------------|
| `GET /api/health` | Health check + versions |
| `POST /api/chat` | Chat avec Claude |
| `GET /api/skills/*` | Gestion skills |
| `POST /api/llm/*` | Appels LLM |

### 7.3 Endpoints DEV Only

| Route | Description |
|-------|-------------|
| `GET /` | Dashboard dev |
| `/api/github/*` | Toutes operations GitHub |
| `/api/releases/*` | Gestion releases |
| `/api/build/*` | Check updates |
| `/api/changelog/*` | Sync changelog |
| `/connector/dashboard/*` | WebSocket dashboard |

---

## 8. STOCKAGE

### 8.1 Chemins Principaux

| Chemin | Contenu | Env |
|--------|---------|-----|
| `~/.localagent/` | Donnees runtime | PUBLIC + DEV |
| `~/.localagent/modules/` | Modules installes | PUBLIC + DEV |
| `~/.localagent/themis/` | Donnees THEMIS-QS | PUBLIC + DEV |
| `~/.localagent/logs/` | Logs service | PUBLIC + DEV |
| `~/.localagent-dev/` | Tokens dev | DEV ONLY |
| `~/.localagent-dev/github_token` | Token GitHub | DEV ONLY |

### 8.2 Fichiers de Configuration

| Fichier | Env | Usage |
|---------|-----|-------|
| `~/.localagent/BUILD` | DEV | Version build |
| `~/.localagent/manifest.json` | BOTH | Manifest modules |
| `~/.localagent/config/github.json` | DEV | Config GitHub |
| `~/.localagent/service/daemon.pid` | BOTH | PID daemon |

---

## 9. RESUME

### 9.1 Matrice Composants

| Composant | PUBLIC | DEV | GitHub |
|-----------|--------|-----|--------|
| THEMIS-QS | OUI | OUI | NON |
| LocalAgent Service | OUI | OUI | NON |
| Modules (themis-ui, etc.) | OUI | OUI | NON |
| Dashboard | NON | OUI | OUI |
| Scripts (bump, push) | NON | OUI | OUI |
| /api/github/* | NON | OUI | OUI |
| /api/releases/* | NON | OUI | OUI |

### 9.2 Matrice Connexions

| Connexion | PUBLIC | DEV |
|-----------|--------|-----|
| GitHub API | NON | OUI |
| GitHub Token | NON | OUI |
| Internet (apres install) | NON | OUI |
| Claude API | Optionnel | Optionnel |
| MLX Local | OUI | OUI |

### 9.3 Principe Cle

```
+--------------------------------------------------------+
|                                                        |
|   GitHub existe UNIQUEMENT dans l'environnement DEV   |
|                                                        |
|   L'utilisateur final ne voit JAMAIS GitHub           |
|   L'utilisateur final n'a JAMAIS besoin de token      |
|   L'utilisateur final fonctionne 100% OFFLINE         |
|                                                        |
+--------------------------------------------------------+
```

---

## 10. REFERENCES CODE

| Fichier | Ligne | Description |
|---------|-------|-------------|
| `localagent/connectors/github.py` | 28-38 | Definition REPOS |
| `localagent/service/server.py` | 21-24 | Config HOST/PORT |
| `localagent/service/daemon.py` | 12-15 | Chemins PID/LOG |
| `localagent/connectors/themis_connector.py` | 27-30 | Config Themis |
| `scripts/bump_version.py` | 25-31 | Chemins versions |

---

## 11. HISTORIQUE DES MODIFICATIONS

| Version | Date | Auteur | Changements |
|---------|------|--------|-------------|
| 0.1.0 | 2026-02-03 | Claude Code | Creation initiale, chemins critiques ajoutes |

---

*Document genere par analyse statique du code source.*
