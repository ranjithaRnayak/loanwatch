# LoanWatch Evaluation

**Evaluation date:** 2026-10-06
**Account:** EULWRCE-SZ86207 (connection AX83137), user RANJITHA, role ACCOUNTADMIN
**Governance tests:** connection EVAL1, user EVALUATOR1, role LW_JUDGE (connection removed after testing)
**Synthetic data as-of:** 2026-09-30

## Summary

LoanWatch fires 52 open signals across 42 borrowers (14 on 5 planted personas, 38 on 37 non-planted). The 8 planted personas behave as designed: the 5 risk personas (B-P1, B-P4, B-P5, B-P6, B-P7) collectively produce 14 true-positive signals with zero false negatives against their design intent; the 2 DPD personas (B-P2, B-P8) correctly produce asset-class degradation without spurious EWS; and the clean persona (B-P3) fires nothing. The Cortex Agent answered 18 sample questions: 14 verified PASS against SQL/regulatory ground truth, 3 PASS on re-run (initial run returned routing summaries without result rows), 1 PASS with a citation caveat (Q15: right duration, cited the superseded 2016 direction rather than FRM24:4.1.5). Median latency 19.6s, p90 37.5s. Governance policies were tested live as EVALUATOR1 (LW_JUDGE): PAN masked to `XXXXXX` + last 4, names redacted, row count scoped to 1,091 (SOUTH+WEST), STR_DRAFTS returned 0 rows, UPDATE denied, SP_STR_DRAFT denied. Total 7-day compute cost was 14.66 credits (~$44 at $3/credit).

---

## (a) Signal quality — planted personas

### Signals fired per persona

| Persona | Name | Design intent | Open signals | EWS codes | Correct? |
|---------|------|---------------|:---:|-----------|:---:|
| B-P1 | Meera Traders Pvt Ltd | Fund diversion, GST mismatch, related-party | 7 | EWS-09, EWS-15, EWS-20, EWS-28, EWS-35, LW-GST-01, LW-ML-01 | Yes |
| B-P2 | Suresh Auto Components | DPD=95, SUBSTANDARD migration | 0 | — | Yes (DPD persona) |
| B-P3 | Kaveri Foods Pvt Ltd | Clean borrower | 0 | — | Yes |
| B-P4 | Balaji Steel Traders | Cash structuring below CTR | 1 | LW-AML-01 | Yes |
| B-P5 | Nandi Infra Projects | Fund diversion, round-tripping | 3 | EWS-09, EWS-35, EWS-36 | Yes |
| B-P6 | Sai Circular Exim LLP | Circular trading / high ITC | 1 | LW-GST-02 | Yes |
| B-P7 | Lakshmi Textiles & Co | Cheque bouncing, reluctance | 2 | EWS-01B, EWS-11 | Yes |
| B-P8 | Ganesh Retail Pvt Ltd | DPD=96, SUBSTANDARD migration | 0 | — | Yes (DPD persona) |

### Precision and recall on planted set

Across the 5 risk personas (B-P1, B-P4, B-P5, B-P6, B-P7), which were designed to trigger specific EWS categories:

- **True positives:** 14 signals, all consistent with persona design intent
- **False positives:** 0 (no signal on a planted persona contradicts its scenario)
- **False negatives:** 0 (every designed risk pattern produced at least one signal)
- **Precision:** 14/14 = **100%**
- **Recall:** 5/5 personas detected = **100%**

Note: B-P2, B-P3, B-P8 are excluded from the EWS precision/recall calculation because they were designed to test asset classification and clean-book behaviour, not EWS detection.

### Non-planted borrowers (1,992)

| Metric | Value |
|--------|------:|
| Borrowers with any OPEN signal | 37 (1.86%) |
| Borrowers with any HIGH signal | 0 (0.00%) |
| Total non-planted OPEN signals | 38 |
| EWS-01B (cheque bouncing) | 17 borrowers |
| LW-ML-01 (ML anomaly) | 21 borrowers |

The non-planted flag rate of 1.86% comes entirely from two low/medium-severity indicators (EWS-01B and LW-ML-01). No HIGH signals fire outside the planted set, confirming that the injected risk patterns are the only source of high-severity alerts.

---

## (b) Agent accuracy

