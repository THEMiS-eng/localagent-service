---
name: contract-analyst
description: >
  Construction contract analysis for ADR proceedings. Interprets contract provisions,
  identifies entitlements, analyzes conditions precedent, and evaluates defenses.
  
  Triggers-Core: condition precedent, time bar, prevention principle, time at large,
  contra proferentem, entire agreement, no oral modification, FIDIC Sub-Clause,
  NEC clause, JCT clause, compensation event, relevant event, relevant matter.
  
  Triggers-Strong: entitlement, breach, contract interpretation, liquidated damages, LADs,
  extension of time clause, loss and expense clause, variation clause, termination clause,
  force majeure, exceptional event, notice requirement, compliance, waiver, estoppel,
  FIDIC, NEC, JCT, FAR, DFARS, standard form, amendment, particular conditions.
  
  Triggers-Weak: contract, clause, provision, term, condition, obligation, right, duty,
  notice, instruction, direction, approval, consent, certificate, determination,
  specification, drawing, programme, method statement, quality, defect.
  
  Use when: analyzing contract provisions for claims, identifying entitlement basis,
  evaluating time bar issues, reviewing notice compliance, comparing standard forms,
  advising on contract interpretation for ADR, preparing contract-based submissions.
  
  ADR Context: Legal/technical advisor in arbitration, contract interpretation support
  in adjudication, identifying strengths/weaknesses for mediation.
---

# Contract Analyst

Construction contract analysis for ADR dispute support.

## Role in ADR

Contract analysis underpins every ADR claim:
- **Arbitration**: Entitlement submissions, contract interpretation arguments
- **Adjudication**: Identifying relevant clauses, notice compliance
- **Mediation**: Evaluating legal positions, settlement leverage
- **Expert Determination**: Scope of determination per contract

## Prompt Rewrites

### entitlement | droit | claim basis
```
Analyze contractual entitlement:

CONTRACT: [Form: FIDIC/NEC/JCT/FAR/bespoke]
VERSION: [year/edition]
AMENDMENTS: [list bespoke amendments if any]

CLAIM TYPE: [EOT / Additional Payment / Both / Termination / Other]

EVENT/BREACH: [description of triggering event]
DATE OF EVENT: [YYYY-MM-DD]
DATE DISCOVERED: [YYYY-MM-DD if different]

ENTITLEMENT ANALYSIS:

1. EXPRESS CONTRACTUAL ENTITLEMENT
   
   Primary clause: [Clause X.X]
   Text: "[quote relevant provision]"
   
   Interpretation:
   - Triggering event defined: [quote/explain]
   - Relief available: [EOT/cost/both]
   - Mechanism: [claim procedure]
   
   Application to facts:
   - Event matches trigger: [analysis]
   - Relief available: [analysis]

2. CONDITIONS PRECEDENT
   
   | Requirement | Clause | Deadline | Compliance | Evidence |
   |-------------|--------|----------|------------|----------|
   | Notice of event | [X.X] | [X] days | [Y/N/partial] | [doc ref] |
   | Particulars | [X.X] | [X] days | [Y/N/partial] | [doc ref] |
   | Substantiation | [X.X] | ongoing | [Y/N/partial] | [doc ref] |
   
   Time bar risk: [HIGH/MEDIUM/LOW - explain]

3. DEFENSES/LIMITATIONS
   
   - Contractor's own fault: [Clause X.X - risk allocation]
   - Contributory negligence: [analysis]
   - Failure to mitigate: [Clause X.X]
   - Caps/limitations: [Clause X.X]
   - Exclusions: [Clause X.X]

4. ALTERNATIVE BASES
   
   If primary fails:
   - Alternative clause: [X.X]
   - Implied term: [describe]
   - Breach of contract: [which term]
   - Quantum meruit: [if applicable]

CONCLUSION:
- Entitlement strength: [STRONG/MODERATE/WEAK]
- Key risks: [list]
- Recommended approach: [advice]
```

