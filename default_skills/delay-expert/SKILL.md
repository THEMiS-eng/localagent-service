---
name: delay-expert
description: >
  Forensic schedule analysis expert for ADR proceedings. Provides independent delay
  analysis for mediation, adjudication, arbitration, and expert determination.
  
  Triggers-Core: TIA, time impact analysis, fragnet, collapsed as-built, impacted as-planned,
  windows analysis, contemporaneous period analysis, SCL protocol, AACE RP 29R-03,
  as-planned vs as-built, MIP, TIP, forensic schedule, but-for analysis.
  
  Triggers-Strong: critical path, longest path, driving logic, float, total float, free float,
  near-critical, baseline, as-built, retrospective, prospective, delay analysis,
  concurrent delay, pacing delay, excusable delay, compensable delay, culpable delay,
  extension of time, EOT, prolongation, schedule impact, Primavera, P6, XER, MPP,
  RFI delay, submittal delay, approval delay, late information.
  
  Triggers-Weak: delay, schedule, programme, program, activity, duration, sequence, logic,
  predecessor, successor, milestone, constraint, lag, lead, calendar, progress,
  slippage, variance, update, status, impact, cause, effect,
  RFI, submittal, shop drawing, approval, information, design, drawing.
  
  Use when: preparing delay expert reports, analyzing schedule impacts for disputes,
  providing independent schedule opinions for ADR, reviewing opposing delay claims,
  quantifying excusable/compensable delay, establishing causation between events and delay.
  
  ADR Context: Expert witness in arbitration, single joint expert in adjudication,
  technical advisor in mediation, expert determiner for schedule disputes.
---

# Delay Expert

Independent forensic schedule analysis for ADR proceedings.

## Expert Role

As delay expert in ADR:
- **Arbitration**: Party-appointed or tribunal-appointed expert witness
- **Adjudication**: Responding to/preparing referral, advising adjudicator
- **Mediation**: Technical advisor, reality-testing delay positions
- **Expert Determination**: Acting as expert determiner on schedule disputes

## Prompt Rewrites

### delay expert report | expert witness | opinion retard
```
Prepare Delay Expert Report for [ARBITRATION/ADJUDICATION/EXPERT DETERMINATION]:

CASE CONTEXT: {{framework}} / {{methodology}} / {{jurisdiction}}
CASE REFERENCE: [tribunal/adjudicator reference]
INSTRUCTING PARTY: [Claimant/Respondent/Tribunal]
OPPOSING EXPERT: [name, if known]

1. INSTRUCTIONS
   - Date of instruction: [YYYY-MM-DD]
   - Issues to address: [list specific questions]
   - Documents provided: [list key documents]

2. EXPERT QUALIFICATIONS
   - Professional background
   - Relevant experience
   - Prior expert appointments

3. PROJECT BACKGROUND
   - Contract particulars
   - Original programme
   - Key milestones
   - Actual completion

4. METHODOLOGY
   {{#if uses_aace}}
   - Analysis per AACE RP 29R-03
   - Method: [MIP-3/MIP-5/Contemporaneous Period Analysis]
   {{/if}}
   {{#if uses_scl}}
   - Analysis per SCL Delay and Disruption Protocol (2nd Ed.)
   - Method: [Time Impact/Windows/As-Planned vs As-Built]
   {{/if}}
   - Software used: [P6/Asta/MS Project]
   - Assumptions made

5. SCHEDULE ANALYSIS
   - Baseline schedule assessment
   - As-built schedule reconstruction
   - Critical path identification
   - Float analysis

6. DELAY EVENTS ANALYSIS
   [For each delay event:]
   - Event description
   - Date range
   - Causation analysis
   - Critical path impact
   - Responsibility attribution
   {{#if is_us_federal}}
   - Excusable/Compensable determination per FAR 52.249
   {{/if}}
   - Quantification (days)

7. CONCURRENT DELAY ASSESSMENT
   {{#if uses_scl}}
   - SCL Protocol Core Principle 11 application
   - Dominant cause analysis
   {{/if}}
   {{#if uses_aace}}
   - AACE concurrent delay treatment
   - Apportionment methodology
   {{/if}}
   - Net effect calculation

8. OPINIONS
   - Opinion 1: [clear, numbered opinion]
   - Opinion 2: [...]
   - Qualifications to opinions

9. EXPERT DECLARATION
   - Independence statement
   - Duty to tribunal
   - No conflict of interest
   - Signature and date

APPENDICES:
- A: CV and prior appointments
- B: Documents reviewed
- C: Schedule analysis outputs
- D: Chronology
- E: Calculations
```