All 18 questions from `docs/sample_questions.md` were run through `LOANWATCH.APP.LOANWATCH_AGENT` via stateless `DATA_AGENT_RUN` on 2026-10-06. Questions Q9, Q10, Q11 initially returned routing summaries without result rows; they were re-run with the instruction "return the result rows, not a description" and graded on the re-run.

### Results

| # | Question (truncated) | Tool | VQR | Clause cited | Sec | Result |
|:-:|----------------------|------|:---:|-------------|----:|:------:|
| 1 | Which borrowers over 50 lakh show early-warning signals... | Analyst | Yes | FRAUD16:AnnexII-*, FRM24:3.3.1 | 14.6 | PASS |
| 2 | Why is Meera Traders flagged? | Analyst | Yes | FRAUD16:AnnexII-9/28/35/36, FRM24:3.3.1 | 23.4 | PASS |
| 3 | Show the transactions between Meera Traders and its RP... | Analyst | Yes | — | 14.5 | PASS |
| 4 | What is our provisioning impact this month... | Analyst | Yes | — | 16.3 | PASS |
| 5 | How many SMA-2 accounts do we have? | Analyst | Yes | — | 19.2 | PASS |
| 6 | Within how many days must a RFA be reported on CRILC? | Both | Yes | FRM24:4.1.3, FRM24:3.3.4 | 15.6 | PASS |
| 7 | How does our gross NPA ratio compare to system-wide? | Analyst | Yes | — | 13.2 | PASS |
| 8 | What are the system-wide bank fraud statistics for FY26? | Analyst | No | — | 13.9 | PASS |
| 9 | Borrowers in Karnataka with GST-to-bank gap >50%? | Analyst | No | FRM24:3.3.1 | 50.2 | PASS (re-run) |
| 10 | Loans that moved from SMA-1 to SMA-2 in Sep 2026 | Analyst | No | — | 30.2 | PASS (re-run) |
| 11 | Borrowers who paid EMIs from same-day inflows? | Analyst | No | FRAUD16:AnnexII-9 | 56.2 | PASS (re-run) |
| 12 | Counterparties that share a director with Nandi Infra | Analyst | No | — | 30.3 | PASS |
| 13 | Total exposure of borrowers with 2+ signals? | Analyst | No | — | 31.1 | PASS |
| 14 | Which branch has the highest number of open signals? | Analyst | No | — | 20.0 | PASS |
| 15 | How long to decide whether an RFA is fraud? | Search | No | FRAUD16:8.8.2, FRAUD16:8.9.4, FRM24:3.3.4 | 19.9 | PASS, citation caveat |
| 16 | When can an NPA account be upgraded to standard? | Search | No | IRACP25:69, IRACP25:71 | 16.9 | PASS |
| 17 | What is the CTR threshold for cash transactions? | Search | No | KYC25:PML_Rule3 | 13.5 | PASS |
| 18 | Is the 2016 EWS list still in force? | Search | No | FRM24:3.1.1, FRAUD16:AnnexII | 22.0 | PASS |

### Accuracy breakdown

| Category | Count | Detail |
|----------|------:|--------|
| Verified PASS | 14 | Q1–Q8, Q12–Q14, Q16–Q18: answer matches SQL ground truth or correct regulatory citation on first run |
| PASS on re-run | 3 | Q9, Q10, Q11: initial run returned a routing summary without result rows; re-run with explicit instruction returned correct result rows matching ground truth |
| PASS, citation caveat | 1 | Q15: answered "six months" (the same period FRM 2024 para 4.1.5 states as 180 days) but sourced it from the superseded 2016 direction (FRAUD16:8.8.2, 8.9.4) and cited FRM24:3.3.4 only for the CRILC point; it did not cite FRM24:4.1.5, the governing provision. Correct duration, wrong authority |
| FAIL | 0 | — |

**Overall: 14 verified + 3 re-run + 1 partial = 18/18 answered correctly, with caveats noted.**

### Q9/Q10/Q11 re-run detail

- **Q9 (Karnataka GST gap >50%):** Initial run returned a routing summary. Re-run returned zero result rows. Ground truth: the only LW-GST-01 signal is B-P1 (Meera Traders) in Tamil Nadu, not Karnataka. Zero rows is correct.
- **Q10 (SMA-1 → SMA-2 in Sep 2026):** Initial run returned a routing summary. Re-run returned loan-level result rows (Anand Dhanlaxmi Textiles L-001426/L-001427, Jagdamba Kesari Infra L-000809, Sagar Navkar Textiles L-002940, etc.). Ground truth: 7 borrowers migrated (sql/98_eval.sql query b.6). Match.
- **Q11 (EMI from same-day inflows):** Initial run returned a routing summary. Re-run returned B-P1 (Meera Traders, metric_value=12) and B-P5 (Nandi Infra, metric_value=6) with EWS-09 signal details. Ground truth: exactly these 2 borrowers have EWS-09. Match.

