# CHANGELOG

All notable changes to LocalAgent / THEMIS-QS will be documented in this file.

## [10.5.31] - 2026-01-31

### Added - FULL NEGOTIATOR INTEGRATION

**Console Error → Negotiator → LLM Retry Loop**

The Negotiator now intercepts runtime errors from executed code and automatically retries with the LLM to fix them.

```
User Prompt → LLM Response → Execute (HTML/JS/Code)
                                    ↓
                            Console Error Caught?
                                    ↓ YES
                    ┌───────────────────────────────┐
                    │         NEGOTIATOR            │
                    │  1. classify_console_error()  │
                    │  2. build_error_feedback()    │
                    │  3. learn_from_error()        │
                    │  4. should_retry()?           │
                    │  5. Retry with feedback       │
                    └───────────────────────────────┘
                                    ↓
                            Corrected Response
                                    ↓
                            Update UI + Learning
```

**Backend Changes**:
- `POST /themis/api/chat/error` - Receives console errors from frontend
- `DELETE /themis/api/chat/error/{message_id}` - Clears error tracking on success
- `classify_console_error()` - Maps error patterns to types (syntax_error, reference_error, etc.)
- `build_error_feedback()` - Builds detailed feedback for LLM retry
- New NEGOTIATION_STRATEGIES for runtime errors:
  - `runtime_error` (max_retries: 3)
  - `syntax_error` (max_retries: 3)
  - `reference_error` (max_retries: 2)
  - `type_error` (max_retries: 2)
  - `console_error` (max_retries: 3)
  - `render_error` (max_retries: 2)
  - `network_error` (max_retries: 1)

**Frontend Changes**:
- `setLastLLMContext()` - Stores response context for error correction
- `triggerErrorCorrection()` - Sends errors to backend Negotiator
- `isLLMCodeError()` - Detects if error is from LLM-generated code
- `negotiator-correction` event listener - Updates UI on correction
- Auto-correction banner shows retry status in real-time

**Console Error Patterns Detected**:
- JavaScript: SyntaxError, ReferenceError, TypeError, RangeError
- React/JSX: Invalid hook call, is not defined, is not a function
- Network: CORS, 404, 500, Failed to load resource
- Python: IndentationError, NameError, ImportError, ValueError, KeyError

**UI Feedback**:
- 🔄 Orange banner during correction: "Negotiator: Correcting error..."
- ✅ Green banner on success: "Correction applied (attempt N)"
- ❌ Red banner on failure: "Correction failed"
- Steps panel auto-expands to show correction history
- Corrected message shows "🔄 Auto-corrected" indicator

**Learning Integration**:
- Every error correction enriches the Learning Engine
- Patterns are stored per project/skill combination
- Future prompts benefit from learned solutions

## [10.5.30] - 2026-01-31

### Added - NEGOTIATOR UI Integration

**Backend - Protocol Steps Tracking**:
- `/api/chat` now returns `protocol` array with step-by-step execution status
- Each step has: `step`, `label`, `status` (running/complete/error), `issues`, `violations`
- Returns `negotiation_attempts` and `negotiation_success` for validation tracking
- Returns `auto_expand: true` when errors occur to signal UI

**Protocol Steps Returned**:
1. `skill_matching` - Shows matched skill or "No skill matched"
2. `case_context` - Shows loaded case context (framework/methodology)
3. `llm_call` - Shows AI source (MLX/Claude) and response status
4. `validation` - Shows Negotiator validation score and violations

**Frontend - Auto-Expand on Errors**:
- Processing panel now **auto-expands** when errors/violations occur
- Processing panel **collapses** when all steps succeed
- Individual step content auto-expands when it has issues or violations
- Global violations displayed in dedicated error step
- Negotiation status shows validation result with attempts count

**Visual Feedback**:
- ✅ Green checkmark for success
- ❌ Red X for errors
- ⚠️ Warning for issues
- 🔄 Retry icon for negotiation

**Response Format**:
```json
{
  "response": "...",
  "skill_used": "delay-expert",
  "protocol": [
    {"step": "skill_matching", "label": "🎯 Skill: delay-expert", "status": "complete"},
    {"step": "case_context", "label": "📋 Context: RICS/AACE", "status": "complete"},
    {"step": "llm_call", "label": "🤖 MLX responded", "status": "complete"},
    {"step": "validation", "label": "✅ Valid (score: 85)", "status": "complete", "issues": ["..."]}
  ],
  "negotiation_attempts": 1,
  "negotiation_success": true,
  "violations": [],
  "auto_expand": false
}
```