### time bar | notice | condition precedent | forclusion
```
Analyze notice and time bar compliance:

CONTRACT: [Form and version]
RELEVANT CLAUSE: [Clause number]

NOTICE REQUIREMENTS:

Clause text: "[quote notice provision]"

| Requirement | Contractual Deadline | Actual Date | Status |
|-------------|---------------------|-------------|--------|
| Event occurred | - | [YYYY-MM-DD] | - |
| Awareness date | - | [YYYY-MM-DD] | - |
| Notice required by | [X] days = [date] | - | - |
| Notice given | - | [YYYY-MM-DD] | [compliant/late/none] |
| Particulars by | [X] days = [date] | [YYYY-MM-DD] | [compliant/late/none] |

NOTICE CONTENT ANALYSIS:

Required content per clause:
- [ ] Description of event: [present/absent]
- [ ] Date of event: [present/absent]
- [ ] Intention to claim: [present/absent]
- [ ] Estimated impact: [present/absent]
- [ ] Clause relied upon: [present/absent]

Notice deficiencies: [list any gaps]

TIME BAR ANALYSIS:

Is the time bar:
- [ ] Condition precedent (strict - claim fails if missed)
- [ ] Directory only (substantial compliance sufficient)
- [ ] Subject to waiver/estoppel

Jurisdiction considerations:
- [UK: strict approach post-Bremer Vulkan]
- [Civil law: may be less strict]
- [Specific contract language controls]

WAIVER/ESTOPPEL ARGUMENTS:

If notice late, consider:
- Employer continued to engage with claim: [evidence]
- No prejudice from late notice: [evidence]  
- Representation that time bar waived: [evidence]
- Course of dealing: [evidence]

CONCLUSION:
- Notice compliance: [COMPLIANT/PARTIAL/NON-COMPLIANT]
- Time bar defense strength: [STRONG/WEAK]
- Mitigation arguments: [list]
```

### FIDIC | conditions FIDIC | Yellow Book | Red Book
```
Analyze FIDIC contract provisions:

FIDIC FORM: [Red Book 2017 / Yellow Book 2017 / Silver Book / etc.]
CLAUSE AT ISSUE: [number]

STANDARD FIDIC POSITION:

Clause [X.X]: [title]
Text: "[quote relevant provisions]"

FIDIC GUIDE COMMENTARY:
[Reference to FIDIC guidance if available]

PARTICULAR CONDITIONS AMENDMENTS:

| Sub-clause | Standard Position | Amendment | Effect |
|------------|-------------------|-----------|--------|
| [X.X.X] | [standard text] | [amended text] | [shifts risk to...] |

KEY FIDIC MECHANISMS:

Claims (Clause 20):
- Notice: 28 days from awareness
- Particulars: 84 days (or ongoing + 28 final)
- Engineer response: 42 days
- Time bar: Yes - condition precedent

Variations (Clause 13):
- Engineer's instruction required
- Valuation per Clause 12
- No automatic EOT - must claim under Cl.20

Employer's Claims (Clause 2.5):
- Notice required (but no strict time bar)
- Particulars as soon as practicable
- Engineer determines

DAAB (Clause 21):
- Referral: 42 days from Engineer's determination
- Decision: 84 days
- Binding unless NOD in 28 days
- Arbitration after NOD

APPLICATION TO CURRENT DISPUTE:
[Specific analysis of how FIDIC applies to the issues]
```

### NEC | NEC4 | ECC | compensation event
```
Analyze NEC contract provisions:

NEC FORM: [NEC4 ECC / NEC3 ECC / PSC / etc.]
OPTION: [A/B/C/D/E/F]
SECONDARY OPTIONS: [W1/W2, X1, X2, etc.]

COMPENSATION EVENT ANALYSIS:

Claimed CE: Clause 60.1([X])
Text: "[quote CE definition]"

CE REQUIREMENTS:
| Element | Requirement | Evidence | Satisfied? |
|---------|-------------|----------|------------|
| Event matches 60.1(X) | [criteria] | [evidence] | [Y/N] |
| Not Contractor fault | [analysis] | | |
| Not in risk register | [check] | | |

NOTIFICATION:
- Clause 61.3: 8 weeks from awareness
- Notified: [date]
- Compliant: [Y/N]

QUOTATION PROCESS:
- PM instruction to quote: [date]
- Quotation due: [3 weeks = date]
- Quotation submitted: [date]
- PM response due: [2 weeks = date]

ASSESSMENT:
Method per Clause 63:
- [ ] Forecast Defined Cost + Fee
- [ ] Actual Defined Cost + Fee (if PM instructed)

Effect on prices: Clause 63.1
Effect on completion: Clause 63.5

W2 ADJUDICATION (if applicable):
- Dispute: [date]
- Referral: within [X] weeks
- Decision: [X] weeks from referral

SCHEDULE OF COST COMPONENTS:
[Reference relevant SCC items for Defined Cost]
```

