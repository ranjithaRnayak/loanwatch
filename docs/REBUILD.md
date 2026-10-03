# LoanWatch — Rebuild Guide

Rebuild the entire LoanWatch system in a fresh Snowflake account from this repo.
Estimated wall-clock time: **under 1 hour** (most time is spent on AI_PARSE_DOCUMENT and the agent tests).

## Prerequisites

- A Snowflake account with Cortex AI features enabled (cross-region inference ON).
- ACCOUNTADMIN or a role with CREATE DATABASE, CREATE WAREHOUSE, CREATE ROLE privileges.
- The CoCo CLI (Cortex Code) or Snowsight SQL worksheet.
- The 4 regulatory PDFs in `docs/regs/`.

---

## Step 0 — Account setup (`00_setup.sql`)

> This script does not exist in the repo. Run these commands manually or save as `sql/00_setup.sql`.

```sql
CREATE DATABASE IF NOT EXISTS LOANWATCH;

CREATE SCHEMA IF NOT EXISTS LOANWATCH.RAW   COMMENT = 'Raw ingestion from three simulated source systems';
CREATE SCHEMA IF NOT EXISTS LOANWATCH.CORE  COMMENT = 'Governed dynamic tables: reconciled DPD, asset class, borrower metrics';
CREATE SCHEMA IF NOT EXISTS LOANWATCH.REF   COMMENT = 'Reference tables, regulatory documents, Cortex Search service';
CREATE SCHEMA IF NOT EXISTS LOANWATCH.OUT   COMMENT = 'Signals, findings, reports, STR drafts, audit log';
CREATE SCHEMA IF NOT EXISTS LOANWATCH.APP   COMMENT = 'Semantic view, Cortex Agent, Streamlit app';
CREATE SCHEMA IF NOT EXISTS LOANWATCH.GOV   COMMENT = 'LoanWatch governance: tags, policies, entitlements';

CREATE WAREHOUSE IF NOT EXISTS LW_XS      WAREHOUSE_SIZE = 'XSMALL' AUTO_SUSPEND = 60 AUTO_RESUME = TRUE;
CREATE WAREHOUSE IF NOT EXISTS LW_APP_XS   WAREHOUSE_SIZE = 'XSMALL' AUTO_SUSPEND = 60 AUTO_RESUME = TRUE;
```

**Expected:** 6 schemas, 2 warehouses.

---

## Steps 10–15 — Synthetic data load

> The 21 RAW tables and 10+ REF tables were generated via CoCo CLI prompts. The DDL and INSERT scripts are embedded in the CoCo session history (see PROMPTS.md, Prompt 1 preamble). To rebuild, replay the CoCo session or load from a Snowflake share / export.

### Expected row counts — RAW (21 tables)

| Table | Rows |
|-------|------|
| BORROWERS | 2,000 |
| LOAN_ACCOUNTS | 3,003 |
| BRANCHES | 50 |
| DIRECTORS | 9,000 |
| BORROWER_DIRECTORS | 3,050 |
| COUNTERPARTIES | 6,004 |
| COUNTERPARTY_DIRECTORS | 7,066 |
| RELATED_PARTY_SOURCES | 441 |
| CBS_ACCOUNT_SNAPSHOT | 36,036 |
| LMS_ACCOUNT_SNAPSHOT | 36,036 |
| REPAYMENT_SCHEDULE | 72,072 |
| EMI_PAYMENTS | 71,439 |
| DRAWDOWNS | 25,957 |
| BANK_TRANSACTIONS | 311,552 |
| CHEQUE_BOUNCES | 3,006 |
| STOCK_STATEMENTS | 7,984 |
| INSPECTIONS | 4,001 |
| COLLECTIONS_CASES | 1,405 |
| GST_FILINGS | 96,000 |
| GST_B2B_INVOICES | 192,016 |
| CONFLICT_INJECTION_LOG | 460 |

### Expected row counts — REF (10 tables)

| Table | Rows |
|-------|------|
| EWS_INDICATORS | 47 |
| IRAC_RULES | 13 |
| PROVISION_RATES | 12 |
| DEFINITIONS_GLOSSARY | 23 |
| LW_SETTINGS | 5 |
| PROMPT_TEMPLATES | 4 |
| REG_DOCS | 8 |
| REG_PAGES | 125 |
| SYSTEM_BENCHMARKS | 8 |
| REG_CHUNKS | 641 |

