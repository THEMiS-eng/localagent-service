---
name: quantum-expert
description: >
  Quantum and damages expert for ADR proceedings. Provides independent cost analysis,
  valuation, and damages quantification for mediation, adjudication, arbitration.
  
  Triggers-Core: Eichleay, Hudson, Emden, measured mile, total cost method,
  head office overhead, HO overhead, extended preliminaries, thickening,
  loss and expense, quantum expert, damages quantification.
  
  Triggers-Strong: quantum, damages, prolongation costs, disruption costs, productivity loss,
  inefficiency, acceleration costs, variation valuation, loss of profit, wasted costs,
  abortive work, financing costs, compound interest, site overhead, preliminaries,
  time-related costs, direct costs, indirect costs, actual cost, estimated cost.
  
  Triggers-Weak: cost, price, rate, valuation, payment, invoice, claim, assessment,
  budget, estimate, tender, margin, overhead, profit, labour, material, plant,
  subcontractor, bill of quantities, BOQ, schedule of rates, daywork.
  
  Use when: preparing quantum expert reports, valuing damages for disputes, providing
  independent cost opinions for ADR, reviewing opposing quantum claims, establishing
  causation between breach and loss, calculating prolongation/disruption costs.
  
  ADR Context: Expert witness in arbitration, quantum advisor in adjudication,
  technical advisor in mediation, expert determiner for valuation disputes.
---

# Quantum Expert

Independent damages quantification for ADR proceedings.

## Expert Role

As quantum expert in ADR:
- **Arbitration**: Party-appointed or tribunal-appointed expert on damages
- **Adjudication**: Preparing/responding to quantum elements of referral
- **Mediation**: Reality-testing quantum positions, settlement range analysis
- **Expert Determination**: Final determination on valuation/quantum disputes

## Prompt Rewrites

### quantum expert report | damages opinion | rapport quantum
```
Prepare Quantum Expert Report for [ARBITRATION/ADJUDICATION]:

CASE REFERENCE: [tribunal reference]
INSTRUCTING PARTY: [Claimant/Respondent]
CLAIM VALUE: [currency] [amount]

1. INSTRUCTIONS AND SCOPE
   - Issues to address
   - Limitation on scope (if any)
   - Documents reviewed

2. EXPERT QUALIFICATIONS
   - QS/cost expertise
   - Relevant experience
   - Prior expert appointments

3. EXECUTIVE SUMMARY
   - Claim summary by head of claim
   - Our assessed value by head
   - Key variances explained

4. METHODOLOGY
   - Valuation approach per head of claim
   - Standards applied (RICS, AACE)
   - Assumptions made

5. HEADS OF CLAIM ANALYSIS

   5.1 PROLONGATION
   - Period: [X] days
   - Methodology: [actual/planned pro-rata]
   - Quantification: [see detailed section]
   
   5.2 DISRUPTION
   - Affected scope: [description]
   - Methodology: [measured mile/studies]
   - Quantification: [see detailed section]
   
   5.3 VARIATIONS
   - Number: [X] variations
   - Valuation basis: [contract rates/fair rates]
   - Quantification: [see detailed section]
   
   5.4 OTHER HEADS
   - [as applicable]

6. DETAILED CALCULATIONS
   [Per head of claim with workings]

7. SUMMARY
   | Head of Claim | Claimed | Assessed | Variance |
   |---------------|---------|----------|----------|
   | Prolongation | | | |
   | Disruption | | | |
   | Variations | | | |
   | Other | | | |
   | TOTAL | | | |

8. OPINIONS
   - Numbered opinions with reasoning
   - Qualifications and caveats

9. EXPERT DECLARATION

APPENDICES:
- A: CV
- B: Documents reviewed  
- C: Detailed calculations
- D: Supporting schedules
```