## [10.5.29] - 2026-01-31

### Added - NEGOTIATOR: Skill Constraint Validation

**Core Validators** (in `localagent/core/negotiator.py`):
- `currency_stated` - Validates amounts have currency specified
- `vat_treatment` - Checks VAT/tax treatment is specified
- `interest_separate` - Ensures interest calculations shown separately
- `mitigation_addressed` - Checks mitigation is addressed
- `causation_established` - Verifies causation links per head of claim
- `assumptions_stated` - Confirms assumptions are documented
- `methodology_specified` - Validates methodology is specified
- `framework_reference` - Checks for AACE/RICS/SCL references
- `dates_specified` - Validates dates are included
- `period_quantified` - Ensures time periods are quantified

**Functions**:
- `parse_skill_constraints(skill_body)` - Extract constraints from skill markdown
- `get_validators_for_skill(skill_name, skill_body)` - Get applicable validators
- `validate_output_against_skill(output, skill_name, skill_body, strict)` - Main validation
- `build_retry_prompt_with_skill_feedback(...)` - Build retry prompt with feedback

**API Endpoints**:
- `POST /api/protocol/validate-output` - Validate LLM output against skill
- `POST /api/protocol/negotiate` - Full negotiation cycle with retry prompt

**Validation Result Structure**:
```json
{
  "valid": true/false,
  "violations": [{"constraint": "...", "error": "...", "severity": "high/medium/low"}],
  "warnings": [{"constraint": "...", "suggestion": "..."}],
  "score": 0-100,
  "feedback": "string for retry prompt"
}
```

**Severity Levels**:
- `high`: Blocks validation (currency, causation, methodology)
- `medium`: Warning by default, blocks in strict mode (VAT, mitigation, assumptions)
- `low`: Always warning only (framework reference, dates)

## [10.5.21] - 2026-01-31

### Fixed
- **Auto-fix button now populates input** - Was using `optimized` but rewrites use `topRewrite.template`
- **Send button now enabled after Auto-fix** - Was staying disabled because button state wasn't updated
- `applyFix()` now prefers `topRewrite.template` over basic `optimized`
- `applyFix()` and `applyRewrite()` now explicitly enable Send button
- Both functions now sync with collapsed input

## [10.5.20] - 2026-01-31

### Added
- **Real-time Skill Suggestions UI** - Skills matched while typing, suggestions displayed above input
- **Skill Selection Flow** - User can click skill badge or apply rewrite template
- **Selected Skill Badge** - Shows active skill with clear button
- States: `linterResult`, `selectedSkill`, `selectedRewrite`, `showSuggestions`
- Debounced linting (300ms) via `PromptLinter.lintPromptAsync()`
- `applyRewrite()` - Apply template and set skill
- `selectSkillOnly()` - Select skill without template
- `clearSkillSelection()` - Clear selection

### Changed
- `handleSend()` now builds `messagePayload` with:
  - `prompt`: final text
  - `selected_skill`: user-selected or null
  - `selected_rewrite`: true if template applied
  - `linter_result`: score, taskType, topSkill, skillMatches
- `ThemisAPI.chat.send()` now receives `skill_context` in options
- Chat endpoint `/api/chat` now:
  - Extracts `skill_context` from request
  - Injects skill system prompt if selected
  - Falls back to `topSkill` from linter if no selection
  - Injects case context (framework, methodology, jurisdiction)
  - Returns `skill_used` in response
- Chat history stores `skill` and `skill_used` per message

### UI Components
```
┌─────────────────────────────────────────┐
│ Skill Suggestions Panel                 │
│ ┌─────────────────────────────────────┐ │
│ │ MATCHED SKILLS                      │ │
│ │ [delay-expert (30)] [quantum (12)]  │ │
│ ├─────────────────────────────────────┤ │
│ │ SUGGESTED TEMPLATES                 │ │
│ │ ┌─────────────────────────────────┐ │ │
│ │ │ delay-expert                    │ │ │
│ │ │ Prepare Delay Expert Report...  │ │ │
│ │ └─────────────────────────────────┘ │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
         ↓ Click to apply
┌─────────────────────────────────────────┐
│ [Using: delay-expert ×]                 │
├─────────────────────────────────────────┤
│ [Template applied in input...]    [Send]│
└─────────────────────────────────────────┘
```

## [10.5.19] - 2026-01-31