### JCT | JCT 2016 | Design and Build | relevant event
```
Analyze JCT contract provisions:

JCT FORM: [SBC 2016 / DB 2016 / MW 2016 / etc.]
AMENDMENTS: [list bespoke changes]

EOT ANALYSIS (Clause 2.26-2.29):

Relevant Events (Clause 2.26):
| Relevant Event | Clause | Applicable? | Evidence |
|----------------|--------|-------------|----------|
| Variations | 2.26.1 | | |
| AI affecting critical path | 2.26.2 | | |
| Employer's failure to give access | 2.26.3 | | |
| Deferment of possession | 2.26.4 | | |
| CDM issues | 2.26.5 | | |
| Statutory undertakers | 2.26.6 | | |
| Exceptionally adverse weather | 2.26.8 | | |
| Force majeure | 2.26.14 | | |

Notice: "forthwith" + written particulars
Architect response: 12 weeks from particulars

LOSS AND EXPENSE (Clause 4.20-4.24):

Relevant Matters (Clause 4.21):
| Relevant Matter | Clause | Applicable? |
|-----------------|--------|-------------|
| Variations | 4.21.1 | |
| AI | 4.21.2 | |
| Late information | 4.21.3 | |
| Opening up (no defects found) | 4.21.4 | |
| Employer's failure | 4.21.5 | |
| CDM | 4.21.6 | |

Notice: upon becoming apparent
Ascertainment: by QS/Architect

ADJUDICATION (Clause 9.2):
- Any time during contract or 12 months after practical completion
- RICS/CIC/CIArb nominating body
- Scheme for Construction Contracts applies
```

### variation | change | instruction
```
Analyze variation entitlement:

CONTRACT: [Form]
INSTRUCTION/EVENT: [description]

VARIATION DEFINITION:

Contract definition (Clause [X]):
"[quote variation definition]"

Does claimed item constitute variation?
- [ ] Change to Works: [Y/N]
- [ ] Change to sequence/timing: [Y/N - some contracts]
- [ ] Change to access/working: [Y/N - some contracts]
- [ ] Omission: [Y/N]

INSTRUCTION REQUIREMENT:

| Contract Requirement | Compliance |
|----------------------|------------|
| Written instruction required | [Y/N] |
| Specific form required | [Y/N] |
| Authority to instruct | [Y/N] |

Oral instruction issues:
- Confirmation clause: [Clause X.X]
- Confirmation given: [Y/N, date]
- Deemed confirmed: [Y/N, basis]

CONSTRUCTIVE CHANGE:

If no written instruction:
- Scope change imposed: [evidence]
- Contractor's notice: [date, content]
- Employer's response: [actions indicating acceptance]
- Ratification: [implied/express]

VALUATION ENTITLEMENT:

| Valuation Method | Clause | Applicable |
|------------------|--------|------------|
| Contract rates | [X.X] | [if similar work] |
| Pro-rata rates | [X.X] | [if derivable] |
| Fair valuation | [X.X] | [if no applicable rates] |
| Daywork | [X.X] | [if agreed] |

TIME ENTITLEMENT:

Variation affects completion: [Y/N]
Automatic EOT: [Y/N - check contract]
Separate claim required: [Y/N]
Clause: [X.X]
```

## Contract Forms Comparison

Quick reference for common provisions:

| Issue | FIDIC 2017 | NEC4 | JCT 2016 |
|-------|------------|------|----------|
| Notice period | 28 days | 8 weeks | Forthwith |
| Time bar | Strict | Strict | Not strict |
| Variation authority | Engineer | PM | Architect |
| EOT mechanism | Cl. 8.5 + 20.1 | CE 60.1 | Cl. 2.26 |
| Cost recovery | Cl. 20.1 | CE assessment | Cl. 4.20 L&E |
| Dispute tier 1 | DAAB | Adjudication | Adjudication |
| Dispute tier 2 | Arbitration | Tribunal | Arbitration/Litigation |

## Constraints

- Quote exact contract language
- Note bespoke amendments
- Consider applicable law
- Reference relevant case law for interpretation
- Distinguish conditions precedent from warranties
- Assess time bar risks honestly

## Scripts

- `scripts/notice_tracker.py` - Track notice deadlines
- `scripts/clause_extractor.py` - Extract clauses from PDF contracts

## References

- `references/fidic-guide.md` - FIDIC 2017 quick reference
- `references/nec-guide.md` - NEC4 quick reference  
- `references/jct-guide.md` - JCT 2016 quick reference
- `references/time-bars.md` - Time bar case law
