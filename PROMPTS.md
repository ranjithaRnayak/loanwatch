# PROMPTS.md — LoanWatch Prompt Log

## Prompt 1: Regulatory Document Search Pipeline

**Prompt:**
Parse every PDF in @LOANWATCH.REF.REG_STAGE with AI_PARSE_DOCUMENT in LAYOUT mode. Split the output into paragraph chunks and store them in LOANWATCH.REF.REG_CHUNKS with columns DOC_ID (IRACP2025, FRM2024, FRAUD2016 or FIUIND, derived from the file name), PARA_REF (the paragraph number found in the text, else the page number), PAGE, CHUNK_TEXT. Create Cortex Search service LOANWATCH.REF.REG_SEARCH on CHUNK_TEXT with DOC_ID and PARA_REF as attributes, warehouse LW_XS, target lag 1 day. Save all SQL as sql/20_reg_search.sql. Test with the query "within how many days must a Red Flagged Account be reported on CRILC" and show the top 3 results with DOC_ID and PARA_REF.

**Outcome:**
- Parsed 4 regulatory PDFs (IRACP2025, FRM2024, FRAUD2016, FIUIND) using `AI_PARSE_DOCUMENT` in LAYOUT mode with `page_split: true`.
- Split markdown output on double-newline boundaries into 4,338 paragraph chunks stored in `LOANWATCH.REF.REG_CHUNKS`.
- `PARA_REF` extracted via regex from leading paragraph numbers (e.g. `4.1.5`, `3.3.4`); falls back to page number.
- Created Cortex Search service `LOANWATCH.REF.REG_SEARCH` with 1-day target lag on warehouse `LW_XS`.
- SQL saved to `sql/20_reg_search.sql`.

**Test query:** "within how many days must a Red Flagged Account be reported on CRILC"

| Rank | DOC_ID  | PARA_REF | Key excerpt |
|------|---------|----------|-------------|
| 1    | FRM2024 | 4.1.5    | "...entire process...shall ordinarily be completed within **180 days** from the date of first reporting..." |
| 2    | FRM2024 | 3.3.4    | "...once red flagged, shall be reported to the Reserve Bank **within seven days**..." |
| 3    | FRM2024 | 4.1.3    | "...shall report the status...on CRILC platform immediately (**not later than seven days**)..." |

## Prompt 2: Cortex Agent Creation

**Prompt:**
Create Cortex Agent LOANWATCH.APP.LOANWATCH_AGENT with Cortex Analyst over LOANWATCH.APP.LOANWATCH_SV, Cortex Search over LOANWATCH.REF.REG_SEARCH, and four stored procedures (SP_CREATE_FINDING, SP_RFA_NOTE, SP_PROVISIONING_RETURN, SP_STR_DRAFT). Agent instructions: show evidence and CLAUSE_REF, cite RBI document and paragraph, only draft reports, all data synthetic. Test with 8 questions.

**Outcome:**
- Created `LOANWATCH.APP.LOANWATCH_AGENT` with 2 tools: Cortex Analyst (semantic view) + Cortex Search (reg docs).
- Custom tools (stored procedures) could not be attached via YAML `generic` tool_resources — Snowflake returned `"generic tool resources is nil"` and `"empty type/execution environment"` errors across multiple spec formats. Procedures remain available for manual attachment via Snowsight UI.
- SQL saved to `sql/30_agent.sql`.

**Test results (4 of 8 questions tested with Analyst + Search):**

| # | Question | Tool used | Brief answer |
|---|----------|-----------|--------------|
| 1 | Which borrowers over 50 lakh show EWS signals this quarter? | Analyst | **38 borrowers**. Top: Meera Traders (7 signals, ₹4.2Cr), Nandi Infra (3 signals, ₹4.0Cr). All with CLAUSE_REFs. |
| 2 | Why is Meera Traders flagged? | Analyst | **7 open signals** — 5 HIGH (EWS-09 evergreening via Axis Bank, EWS-15 turnover collapse -52.6%, EWS-20/35 ₹1.96Cr diverted to Meera Agencies via shared director D-0042, LW-GST-01 bank/GST gap 223%), 2 MEDIUM (EWS-28 CC util 95%, LW-ML-01 anomaly). Refs: FRAUD16:AnnexII-9/15/20/28/35, FRM24:EWS. |
| 5 | How many SMA-2 accounts? | Analyst | **7 borrowers, 11 facilities, ₹1,387M exposure** (governed). Cross-checked against CBS (6), LMS (0), Collections 60+ bucket (17). |
| 6 | Within how many days must an RFA be reported on CRILC? | Analyst (glossary VQR) | **7 days** from classification as RFA, per FRM24:4.1.3. Applies to accounts ≥ ₹3 crore aggregate exposure (FRM24:3.3.4, fn11). |

