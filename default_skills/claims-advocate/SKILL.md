---
name: claims-advocate
description: >
  Construction claims preparation and advocacy for ADR. Drafts claim submissions,
  notices, and responses. Builds persuasive narratives linking entitlement to loss.
  
  Triggers-Core: REA, request for equitable adjustment, Scott Schedule, statement of case,
  memorial, counter-memorial, witness statement, evidence bundle, heads of claim,
  particulars of claim, claim narrative, entitlement narrative.
  
  Triggers-Strong: claim submission, notice of claim, referral notice, response, defense,
  counterclaim, reply, rejoinder, rebuttal, position paper, chronology, causation,
  nexus, substantiation, contemporaneous records, burden of proof, relief sought,
  RFI log, submittal log, transmittal, correspondence register.
  
  Triggers-Weak: claim, submission, notice, document, evidence, record, correspondence,
  letter, email, meeting minutes, report, photo, exhibit, appendix, facts, issues,
  analysis, conclusion, remedy, dispute, breach, event, impact, loss,
  RFI, submittal, request for information, shop drawing, approval, review.
  
  Use when: preparing claim documentation, drafting contractual notices, writing
  entitlement narratives, structuring ADR submissions, responding to claims,
  preparing referral notices, building evidence bundles, drafting witness statements.
  
  ADR Context: Preparing adjudication referrals and responses, arbitration memorials,
  mediation position papers, expert determination submissions.
---

# Claims Advocate

Construction claims preparation and ADR documentation.

## Role in ADR

Prepares documentation for all ADR forums:
- **Adjudication**: Referral Notice, Response, Reply, Rejoinder
- **Arbitration**: Statement of Claim, Statement of Defense, Memorials
- **Mediation**: Position Paper, Settlement Proposal
- **Expert Determination**: Submission, Response

## Prompt Rewrites

### claim submission | mémoire | statement of claim
```
Prepare claim submission for [ADJUDICATION/ARBITRATION/EXPERT DETERMINATION]:

CASE REFERENCE: [reference]
CLAIMANT: [name]
RESPONDENT: [name]
CONTRACT: [reference]

CLAIM SUMMARY:
- Extension of Time: [X] days
- Additional Payment: [currency] [amount]
- Other relief: [specify]

STRUCTURE:

1. INTRODUCTION
   1.1 Parties
   1.2 Contract
   1.3 Nature of dispute
   1.4 Relief sought
   1.5 Structure of submission

2. FACTUAL BACKGROUND
   2.1 The Project
   2.2 Contract particulars
   2.3 Key dates and milestones
   2.4 Chronology of relevant events
   [Reference detailed chronology at Appendix X]

3. RELEVANT CONTRACT PROVISIONS
   3.1 [Key clause 1] - [quote and explain]
   3.2 [Key clause 2] - [quote and explain]
   3.3 [Notice/procedural clauses]

4. THE CLAIM

   4.1 DELAY CLAIM
   
   4.1.1 Delay Event 1: [Title]
   - Facts: [what happened]
   - Entitlement: [contract clause + interpretation]
   - Causation: [link to delay - reference delay expert]
   - Quantum: [X] days
   
   4.1.2 Delay Event 2: [Title]
   [same structure]
   
   4.2 COST CLAIM
   
   4.2.1 Prolongation
   - Entitlement basis: [clause]
   - Period: [X] days (per delay analysis)
   - Quantification: [currency] [amount] (per quantum expert)
   
   4.2.2 Disruption
   [same structure]
   
   4.2.3 Variations
   [same structure]

5. NOTICE COMPLIANCE
   - Event awareness: [date]
   - Notice given: [date, reference]
   - Particulars: [date, reference]
   - Ongoing updates: [list]

6. RESPONDENT'S FAILURES/BREACHES
   [Detailed narrative of what Respondent did wrong]

7. SUMMARY OF CLAIM
   | Head | Days | Amount |
   |------|------|--------|
   | EOT - Event 1 | | - |
   | EOT - Event 2 | | - |
   | Prolongation | - | |
   | Disruption | - | |
   | Variations | - | |
   | TOTAL | [X] days | [amount] |

8. RELIEF SOUGHT
   - Declaration that Claimant entitled to EOT of [X] days
   - Payment of [currency] [amount]
   - Interest from [date] at [rate]
   - Costs

APPENDICES:
A - Chronology
B - Contract extracts
C - Key correspondence
D - Notice schedule
E - Delay analysis (expert report)
F - Quantum analysis (expert report)
G - Witness statements
```