### prolongation | extended preliminaries | coûts de prolongation
```
Calculate prolongation costs for ADR:

ENTITLEMENT PERIOD: [X] days (from delay expert)
PERIOD DATES: [start YYYY-MM-DD] to [end YYYY-MM-DD]

METHODOLOGY SELECTION:
- [ ] Actual cost (preferred - contemporaneous records available)
- [ ] Planned cost pro-rata (baseline preliminaries budget)
- [ ] Assessment (where records incomplete)

PRELIMINARIES ANALYSIS:

TIME-RELATED COSTS (recoverable during prolongation):
| Item | Monthly Rate | Source | Extended Period | Amount |
|------|--------------|--------|-----------------|--------|
| Site management | | [payroll/budget] | [X] months | |
| Site staff | | | | |
| Site accommodation | | | | |
| Temporary facilities | | | | |
| Plant standing | | | | |
| Small tools/consumables | | | | |
| Utilities | | | | |
| Security | | | | |
| Insurance | | | | |
| Bonds/guarantees | | | | |

FIXED COSTS (one-time, not time-related):
[Identify and exclude from prolongation]

VERIFICATION:
- Costs incurred during delay period: [Y/N]
- Causation established: [Y/N]
- Not recovered elsewhere: [Y/N]
- Mitigation considered: [Y/N]

ASSESSED PROLONGATION: [currency] [amount]

ALTERNATIVE CALCULATION (if disputed):
| Scenario | Period | Amount | Basis |
|----------|--------|--------|-------|
| Claimant's case | [X] days | | |
| Respondent's case | [X] days | | |
| Our assessment | [X] days | | |
```

### head office overhead | HO overhead | Eichleay | Hudson | Emden
```
Calculate head office overhead for ADR:

FORMULA SELECTION:
- [ ] Eichleay (US Federal - requires standby)
- [ ] Hudson (UK - uses tender %)
- [ ] Emden (UK - uses audited accounts %)
- [ ] Actual absorption analysis

EICHLEAY FORMULA:
Contract billings: [currency] [amount]
Contractor's total billings (same period): [currency] [amount]
Contractor's HO overhead (same period): [currency] [amount]
Original contract days: [X]
Delay days: [X]

Step 1: Allocable % = Contract billings / Total billings = [X]%
Step 2: Allocable overhead = [X]% × HO overhead = [amount]
Step 3: Daily rate = Allocable overhead / Contract days = [amount/day]
Step 4: HO claim = Daily rate × Delay days = [amount]

EICHLEAY PREREQUISITES:
- [ ] Contractor on standby during delay
- [ ] Unable to take replacement work
- [ ] Uncertainty about resumption date
- [ ] HO overhead continued unabated

HUDSON FORMULA (alternative):
HO % from tender: [X]%
Contract sum: [currency] [amount]
Original period: [X] weeks
Delay period: [X] weeks

HO claim = (HO% × Contract sum × Delay period) / Original period = [amount]

EMDEN FORMULA (alternative):
HO % from audited accounts: [X]%
[Same calculation as Hudson]

RECOMMENDATION:
[Which formula appropriate and why - with case law support if arbitration]
```

### disruption | productivity loss | inefficiency | perturbation
```
Calculate disruption damages for ADR:

AFFECTED WORK: [description]
DISRUPTED PERIOD: [start YYYY-MM-DD] to [end YYYY-MM-DD]
DISRUPTING EVENTS: [reference to liability findings]

METHODOLOGY:
- [ ] Measured Mile (preferred - project data available)
- [ ] Earned Value Analysis
- [ ] Industry Studies (MCAA, Leonard)
- [ ] System Dynamics Modeling
- [ ] Total Cost (last resort - strict requirements)

MEASURED MILE ANALYSIS:

Baseline Period (undisrupted):
| Trade | Location | Hours | Output | Productivity |
|-------|----------|-------|--------|--------------|
| | | | | [unit/hr] |

Impacted Period:
| Trade | Location | Hours | Output | Productivity | Loss % |
|-------|----------|-------|--------|--------------|--------|
| | | | | [unit/hr] | |

Productivity Loss: [X]% 

Causation Factors:
| Factor | Impact Assessment | Evidence |
|--------|-------------------|----------|
| Out-of-sequence work | | [doc ref] |
| Trade stacking | | |
| Restricted access | | |
| Design changes | | |
| Stop-start | | |

QUANTUM CALCULATION:
Impacted hours: [X]
Productivity loss: [X]%
Lost hours: [X]
Blended labor rate: [currency/hr]
Disruption damages: [currency] [amount]

TOTAL COST METHOD (if used - strict test):
- Actual cost: [amount]
- Bid/estimated cost: [amount]
- Difference: [amount]
- Contractor fault eliminated: [evidence]
- No other cause: [evidence]
- Bid was reasonable: [evidence]
```