**Remaining questions (Q3, Q4, Q7, Q8)** require the stored-procedure custom tools which could not be attached via SQL. They can be tested after adding the tools through the Snowsight UI.

**Additional Q3/Q4 tests (via Agent Analyst tool — no SPs needed):**

| # | Question | Brief answer |
|---|----------|--------------|
| 3 | Meera Traders related-party transactions last 6 months | **4 RTGS debits totalling ₹1.96Cr** to Meera Agencies (C-P1A), shared director D-0042. Not in CBS/LMS. |
| 4 | Provisioning impact this month, which accounts drove it? | Net **+₹11.93Cr**. Three SMA-2→Substandard slippages: Surya Dhanlaxmi (+₹9.78Cr), Kamdhenu Pragati (+₹4.62Cr), Prakash Chetan (+₹52.5L). |

**Q7/Q8 tested via direct SP calls:**

| # | Action | Result |
|---|--------|--------|
| 7 | SP_CREATE_FINDING('B-P1') + SP_RFA_NOTE | Finding FND-B-P1-20260930 (RFA_RECOMMENDED, CRILC due 07-Oct). Full RFA note with 7 EWS grounds, Meera Agencies link, regulatory timeline, proposed actions. |
| 8 | SP_STR_DRAFT('B-P4') | STR-B-P4-20260930 — 11 cash deposits totalling ₹1.06Cr in Aug 2026, each below ₹10L, spread across 3 branches. Ground: structuring below CTR threshold. |

## Prompt 3: Streamlit UI

**Prompt:**
Create a Streamlit in Snowflake app LOANWATCH.APP.LOANWATCH_UI on warehouse LW_APP_XS with four pages: Chat (agent), Signals (filterable table + evidence expander), Actions (SP callers + generated text), Audit (last 50 audit rows). Footer on every page. Save under app/ and sql/40_streamlit.sql.

**Outcome:**
- Created 6 files under `app/`: `streamlit_app.py`, `environment.yml`, `pages/1_Chat.py`, `pages/2_Signals.py`, `pages/3_Actions.py`, `pages/4_Audit.py`.
- Deployed to `LOANWATCH.APP.LOANWATCH_UI` on warehouse `LW_APP_XS`.
- SQL saved to `sql/40_streamlit.sql`.
- App URL: `https://app.snowflake.com/EULWRCE/AX83137/#/streamlit-apps/LOANWATCH.APP.LOANWATCH_UI`

**Pages:**
1. **Chat** — sends questions to `LOANWATCH.APP.LOANWATCH_AGENT` via `DATA_AGENT_RUN`, renders text + tables + SQL expanders, supports multi-turn via thread_id.
2. **Signals** — loads `OUT.SIGNALS`, filters by borrower/category/severity, shows evidence JSON + CLAUSE_REF in expander.
3. **Actions** — borrower selector, 4 buttons (Create Finding, RFA Note, Provisioning Return, STR Draft), displays generated markdown.
4. **Audit** — last 50 rows of `OUT.AUDIT_LOG`.

## Prompt 4: System Benchmarks and NPA Comparison

**Prompt:**
Create REF.SYSTEM_BENCHMARKS (AS_OF_DATE, METRIC, VALUE, UNIT, SOURCE) and insert gross NPA ratios for SCBs FY21-FY26 plus bank fraud stats FY26. Add to semantic view APP.LOANWATCH_SV as a benchmark fact with verified query: "How does our gross NPA ratio compare to the system-wide ratio?" Test through the agent.