### TIA | time impact analysis | analyse d'impact
```
Perform Time Impact Analysis ({{methodology}}):

CASE CONTEXT: {{case_name}} - {{framework}}
INSERTION POINT DATA DATE: [YYYY-MM-DD]
DELAY EVENT REFERENCE: [event ID from chronology]

{{#if uses_aace}}
AACE RP 29R-03 METHODOLOGY:
- Implementation: MIP-3 (Modeled/Isolated/Contemporaneous)
- Fragnet insertion approach
- Float consumption tracking
{{/if}}
{{#if uses_scl}}
SCL PROTOCOL METHODOLOGY:
- Time Impact Analysis per Core Principle 7
- Prospective/Retrospective application
- Baseline programme assessment
{{/if}}

PRE-IMPACT STATUS:
- Schedule version: [reference]
- Data date: [YYYY-MM-DD]  
- Project completion: [YYYY-MM-DD]
- Critical path: [key activities]
- Available float: [days] on [activity]

DELAY FRAGNET:
| Activity ID | Description | Duration | Predecessors | Successors |
|-------------|-------------|----------|--------------|------------|
| DEL-001 | [delay activity] | [X] days | [ID] FS+[lag] | [ID] |
| | | | | |

FRAGNET LOGIC JUSTIFICATION:
- Why these predecessors: [explanation]
- Why these successors: [explanation]
- Duration basis: [contemporaneous record reference]

POST-IMPACT RESULT:
- New completion date: [YYYY-MM-DD]
- Delay to completion: [X] calendar days
- Float consumed: [X] days
- New critical path: [if changed]

CAUSATION LINK:
- Event: [description]
- Contemporaneous evidence: [document references]
- But-for test: [without this event, completion would have been...]

RESPONSIBILITY: [Owner/Contractor/Shared/Neutral Event]
```

### concurrent delay | délai concomitant | apportionment
```
Analyze concurrent delays for ADR:

ANALYSIS PERIOD: [start YYYY-MM-DD] to [end YYYY-MM-DD]

OWNER-RESPONSIBLE DELAYS:
| Ref | Event | Start | End | Days | Evidence | CP Impact |
|-----|-------|-------|-----|------|----------|-----------|
| O-1 | [description] | | | | [doc ref] | [Y/N] |
| | | | | | | |

CONTRACTOR-RESPONSIBLE DELAYS:
| Ref | Event | Start | End | Days | Evidence | CP Impact |
|-----|-------|-------|-----|------|----------|-----------|
| C-1 | [description] | | | | [doc ref] | [Y/N] |
| | | | | | | |

CONCURRENCY ANALYSIS:

Period 1: [date range]
- Owner delay: [O-X] - [X] days on critical path
- Contractor delay: [C-X] - [X] days on critical path  
- Overlap: [X] days
- True concurrency test: Both independently critical? [Y/N]

APPORTIONMENT METHODOLOGY:
- [ ] Dominant cause (Devlin approach)
- [ ] Apportionment (Malmaison)
- [ ] But-for on each delay
- [ ] First-in-time

APPLICATION:
[Apply selected methodology with reasoning]

NET ENTITLEMENT:
- Gross owner delay: [X] days
- Less concurrent periods: [X] days
- Net compensable delay: [X] days
- Net excusable delay: [X] days (if different)
```

### windows analysis | analyse par fenêtres | retrospective
```
Perform Windows Analysis for ADR:

WINDOW DEFINITION:
| Window | Period | Basis for Selection |
|--------|--------|---------------------|
| W1 | [start] to [end] | [monthly/milestone/event-driven] |
| W2 | [start] to [end] | |
| W3 | [start] to [end] | |

FOR EACH WINDOW:

WINDOW [X]: [start] to [end]

Opening Position:
- Planned completion: [date]
- Critical path: [activities]
- Float status: [days on key activities]

Delay Events in Window:
| Event | Responsible | Days | Critical? |
|-------|-------------|------|-----------|
| | | | |

Progress Achieved:
- Planned: [% or activities]
- Actual: [% or activities]
- Variance explanation:

Closing Position:
- Revised completion: [date]
- Critical path: [activities - note changes]
- Float status: [days]

Window Summary:
- Owner delays: [X] days
- Contractor delays: [X] days
- Net movement: [X] days [gain/slip]

CUMULATIVE SUMMARY:
| Window | Owner | Contractor | Cumulative Slip |
|--------|-------|------------|-----------------|
| W1 | | | |
| W2 | | | |
| TOTAL | | | |
```