### Added
- **Protocol Skill Injection** - Protocol now injects skill context into LLM prompts
- `_match_skills_for_todo()` - Matches skills based on TODO title with weighted triggers
- `_get_skill_template()` - Gets best matching template from skill
- `_apply_context_to_template()` - Applies case context variables to templates
- Case Context injection in `_step_build_claude_context()`
- New API endpoint `POST /api/protocol/build-context` - Preview context without execution
- New API endpoint `POST /api/protocol/execute` - Execute full protocol

### Changed
- `_step_build_claude_context()` now includes:
  - Case Context (case_id, framework, methodology, jurisdiction)
  - Skill Context (is_us_federal, uses_aace, is_delay_case, etc.)
  - Matched Skills with templates
- `_claude_context` now contains `case_context` and `matched_skills`

### Technical Details
```
System Prompt Structure:
1. Base constraints (from build_system_prompt)
2. Version Context (ENV015)
3. Case Context (if available)
4. Matched Skills with templates (top 3)
```

## [10.5.18] - 2026-01-31

### Fixed
- **Release Notes now load without Service Worker** - Local changelog loads even when GitHub unavailable
- Removed early `return` that blocked changelog loading when service worker health check failed
- Console now logs "Adding X local releases" for debugging

## [10.5.17] - 2026-01-31

### Changed
- CHANGELOG.md now contains complete detailed history since v10.3.0
- All 14 versions (10.3.0 → 10.5.16) documented with full details

## [10.5.16] - 2026-01-31

### Added
- **Local CHANGELOG Support** - Release notes now load from local CHANGELOG.md
- New API endpoint `GET /api/changelog` returns parsed releases
- New API endpoint `GET /api/changelog/version/{version}` for specific version
- Local releases merged with GitHub releases in Release Notes modal
- "LOCAL" badge for versions not yet published to GitHub
- Shows up to 15 releases (was 10)

### Changed
- Release Notes modal now shows local versions first
- Better line-height for release notes readability

## [10.5.15] - 2026-01-31

### Added
- **Case Context Injection** - Skills now inherit case attributes (framework, methodology, jurisdiction)
- New `CaseContextManager` in `localagent/core/case_context.py`
- API endpoints: `GET/POST /api/skills/context`, `POST /api/skills/context/from-case`
- Template variables: `{{framework}}`, `{{methodology}}`, `{{jurisdiction}}`
- Conditional templates: `{{#if uses_aace}}...{{/if}}`, `{{#if uses_scl}}...{{/if}}`
- THEMIS auto-syncs context on case selection via `selectCase()`
- `applyContextToTemplate()` function for variable substitution

### Changed
- PromptLinter upgraded to v8.0 with context support
- delay-expert SKILL.md now has AACE/SCL conditional templates

## [10.5.14] - 2026-01-31

### Added
- RFI and submittals triggers to `delay-expert` and `claims-advocate`
- **delay-expert Strong triggers**: RFI delay, submittal delay, approval delay, late information
- **delay-expert Weak triggers**: RFI, submittal, shop drawing, approval, information, design, drawing
- **claims-advocate Strong triggers**: RFI log, submittal log, transmittal, correspondence register
- **claims-advocate Weak triggers**: RFI, submittal, request for information, shop drawing, approval, review

## [10.5.13] - 2026-01-31

### Added
- **Weighted Trigger Categories** for precise skill matching
  - Core (weight 20): Highly specific terms (TIA, Eichleay, HGCRA, Redfern Schedule)
  - Strong (weight 10): Domain-specific terms (critical path, prolongation, arbitration)
  - Weak (weight 3): Generic terms (delay, cost, contract, claim)
- `TRIGGER_WEIGHTS` constant in PromptLinter
- `parseTriggersWeighted()` function for categorized parsing

### Changed
- All 8 ADR skills updated with `Triggers-Core`, `Triggers-Strong`, `Triggers-Weak` sections
- PromptLinter `matchSkills()` now uses category weights instead of trigger length
- Console logging shows trigger breakdown: `(C:13 S:23 W:9)`

## [10.5.12] - 2026-01-31

### Added
- 100+ triggers per skill for comprehensive matching
- Construction-specific terminology across all skills including:
  - Schedule terms: activity, duration, sequence, logic, predecessor, successor, milestone
  - Cost terms: BOQ, schedule of rates, daywork, labour, material, plant
  - Contract terms: waiver, estoppel, repudiation, novation, assignment
  - ADR terms: memorial, witness statement, cross-examination, award

## [10.5.11] - 2026-01-31

