---
name: arbitration-support
description: >
  Construction arbitration support for binding dispute resolution. Formal proceedings
  under institutional rules (ICC, LCIA, DIAC, SIAC, HKIAC) or ad hoc (UNCITRAL).
  
  Triggers-Core: ICC arbitration, LCIA, DIAC, SIAC, HKIAC, UNCITRAL, FIDIC DAAB,
  Redfern Schedule, IBA Rules, New York Convention, terms of reference,
  procedural order, tribunal secretary, emergency arbitrator.
  
  Triggers-Strong: arbitration, arbitrator, tribunal, award, memorial, counter-memorial,
  statement of claim, statement of defense, witness statement, expert report,
  document production, hearing, cross-examination, post-hearing brief, costs award,
  partial award, final award, seat, governing law, bifurcation.
  
  Triggers-Weak: dispute resolution, proceeding, submission, evidence, witness, expert,
  document, hearing, decision, finding, order, request, response, reply, costs.
  
  Use when: commencing arbitration, responding to arbitration, preparing memorials,
  document production, witness preparation, expert coordination, hearing preparation,
  post-hearing submissions, costs applications, award enforcement.
  
  ADR Context: Final and binding dispute resolution for construction disputes,
  often mandated by contract (FIDIC, NEC Option W2). International enforcement
  under New York Convention.
---

# Arbitration Support

Construction arbitration proceedings support.

## Prompt Rewrites

### arbitration strategy | stratégie
```
Develop arbitration strategy:

DISPUTE VALUE: [currency] [amount]
CONTRACT CLAUSE: [quote arbitration agreement]

ANALYSIS:

1. ARBITRATION AGREEMENT
   - Seat: [jurisdiction]
   - Rules: [ICC/LCIA/UNCITRAL]
   - Arbitrators: [1/3]
   - Language: [language]
   - Governing law: [law]

2. TRIBUNAL COMPOSITION
   Three-arbitrator panel:
   - Our nominee: [candidate profile]
   - Opposing nominee: [anticipate]
   - Chair profile: [desired attributes]

3. CASE ASSESSMENT
   - Strengths: [list]
   - Weaknesses: [list]
   - Key issues: [list]
   - Best case: [amount]
   - Worst case: [amount]
   - Settlement range: [amount]

4. BUDGET
   - Legal: [amount]
   - Experts: [amount]
   - Tribunal: [amount]
   - Total: [amount]

5. TIMELINE
   Estimated duration: [X] months
```

### request for arbitration | demande | commencement
```
Prepare Request for Arbitration:

INSTITUTION: [ICC/LCIA/other]

---

REQUEST FOR ARBITRATION

1. PARTIES
   Claimant: [full details]
   Respondent: [full details]

2. ARBITRATION AGREEMENT
   "[Quote clause]"
   Seat: [location]
   Rules: [version]
   Language: [language]

3. FACTUAL BACKGROUND
   [Brief project and dispute summary]

4. CLAIMS
   (a) Declaration: [describe]
   (b) Payment: [currency] [amount]
   (c) Interest: [rate] from [date]
   (d) Costs

5. ARBITRATOR NOMINATION
   [Name] - CV attached

6. ATTACHMENTS
   - Contract extract
   - Power of attorney
   - Arbitrator CV
   - Registration fee
```

### memorial | mémoire | statement of claim
```
Prepare Memorial:

---

CLAIMANT'S MEMORIAL

1. INTRODUCTION
   [Case overview, relief sought]

2. FACTUAL BACKGROUND
   [Detailed chronological narrative]

3. CONTRACT PROVISIONS
   [Key clauses quoted and explained]

4. THE CLAIMS
   4.1 Delay Claims [per event]
   4.2 Cost Claims [per head]
   4.3 Variation Claims [per VO]

5. LEGAL ANALYSIS
   [Contract interpretation, authorities]

6. QUANTUM
   [Summary table, cross-ref expert]

7. INTEREST
   [Basis, rate, calculation]

8. RELIEF SOUGHT
   [Specific orders requested]

EXHIBITS: [C-001 to C-XXX]
AUTHORITIES: [CLA-001 to CLA-XXX]
```

### Redfern Schedule | document production
```
Prepare document production request:

---

REDFERN SCHEDULE

| No. | Documents Requested | Relevance | Objection | Reply | Decision |
|-----|---------------------|-----------|-----------|-------|----------|

REQUEST 1:

(a) Documents:
All correspondence between [persons] regarding [subject] from [date] to [date].

(b) Relevance:
Relates to [issue]. Documents likely to show [what].

(c) IBA Rules Compliance:
- Sufficiently particular: [explain]
- Relevant and material: [explain]
- Not in our possession: [explain]
```

### hearing preparation | audience
```
Prepare for arbitration hearing:

DATES: [dates]
VENUE: [location]
DURATION: [days]

SCHEDULE:
| Day | Time | Activity |
|-----|------|----------|
| 1 | 09:00 | Opening - Claimant |
| 1 | 11:00 | Opening - Respondent |
| 1-2 | | Fact witnesses |
| 3-4 | | Expert witnesses |
| 5 | | Closings |

OPENING OUTLINE:
1. Case summary (5 min)
2. Key facts (20 min)
3. Key documents (15 min)
4. Legal framework (15 min)
5. Claims (30 min)
6. Relief (5 min)

WITNESS PREPARATION:
- Documents to review
- Key topics
- Anticipated cross-examination

CROSS-EXAMINATION PLAN:
| Witness | Objective | Key Docs | Questions |
|---------|-----------|----------|-----------|
```

### post-hearing brief | submissions finales
```
Prepare post-hearing brief:

---

POST-HEARING BRIEF

1. INTRODUCTION

2. KEY HEARING EVIDENCE
   2.1 Witness [Name]: [key testimony, transcript refs]
   2.2 Expert [Name]: [key opinions confirmed]

3. RESPONSE TO RESPONDENT
   [Address arguments raised at hearing]

4. LEGAL SUBMISSIONS
   [Final legal analysis]

5. QUANTUM
   | Head | Claimed | As Established |
   |------|---------|----------------|

6. CONCLUSION

TRANSCRIPT REFERENCES: [table]
```

## Arbitration Timeline (ICC)

| Stage | Typical Timing |
|-------|----------------|
| Request | Day 0 |
| Answer | 30 days |
| Tribunal constitution | 60-90 days |
| Terms of Reference | 30 days |
| Procedural Order 1 | 30 days |
| Memorials | 60-90 days each |
| Document production | 60 days |
| Witness statements | 60 days |
| Expert reports | 60 days |
| Hearing | Variable |
| Post-hearing | 30-60 days |
| Award | 3-6 months |

## Constraints

- Follow tribunal directions strictly
- Observe time limits
- Maintain privilege
- Comply with IBA Rules on Evidence
- Respect confidentiality
- Prepare for costs implications

## References

- `references/icc-rules.md` - ICC Rules summary
- `references/lcia-rules.md` - LCIA Rules summary
- `references/iba-evidence.md` - IBA Rules on Evidence
- `references/enforcement.md` - New York Convention