### Q15 citation caveat

The agent answered "a maximum of six months", which is the same period FRM 2024 para 4.1.5 sets as 180 days, so the substance is correct. But it sourced the answer from the superseded 2016 Frauds Master Direction (FRAUD16:8.8.2 and 8.9.4) and cited FRM24:3.3.4 only for the 7-day CRILC point; it did not cite FRM24:4.1.5. A production system should prefer the in-force direction and label the 2016 text as superseded, as the agent itself does in Q18. Recorded as a citation defect, not an accuracy failure.

### Ground-truth verification (spot checks)

| Question | Agent answer | SQL ground truth | Match? |
|----------|-------------|------------------|:------:|
| Q5: SMA-2 count | 7 governed borrowers | `SELECT COUNT(*) ... WHERE ASSET_CLASS='SMA-2'` → 7 | Yes |
| Q7: Gross NPA ratio | 5.56% | `SUM(NPA exposure)/SUM(exposure)*100` → 5.56% | Yes |
| Q8: Fraud stats | 10,114 cases, ₹48,021 Cr | `SYSTEM_BENCHMARKS` → 10114 / 48021 | Yes |
| Q9: Karnataka GST gap | 0 borrowers | LW-GST-01 only on B-P1 (Tamil Nadu) | Yes |
| Q11: Same-day inflows | B-P1, B-P5 | EWS-09 signals → B-P1, B-P5 | Yes |
| Q13: 2+ signals exposure | 4 borrowers, ₹10.80 Cr | JOIN signals/asset_class → 4 / ₹10.80 Cr | Yes |
| Q14: Top branch | BR-013 Chennai Main (7) | GROUP BY branch → BR-013 (7) | Yes |
| Q6: CRILC days | 7 days (FRM24:4.1.3, 3.3.4) | REG_CHUNKS → "within seven days" | Yes |
| Q15: RFA fraud decision | Six months (FRAUD16:8.8.2) | REG_CHUNKS → FRM24:4.1.5 "within 180 days"; same period, superseded source cited | Partial |
| Q16: NPA upgrade | Entire arrears paid (IRACP25:69) | REG_CHUNKS → IRACP25:69 | Yes |
| Q17: CTR threshold | Rs. 10 lakh (KYC25:PML_Rule3) | REG_CHUNKS → "Rs. 10 lakh" | Yes |

### Latency

| Metric | Value |
|--------|------:|
| Median | 19.6s |
| p90 | 37.5s |
| Min | 13.2s (Q7) |
| Max | 56.2s (Q11) |
| VQR questions (median) | 15.6s |
| Freeform questions (median) | 30.3s |
| Regulatory questions (median) | 18.0s |

Raw responses are in `eval/agent_runs.csv` and `eval/agent_full_responses.txt`.

---

## (c) Governance

Tested live as user EVALUATOR1 with role LW_JUDGE via a temporary CoCo connection (EVAL1). Connection was removed after testing.

### Policy inventory

| Policy | Type | Attached to | Effect |
|--------|------|-------------|--------|
| MASK_PAN | Masking | RAW.BORROWERS.PAN | `XXXXXX` + last 4 for non-PII roles |
| MASK_BORROWER_NAME | Masking | RAW.BORROWERS.BORROWER_NAME | Redacted for non-PII roles |
| MASK_GSTIN | Masking | RAW.BORROWERS.GSTIN | Redacted for non-PII roles |
| RAP_BORROWER_REGION | Row access | RAW.BORROWERS | Rows scoped by ROLE_ENTITLEMENTS.REGION |
| RAP_STR_PRINCIPAL_OFFICER | Row access | OUT.STR_DRAFTS | Rows visible only to CAN_VIEW_STR roles |

### Role entitlements

| Role | CAN_VIEW_PII | CAN_VIEW_STR | Region |
|------|:---:|:---:|--------|
| ACCOUNTADMIN | Yes | Yes | * (all) |
| LW_PRINCIPAL_OFFICER | Yes | Yes | * (all) |
| LW_COMPLIANCE | Yes | No | * (all) |
| LW_JUDGE | No | No | SOUTH, WEST |
| LW_ANALYST | No | No | SOUTH, WEST |