### adjudication referral | notice of adjudication | saisine
```
Prepare Adjudication Referral:

NOTICE OF ADJUDICATION

Date: [YYYY-MM-DD]

To: [Respondent name and address]
Copy: [Adjudicator Nominating Body]

CONTRACT: [reference]
PROJECT: [name]

1. NATURE OF DISPUTE

The dispute concerns [brief description].

The Referring Party seeks:
(a) A decision that it is entitled to an extension of time of [X] days
(b) A decision that it is entitled to payment of [currency] [amount]
(c) Interest
(d) [Other relief]

2. PARTIES
Referring Party: [name, address]
Responding Party: [name, address]

3. CONTRACT DETAILS
Date: [YYYY-MM-DD]
Form: [FIDIC/NEC/JCT/etc.]
Works: [description]
Contract Sum: [currency] [amount]

4. WHEN AND HOW DISPUTE AROSE

[Narrative: event → claim → rejection → crystallization]

Date dispute crystallized: [YYYY-MM-DD]
[Reference to rejection letter or failed negotiation]

5. ADJUDICATOR

The Referring Party:
[ ] Has agreed appointment of [name]
[ ] Requests nomination by [ANB name] pursuant to [contract clause]

6. PROCEDURAL MATTERS

This referral is made pursuant to:
- [Contract adjudication clause]
- [Housing Grants, Construction and Regeneration Act 1996 (as amended)]
- [Scheme for Construction Contracts]

---

REFERRAL NOTICE

[Detailed submission following claim structure above]

Required timing:
- Notice of Adjudication: Day 1
- Referral: within 7 days of Notice
- Response: [per timetable - usually 7-14 days]
- Reply: [if allowed - usually 7 days]
- Decision: 28 days from Referral (extendable by 14 days or agreement)
```

### response | défense | statement of defense
```
Prepare Response/Defense to claim:

RESPONDING TO: [Claimant's submission reference]
CLAIM AMOUNT: [currency] [amount]
CLAIM TIME: [X] days

RESPONSE STRUCTURE:

1. INTRODUCTION
   1.1 The Respondent's position in summary
   1.2 Key defenses
   1.3 Counterclaim (if any)

2. ADMISSIONS AND DENIALS

   2.1 FACTS ADMITTED:
   | Para | Claimant's statement | Admitted |
   |------|---------------------|----------|
   | [X] | [quote] | ✓ |

   2.2 FACTS DENIED:
   | Para | Claimant's statement | Respondent's position |
   |------|---------------------|----------------------|
   | [X] | [quote] | [our version] |

3. RESPONSE TO ENTITLEMENT

   3.1 Delay Claim Response
   
   Event 1: [Title]
   - Claimant's position: [summary]
   - Respondent's position: [our view]
   - Contract interpretation: [our reading]
   - Defenses: [list applicable defenses]
   
   3.2 Cost Claim Response
   [Same structure]

4. DEFENSES

   4.1 TIME BAR
   - Notice required by: [date per contract]
   - Notice given: [date]
   - Notice late by: [X] days
   - Consequence: [claim time-barred per Clause X]

   4.2 CONTRIBUTORY FACTORS
   - Claimant's own delays: [description]
   - Effect: [reduces/eliminates entitlement]

   4.3 FAILURE TO MITIGATE
   - Steps Claimant should have taken: [list]
   - Claimant's failure: [description]
   - Quantum reduction: [amount]

   4.4 CONCURRENT DELAY
   - Contractor delays: [description]
   - Effect on entitlement: [apportionment]

5. QUANTUM RESPONSE

   | Head | Claimed | Respondent's Assessment | Basis |
   |------|---------|-------------------------|-------|
   | EOT | [X] days | [Y] days | [reason] |
   | Prolongation | [amount] | [amount] | [reason] |
   | Disruption | [amount] | [amount] | [reason] |
   | TOTAL | [amount] | [amount] | |

6. COUNTERCLAIM (if applicable)

   6.1 Liquidated Damages
   - Completion date: [date]
   - Actual completion: [date]
   - Delay: [X] days
   - LAD rate: [amount/day]
   - LADs claimed: [amount]

   6.2 Defects rectification costs
   [Details]

7. CONCLUSION

   The Respondent respectfully requests that the [Adjudicator/Tribunal]:
   (a) Dismiss the claim in its entirety, or
   (b) In the alternative, assess the claim at no more than [amount]
   (c) Award the Respondent its counterclaim of [amount]
   (d) Award costs
```