### variation valuation | change order | VO
```
Value variations for ADR:

VARIATIONS IN DISPUTE:
| VO No | Description | Claimant Value | Respondent Value | Difference |
|-------|-------------|----------------|------------------|------------|
| | | | | |

VALUATION METHODOLOGY PER CONTRACT:
Clause [X]: [quote relevant valuation clause]

VALUATION HIERARCHY:
1. Contract rates (where work similar)
2. Pro-rata/star rates (derived from contract rates)
3. Fair rates (where no applicable rates)
4. Daywork (as last resort)

DETAILED VALUATION [per VO]:

VO [X]: [Description]

Contract Rate Application:
| Item | BOQ Ref | BOQ Rate | Qty | Amount |
|------|---------|----------|-----|--------|
| | | | | |

OR Fair Rate Buildup:
| Component | Qty | Unit | Rate | Source | Amount |
|-----------|-----|------|------|--------|--------|
| Labor | | hrs | | [wage agreement] | |
| Materials | | | | [invoices/quotes] | |
| Plant | | hrs | | [BCIS/internal] | |
| Subtotal | | | | | |
| OH&P [X]% | | | | [contract/fair] | |
| TOTAL | | | | | |

TIME IMPLICATION: [X] days [separate/included]
```

### loss of profit | perte de bénéfice | lost profit
```
Calculate loss of profit for ADR:

CLAIM BASIS:
- [ ] Lost contract profit (termination/partial termination)
- [ ] Lost opportunity (prevented from other work)
- [ ] Reduced profit margin (cost overrun from breach)

LOST CONTRACT PROFIT:

Original contract value: [currency] [amount]
Work completed before termination: [currency] [amount]
Work remaining (terminated): [currency] [amount]
Profit margin on remaining: [X]%
Lost profit: [currency] [amount]

Proof of profit margin:
- Tender buildup: [evidence]
- Similar project margins: [evidence]
- Actual margin achieved to termination: [evidence]

MITIGATION:
- Attempts to redeploy resources: [evidence]
- Alternative work secured: [value]
- Mitigation credit: [amount]

NET LOSS OF PROFIT: [currency] [amount]

FORESEEABILITY:
[Was loss of profit foreseeable at contract formation?]

REMOTENESS:
[Is claimed loss too remote?]
```

### quantum review | rebuttal quantum | contre-expertise coûts
```
Review opposing quantum expert report:

OPPOSING EXPERT: [name]
CLAIMED AMOUNT: [currency] [amount]

SUMMARY COMPARISON:
| Head of Claim | Claimed | Our Assessment | Variance | Key Issue |
|---------------|---------|----------------|----------|-----------|
| Prolongation | | | | |
| Disruption | | | | |
| HO Overhead | | | | |
| Variations | | | | |
| Other | | | | |
| TOTAL | | | | |

DETAILED CRITIQUE:

1. PROLONGATION
   Claimed: [amount] for [X] days
   Issues identified:
   - [ ] Period disputed (delay expert issue)
   - [ ] Rates unsupported
   - [ ] Actual costs not evidenced
   - [ ] Double recovery with other heads
   Our assessment: [amount]

2. DISRUPTION  
   Claimed: [amount]
   Issues identified:
   - [ ] Methodology inappropriate
   - [ ] Measured mile selection flawed
   - [ ] Causation not established
   - [ ] Contractor inefficiency not excluded
   Our assessment: [amount]

3. [Continue for each head]

UNSUPPORTED/UNSUBSTANTIATED COSTS:
| Item | Amount Claimed | Issue | Deduction |
|------|----------------|-------|-----------|
| | | No backup | |
| | | Not incurred in period | |
| | | Recovered elsewhere | |
```

## ADR-Specific Requirements

### For Adjudication
- Focus on key quantum issues
- Summary calculations acceptable
- Reserve detailed analysis
- Address crystallized sum

### For Arbitration  
- Full supporting documentation
- Respond to quantum directions
- Prepare for cross-examination
- Joint expert statement on quantum

### For Mediation
- Settlement range analysis
- Risk-adjusted valuations
- Commercial reality testing

## Constraints

- Currency clearly stated
- VAT treatment specified
- Interest calculations separate
- Mitigation addressed
- Avoid double recovery
- Causation established per head
- Records-based where possible
- Assumptions clearly stated

## Scripts

- `scripts/eichleay.py` - HO overhead formulas
- `scripts/prolongation.py` - Preliminaries calculator
- `scripts/measured_mile.py` - Productivity analysis
- `scripts/variation_valuer.py` - VO valuation

## References

- `references/quantum-methods.md` - Valuation methodologies
- `references/ho-overhead.md` - HO overhead case law
- `references/disruption-analysis.md` - Disruption quantification
- `references/proof-of-loss.md` - Evidential requirements