**Outcome:**
- Created `REF.SYSTEM_BENCHMARKS` with 8 rows: 6 GNPA ratios (9.11% FY21 → 1.80% FY26) sourced from PIB/RBI FSR, plus 2 fraud rows (10,114 cases / ₹48,021 Cr, RBI Annual Report 2025-26).
- Added `BENCHMARKS` as the 16th logical table in the semantic view with `BENCHMARK_VALUE` fact and `METRIC`/`UNIT`/`SOURCE` dimensions.
- Added VQR `Q7_NPA_VS_SYSTEM` that computes our GNPA from the governed `asset_class` table and joins the system trend from `benchmarks`.
- Initial VQR used quoted physical column `"VALUE"` which Cortex Analyst's CTE generation excluded; fixed to use logical name `BENCHMARK_VALUE`.

**Agent answer:**

| Label | GNPA % | Source |
|-------|--------|--------|
| Our book (governed) | **5.56** | — |
| System (SCB) 2021-03-31 | 9.11 | PIB press release citing RBI |
| System (SCB) 2022-03-31 | 7.28 | PIB press release citing RBI |
| System (SCB) 2023-03-31 | 4.97 | PIB press release citing RBI |
| System (SCB) 2024-03-31 | 3.47 | PIB press release citing RBI |
| System (SCB) 2025-03-31 | 2.58 | PIB (provisional) |
| System (SCB) 2026-03-31 | **1.80** | RBI FSR June 2026 |

Our synthetic book at 5.56% is ~3x the system-wide 1.80%, sitting where the industry was around FY2023.

## Prompt 5: Streamlit UI Overhaul — Judge-Ready Polish

**Prompt:**
Improve the LoanWatch Streamlit app so a Snowflake judge can see the Snowflake features behind every screen. Seven-point overhaul:
1. Overview page: live metric tiles (exposure, open signals, RFA candidates, provision), SMA-2 reconciliation table, sidebar Snowflake features block, shortened "What it does" section.
2. Chat page: provenance line per answer showing which tools were used (Analyst/Search), citation of DOC_ID/PARA_REF from search results, elapsed time. Stateless per-question calls.
3. Sample Questions page: 3 groups — 8 demo questions (verified queries), 6 "Ask anything" (generated live), 4 "RBI rules" (Cortex Search with paragraph citations). Provenance line on each answer.
4. Signals page: formatted amounts as ₹ lakh, coloured severity badges (CRITICAL/HIGH/MEDIUM/LOW), evidence & clause expander, summary metric tiles.
5. Actions page: st.download_button for each output as .md, CRILC/decision-due metric tiles above results.
6. Audit page: updated descriptive caption and footer.
7. Upload all files, confirm app loads.

**Outcome:**
- Rewrote all 6 Python files: `streamlit_app.py`, `pages/0_Sample_Questions.py`, `pages/1_Chat.py`, `pages/2_Signals.py`, `pages/3_Actions.py`, `pages/4_Audit.py`.
- Uploaded all files to `@LOANWATCH.APP.LOANWATCH_STAGE/app` with `OVERWRITE=TRUE`.
- Fixed ROOT_LOCATION: Streamlit was pointing at `app_v2/`; recreated with `ROOT_LOCATION = '@LOANWATCH.APP.LOANWATCH_STAGE/app'`.
- App URL: `https://app.snowflake.com/EULWRCE/AX83137/#/streamlit-apps/LOANWATCH.APP.LOANWATCH_UI`

**Key features per page:**

| Page | Snowflake features highlighted |
|------|-------------------------------|
| Overview | Dynamic tables (live metrics), SMA-2 reconciliation across CBS/LMS/Collections/Governed |
| Sample Questions | Cortex Agent, Cortex Analyst (semantic view + VQRs), Cortex Search (RAG with paragraph citations) |
| Chat | Stateless DATA_AGENT_RUN, provenance line (tools used, citations, elapsed time) |
| Signals | ANOMALY_DETECTION + rule-based signals on dynamic tables, evidence JSON, CLAUSE_REF |
| Actions | Stored procedures with AI_COMPLETE, download buttons for .md drafts, CRILC/decision metrics |
| Audit | Audit trail from stored procedures and signal tasks |

**Sidebar on every page:** Lists all Snowflake features in use (Cortex Agent, Cortex Analyst, Cortex Search, AI_COMPLETE, AI_PARSE_DOCUMENT, ANOMALY_DETECTION, dynamic tables, tasks, masking/row-access policies, Streamlit in Snowflake).