### notice | notification contractuelle | avis
```
Draft contractual notice:

NOTICE TYPE:
- [ ] Notice of delay event
- [ ] Notice of claim/intention to claim
- [ ] Notice of dispute  
- [ ] Payment notice (Clause 111 / Cl.50)
- [ ] Pay less notice (Clause 111)
- [ ] Notice requiring further particulars
- [ ] Notice of withholding
- [ ] Notice of termination

CONTRACT: [reference]
GOVERNING CLAUSE: [clause number]

---

[LETTERHEAD]

[Date]

BY [DELIVERY METHOD PER CONTRACT]

[Recipient name]
[Title]
[Company]
[Address]

Dear [Name],

Re: [Contract reference]
    [Project name]
    NOTICE PURSUANT TO CLAUSE [X.X]

We write to give notice pursuant to Clause [X.X] of the above Contract.

1. THE EVENT

On or about [date], the following event occurred / we became aware of the following matter:

[Detailed description of event]

2. CONTRACTUAL BASIS

This notice is given pursuant to Clause [X.X], which provides:

"[Quote relevant clause]"

The above event constitutes [a Relevant Event / Compensation Event / delay event] under Clause [X.X] because [explanation].

3. EFFECT

As a consequence of the above, we anticipate / have experienced:

(a) Delay to the Works / Completion of [X] days [preliminary assessment]
(b) Additional cost of approximately [currency] [amount] [preliminary assessment]

4. FURTHER PARTICULARS

We will provide further particulars in accordance with Clause [X.X] within [X] days / by [date].

5. RESERVATION OF RIGHTS

This notice is given without prejudice to any other rights we may have under the Contract, at law, or in equity.

We reserve the right to supplement this notice as further information becomes available.

Yours faithfully,

[Signature]
[Name]
[Title]

cc: [Other parties as required]
    [File]
```

### Scott Schedule | tableau comparatif | schedule of items
```
Prepare Scott Schedule:

CASE: [reference]
FORMAT: [4-column / 6-column / 8-column]

---

SCOTT SCHEDULE OF DISPUTED ITEMS

| Item | Claimant's Claim | Respondent's Response | [Tribunal] |
|------|------------------|----------------------|------------|

ITEM 1: [Description]

Claimant's position:
Contract clause: [X.X]
Event: [description]
Amount claimed: [currency] [amount]
Time claimed: [X] days
Supporting documents: [references]

Respondent's position:
[Leave blank for Respondent to complete]

---

ITEM 2: [Description]

[Same format]

---

SUMMARY:

| Item | Description | Time (C) | Time (R) | Amount (C) | Amount (R) |
|------|-------------|----------|----------|------------|------------|
| 1 | | | | | |
| 2 | | | | | |
| TOTAL | | | | | |

C = Claimant's position
R = Respondent's position

---

COMPLETION INSTRUCTIONS:

1. Claimant completes columns 1-2
2. Respondent completes column 3
3. Column 4 reserved for Tribunal decision
4. Each item should be self-contained
5. Cross-reference supporting documents
6. Maintain consistent numbering
```