### Fixed
- JavaScript template literal syntax errors in version display
- Replaced backtick templates with string concatenation for Safari compatibility
- Fixed: `` `Update available: v${latestVersion}` `` → `"Update available: v" + latestVersion`

## [10.5.10] - 2026-01-31

### Fixed
- Missing `}, []);` closure in useEffect causing "Uncaught SyntaxError: missing ) after argument list"
- Duplicate code block removed after refactoring

## [10.5.9] - 2026-01-31

### Fixed
- API endpoint corrected from `/api/config` to `/api/app` for version fetch
- `curl http://localhost:9998/api/config` was returning 404

## [10.5.8] - 2026-01-31

### Fixed
- Race condition in version loading - `fetchVersion()` and `checkForUpdates()` were running in parallel
- Version comparison now uses locally fetched version, not stale `state.appVersion`
- Refactored to single `initializeApp()` async function that:
  1. Fetches version from API first
  2. Then checks for updates with correct version

## [10.5.7] - 2026-01-31

### Added
- **Dynamic Version Loading** - Version now fetched from `/api/app` at startup
- No more hardcoded version in `themis_react_no_jsx.html`
- Fallback to "10.5.7" if API unavailable

### Changed
- `_get_version()` in `config.py` now searches multiple paths:
  1. Package root (`__file__/../../../VERSION`)
  2. Current working directory (`./VERSION`)
  3. Home directory (`~/.localagent/VERSION`)

## [10.5.6] - 2026-01-31

### Added
- **Two-Stage Skill Matching** in PromptLinter v7.0:
  1. Match prompt against skill TRIGGERS (from description) to identify relevant skills
  2. Match prompt against REWRITE PATTERNS for templates

### Changed
- Triggers parsed dynamically from `Triggers:` line in SKILL.md description
- Removed hardcoded `SKILL_TRIGGERS` object
- `parseTriggers()` function extracts triggers from skill description
- `parseRewrites()` function extracts templates from `## Prompt Rewrites` section

### Fixed
- Version display updated to 10.5.6 in HTML title, appVersion, and banner

## [10.5.5] - 2026-01-31

### Fixed
- Added simple trigger patterns to all skills for basic matching
- Headers changed from `### delay expert report` to `### delay | delay expert report`
- Ensures single-word triggers like "delay", "quantum", "mediation" work

## [10.5.4] - 2026-01-31

### Fixed
- ES5 compatible regex parsing in PromptLinter (no arrow functions, no matchAll)
- Changed `matchAll()` to `exec()` loop for browser compatibility
- Proper regex escaping with `replace(/[.*+?^${}()|[\]\\]/g, '\\$&')`
- Flexible whitespace matching with `replace(/\s+/g, '\\s*')`

## [10.5.3] - 2026-01-31

### Added
- **8 ADR Skills** for construction dispute resolution:

| Skill | Purpose |
|-------|---------|
| `delay-expert` | Forensic schedule analysis, TIA, windows analysis, SCL/AACE methodologies |
| `quantum-expert` | Damages quantification, Eichleay/Hudson formulas, prolongation costs |
| `contract-analyst` | Contract interpretation, entitlement analysis, time bars |
| `claims-advocate` | Claims preparation, notices, Scott Schedules, witness statements |
| `adjudication-support` | UK statutory adjudication, HGCRA, 28-day timeline |
| `arbitration-support` | ICC/LCIA/DIAC proceedings, memorials, Redfern Schedules |
| `mediation-support` | Settlement negotiation, BATNA/WATNA, position papers |
| `expert-determination` | Binding technical decisions, valuation disputes |

- Each skill includes:
  - Structured SKILL.md with triggers and rewrites
  - Prompt rewrite templates for common tasks
  - ADR-specific requirements sections
  - References to industry standards (AACE RP 29R-03, SCL Protocol)

## [10.3.0] - 2026-01-21

### Added
- Initial THEMIS-QS integration with LocalAgent
- Skills system with Anthropic SKILL.md format
- PromptLinter basic implementation
- GitHub release management
- Service worker for offline support
- Landing page with case selection

---

## Backlog

### Planned for v10.6.0
- [ ] Special Skills per CASE (stored in `~/.localagent/cases/{case_id}/skills/`)
- [ ] Skill inheritance (delay-expert-aace, delay-expert-scl variants)
- [ ] Multi-skill UI showing top 3 matches with scores
- [ ] Skill marketplace integration

### Planned for v11.0.0
- [ ] AI-powered skill generation from case documents
- [ ] Cross-case learning from similar disputes
- [ ] Expert report auto-generation with citations
- [ ] Evidence linking in templates