### critical path | longest path | chemin critique
```
Critical path analysis for ADR opinion:

SCHEDULE: [reference]
DATA DATE: [YYYY-MM-DD]
SOFTWARE: [P6/Asta/MS Project]

METHODOLOGY:
- [ ] Longest path (recommended for disputes)
- [ ] Total float = 0
- [ ] Driving logic trace
- [ ] Multiple float paths

CRITICAL PATH IDENTIFICATION:
| Seq | Activity ID | Description | Duration | TF | Predecessors |
|-----|-------------|-------------|----------|----|--------------| 
| 1 | | | | 0 | |
| 2 | | | | 0 | |

NEAR-CRITICAL PATHS (TF ≤ 10):
| Path | Activities | Total Float | Risk Assessment |
|------|------------|-------------|-----------------|
| NC-1 | [IDs] | [X] days | [probability of becoming critical] |

CRITICAL PATH CHANGES OVER PROJECT:
| Period | Critical Path | Cause of Change |
|--------|---------------|-----------------|
| Baseline | [activities] | - |
| [date] | [activities] | [event causing change] |

OPINION ON CRITICALITY:
[Expert opinion on what drove the critical path and how delay events affected it]
```

### schedule analysis review | rebuttal | contre-expertise
```
Review opposing delay expert report:

OPPOSING EXPERT: [name]
REPORT DATE: [YYYY-MM-DD]
METHODOLOGY USED: [TIA/Windows/other]

AREAS OF AGREEMENT:
| Item | Opposing Position | Our Position | Status |
|------|-------------------|--------------|--------|
| Baseline validity | | | Agreed |
| As-built accuracy | | | Agreed |
| | | | |

AREAS OF DISAGREEMENT:

1. METHODOLOGY CRITIQUE
   - Opposing approach: [description]
   - Our objection: [why inappropriate]
   - Impact of error: [quantification if possible]

2. BASELINE ISSUES
   - Opposing position: [description]
   - Our position: [our view]
   - Evidence: [supporting documents]

3. AS-BUILT ISSUES
   - [same structure]

4. DELAY EVENT ANALYSIS
   | Event | Opposing Days | Our Days | Difference | Reason |
   |-------|---------------|----------|------------|--------|
   | | | | | |

5. CONCURRENCY TREATMENT
   - Opposing approach: [description]
   - Our approach: [description]
   - Impact: [X] days difference

SUMMARY OF DIFFERENCES:
- Opposing total: [X] days
- Our total: [X] days
- Variance: [X] days
- Key drivers of variance: [list main items]
```

## ADR-Specific Requirements

### For Adjudication (28-day timeline)
- Rapid turnaround analysis
- Focus on headline issues
- Reserve detailed analysis for arbitration
- Ensure crystallized dispute addressed

### For Arbitration
- Full forensic analysis
- Respond to directions/procedural orders
- Prepare for cross-examination
- Joint expert meetings/statement

### For Expert Determination
- Final and binding opinion
- Exhaustive analysis required
- Clear methodology disclosure
- Reasoned decision

## Constraints

- Independence and impartiality paramount
- Disclose all assumptions
- Acknowledge limitations of analysis
- Reference contemporaneous records
- Dates in ISO 8601 (YYYY-MM-DD)
- Calendar days unless stated otherwise
- Comply with tribunal directions
- Protocol-compliant reports (Civil Evidence Act/IBA Rules)

## Scripts

- `scripts/critical_path.py` - Extract and analyze critical path
- `scripts/float_analysis.py` - Float consumption tracking
- `scripts/window_analyzer.py` - Automated windows analysis
- `scripts/tia_calculator.py` - Time impact quantification

## References

- `references/aace-29r-03.md` - AACE forensic schedule analysis
- `references/scl-protocol.md` - SCL Delay Protocol 2nd Edition
- `references/expert-duties.md` - Expert witness obligations
- `references/concurrent-delay.md` - Concurrency case law