### Expected — CORE (4 dynamic tables + views)

| Object | Type | Rows |
|--------|------|------|
| LOAN_DPD_DAILY | Dynamic table | ~1,096,000 |
| ASSET_CLASS_DAILY | Dynamic table | ~730,000 |
| BORROWER_MONTHLY | Dynamic table | ~48,000 |
| RELATED_PARTY_EDGES | Dynamic table | ~2,600 |
| PROVISION_MONTHLY | View | ~48,000 |
| EWS_ALL (+ 13 individual EWS views) | Views | varies |
| ML_BORROWER_SERIES | View | varies |
| CALENDAR | Table | 365 |
| RUN_CONTEXT | Table | 1 |

### Expected — GOV

| Object | Type | Count |
|--------|------|-------|
| Masking policies | Policy | 7 (PAN, GSTIN, account no, DIN, person name, borrower name, DOB) |
| Row access policies | Policy | 2 (borrower region, STR principal officer) |
| BORROWER_REGION | Table | 2,000 |
| ROLE_ENTITLEMENTS | Table | 7 |

### Expected — OUT

| Table | Rows (after signals run) |
|-------|------|
| SIGNALS | 52 |
| FINDINGS | 0 (populated by SP_CREATE_FINDING) |
| RFA_NOTES | 0 (populated by SP_RFA_NOTE) |
| REPORTS | 0 (populated by SP_PROVISIONING_RETURN) |
| STR_DRAFTS | 0 (populated by SP_STR_DRAFT) |
| AUDIT_LOG | grows with each action |
| ML_ANOMALY_SCORES | ~12,000 |

---

## Step 16–21 — Regulatory search pipeline

```bash
# 1. Upload PDFs to stage
PUT 'file://docs/regs/IRACP2025.pdf' @LOANWATCH.REF.REG_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT 'file://docs/regs/FRM2024.pdf'   @LOANWATCH.REF.REG_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT 'file://docs/regs/FRAUD2016.pdf' @LOANWATCH.REF.REG_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT 'file://docs/regs/FIUIND.pdf'    @LOANWATCH.REF.REG_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
ALTER STAGE LOANWATCH.REF.REG_STAGE REFRESH;

# 2. Run the parse + search pipeline
-- Execute sql/20_reg_search.sql
```

**Expected:** REG_CHUNKS: ~641 rows. REG_SEARCH service: ACTIVE.

---

## Step 30 — Cortex Agent + Semantic View

```bash
# 1. Create the semantic view (DDL is in the CoCo session; 16 tables, 7 VQRs)
# 2. Create the agent
-- Execute sql/30_agent.sql
```

**Expected:** Agent LOANWATCH.APP.LOANWATCH_AGENT with 2 tools (Analyst + Search).

---

## Step 40 — Streamlit app

```bash
-- Execute sql/40_streamlit.sql
```

**Expected:** LOANWATCH.APP.LOANWATCH_UI running on LW_APP_XS with 6 pages.

---

## Step 50 — Judge access

```bash
-- Execute sql/50_judge_access.sql
-- Then create users with passwords (not stored in the script):
CREATE USER EVALUATOR1 PASSWORD = '<generate>' EMAIL = 'evaluator@hack2skill.com'
  DEFAULT_ROLE = LW_JUDGE DEFAULT_WAREHOUSE = LW_APP_XS MUST_CHANGE_PASSWORD = FALSE;
CREATE USER EVALUATOR2 PASSWORD = '<generate>' EMAIL = 'hack2skillevaluator@gmail.com'
  DEFAULT_ROLE = LW_JUDGE DEFAULT_WAREHOUSE = LW_APP_XS MUST_CHANGE_PASSWORD = FALSE;
GRANT ROLE LW_JUDGE TO USER EVALUATOR1;
GRANT ROLE LW_JUDGE TO USER EVALUATOR2;
```

---

## Step 99 — End-to-end validation

```bash
-- Execute sql/99_e2e.sql
```

**Expected:** 13 checks, all PASS:
- 8 agent smoke-tests (each demo question returns content)
- B-P1 has exactly 7 OPEN signals including EWS-09 and LW-GST-01
- B-P2 appears in PROVISION_MONTHLY as SMA-2 → SUBSTANDARD
- REG_CHUNKS has FRM24 para 4.1.3 containing "CRILC"