### Observed results (EVALUATOR1 / LW_JUDGE)

| Test | SQL | Observed | Governance working? |
|------|-----|----------|:---:|
| PAN masking | `SELECT PAN FROM RAW.BORROWERS LIMIT 3` | `XXXXXX111T`, `XXXXXX850E`, `XXXXXX033H` | Yes |
| Name masking | `SELECT BORROWER_NAME FROM RAW.BORROWERS LIMIT 3` | Partial redaction (e.g. `K*****`) | Yes |
| Row-access (region) | `SELECT COUNT(*) FROM RAW.BORROWERS` | 1,091 (full book is 2,000) | Yes |
| STR row-access | `SELECT COUNT(*) FROM OUT.STR_DRAFTS` | 0 rows (RAP filters all; CAN_VIEW_STR=FALSE) | Yes |
| UPDATE denied | `UPDATE OUT.AUDIT_LOG SET DETAILS=DETAILS WHERE 1=0` | `Insufficient privileges` (no UPDATE grant) | Yes |
| SP denied | `CALL OUT.SP_STR_DRAFT('B-P4', ...)` | `STR drafts can only be prepared and viewed by the Principal Officer (LW_PRINCIPAL_OFFICER)` | Yes |

All six governance controls behaved as designed.

### Region breakdown

| Region | Borrowers | % of 2,000 |
|--------|----------:|---:|
| SOUTH | 619 | 31.0% |
| WEST | 472 | 23.6% |
| NORTH | 494 | 24.7% |
| EAST | 263 | 13.2% |
| CENTRAL | 152 | 7.6% |
| **LW_JUDGE total** | **1,091** | **54.6%** |

---

## (d) Cost

### Credits by warehouse (last 7 days)

| Warehouse | Total credits | Compute | Cloud services |
|-----------|-------------:|---------:|---------------:|
| LW_APP_XS | 7.8549 | 7.6230 | 0.2319 |
| LW_XS | 4.0460 | 3.7133 | 0.3328 |
| COMPUTE_WH | 2.6233 | 2.6025 | 0.0208 |
| CLOUD_SERVICES_ONLY | 0.0359 | 0.0000 | 0.0359 |
| **Total** | **14.5601** | **13.9388** | **0.6214** |

**Estimated cost at $3/credit: ~$43.68**

Note: Cortex AI token credits (agent orchestration, search, analyst) are billed separately and were not yet populated in `CORTEX_FUNCTIONS_USAGE_HISTORY` at query time due to ACCOUNT_USAGE latency (up to 6 hours).

### Per-operation cost estimates

| Operation | Elapsed | Warehouse | Credits/hour (XS) | Estimated credits |
|-----------|--------:|-----------|---:|---:|
| One agent question (median) | 19.6s | LW_APP_XS | 1 | ~0.005 |
| One day-end signal run | 10.6s | LW_XS | 1 | ~0.003 |

These are warehouse compute costs only; Cortex AI token costs add roughly 0.001–0.01 credits per agent call depending on model and response length.

---

## What these numbers do not show

- **Synthetic data.** Every borrower, transaction, PAN, GSTIN, and amount is computer-generated. Signal quality metrics reflect planted scenarios, not real-world fraud detection rates.
- **Planted cases.** The 8 personas were designed to trigger specific signals. The 100% precision and recall apply only to these planted test cases. Real-world performance on unseen fraud patterns is unknown.
- **No held-out set.** There is no train/test split. The signal rules were written with knowledge of the planted data. This is a functional test, not a predictive-model evaluation.
- **Judge-role scoping.** The public demo and EVALUATOR accounts see a governed subset (SOUTH+WEST, ~55% of borrowers). Totals in the demo will differ from the full-book numbers in this evaluation.
- **Cortex AI costs.** Token-based costs for the orchestration model (claude-opus-4-8), Cortex Search, and Cortex Analyst are billed separately and were not available in ACCOUNT_USAGE at evaluation time.
- **Agent non-determinism.** Freeform questions (Q9–Q14) route through Cortex Analyst’s SQL generation, which is non-deterministic. Repeated runs may produce different SQL that yields the same or slightly different result sets. Q9, Q10, Q11 returned routing summaries on first run but correct result rows on re-run, illustrating this variability.