### chronology | chronologie | timeline
```
Prepare claim chronology:

CASE: [reference]
PERIOD: [start YYYY-MM-DD] to [end YYYY-MM-DD]
FOCUS: [delay events / variations / all]

---

CHRONOLOGY OF EVENTS

| # | Date | Event | Party | Document Ref | Significance |
|---|------|-------|-------|--------------|--------------|
| 1 | [date] | Contract executed | Both | [ref] | Baseline |
| 2 | [date] | Programme approved | Contractor | [ref] | Baseline |
| 3 | [date] | [Event description] | [party] | [letter/RFI/etc.] | [why important] |

---

DETAILED NARRATIVE:

PHASE 1: PRE-CONTRACT / TENDER
[Relevant background]

PHASE 2: EARLY WORKS
[Key events]

PHASE 3: [DELAY PERIOD / DISPUTED PERIOD]
[Detailed daily/weekly chronology of key events]

Key Event 1: [Date] - [Title]
The [Party] [action]. This is evidenced by [document reference].
The effect was [consequence].

Key Event 2: [Date] - [Title]
[Same structure]

PHASE 4: CLAIM DEVELOPMENT
[Notice given, particulars, response, crystallization]

---

DOCUMENT KEY:

| Prefix | Document Type |
|--------|---------------|
| C- | Contract documents |
| L- | Letters/Correspondence |
| M- | Meeting minutes |
| R- | RFIs |
| S- | Submittals |
| D- | Drawings |
| P- | Progress reports |
| V- | Variation instructions |
```

### witness statement | déclaration | attestation
```
Draft witness statement:

CASE: [reference]
TRIBUNAL: [Adjudicator/Arbitration/Court]
WITNESS: [name]
ROLE: [position during project]

---

IN THE MATTER OF [Case reference]

BETWEEN:

[CLAIMANT NAME]                    Claimant

- and -

[RESPONDENT NAME]                  Respondent

___________________________________

WITNESS STATEMENT OF [NAME]
___________________________________

I, [FULL NAME], of [address], [position] at [company], WILL SAY AS FOLLOWS:

1. INTRODUCTION

1.1 I make this statement in support of the [Claimant's/Respondent's] case in these proceedings.

1.2 I was employed as [position] on the [Project name] from [date] to [date]. My responsibilities included [description].

1.3 The facts stated in this witness statement are within my own knowledge unless otherwise indicated. Where matters are not within my own direct knowledge, I identify the source of my information.

2. BACKGROUND

2.1 [Personal/professional background relevant to credibility]

2.2 [Involvement with the project]

3. [TOPIC 1 - e.g., DELAY EVENT 1]

3.1 On [date], [describe what happened in first person].

3.2 I was present when [event]. I observed [specific observations].

3.3 I refer to [document reference] which is [description]. I [prepared/received/was present when] this document.

3.4 The effect of [event] was [consequence].

4. [TOPIC 2]

[Same structure]

5. STATEMENT OF TRUTH

I believe that the facts stated in this witness statement are true. I understand that proceedings for contempt of court may be brought against anyone who makes, or causes to be made, a false statement in a document verified by a statement of truth without an honest belief in its truth.

Signed: _______________________

Name: [FULL NAME]

Date: [YYYY-MM-DD]
```

## Document Standards

### Adjudication (UK)
- Referral within 7 days of Notice
- Decision within 28 days (extendable)
- Concise, focused submissions
- Key documents only

### Arbitration
- Follow tribunal directions
- IBA Rules on Evidence
- Detailed, fully reasoned
- Complete document production

### Mediation
- Commercial focus
- Without prejudice
- Settlement-oriented
- Flexible format

## Constraints

- Verify all factual assertions
- Cross-reference evidence
- Maintain consistent terminology
- Number paragraphs for reference
- Include privilege markings where appropriate
- Distinguish fact from argument
- Clear causation narrative

## Scripts

- `scripts/chronology.py` - Generate chronology from events
- `scripts/scott_schedule.py` - Scott Schedule generator
- `scripts/bundle_builder.py` - Evidence bundle organizer

## References

- `references/adjudication-procedure.md` - UK adjudication process
- `references/arbitration-procedure.md` - Arbitration procedural steps
- `references/witness-statement-guide.md` - Witness statement standards
- `references/bundle-preparation.md` - Evidence bundle requirements
