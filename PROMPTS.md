# PROMPTS.md — LoanWatch Prompt Log

| Metric | Value |
|--------|-------|
| Total prompts | 22 |
| Snowflake objects | 46 tables, 4 dynamic tables, 16 views, 1 semantic view, 1 agent, 1 Cortex Search service, 8 procedures, 5 tasks, 2 stages, 1 Streamlit app, 7 masking policies, 2 row-access policies, 3 roles |
| Skills used | cortex-ai-function-studio, agent-studio, developing-with-streamlit-in-snowflake |
| E2E checks passing | 13 / 13 |

---

## Prompt 1: Regulatory Document Search Pipeline

**Prompt:**
Parse every PDF in @LOANWATCH.REF.REG_STAGE with AI_PARSE_DOCUMENT in LAYOUT mode. Split the output into paragraph chunks and store them in LOANWATCH.REF.REG_CHUNKS with columns DOC_ID, PARA_REF, PAGE, CHUNK_TEXT. Create Cortex Search service LOANWATCH.REF.REG_SEARCH on CHUNK_TEXT with DOC_ID and PARA_REF as attributes, warehouse LW_XS, target lag 1 day. Save all SQL as sql/20_reg_search.sql. Test with the query "within how many days must a Red Flagged Account be reported on CRILC" and show the top 3 results with DOC_ID and PARA_REF.

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

## Prompt 2: Regex Fix During PDF Parsing

**Prompt:**
The PARA_REF regex failed with "invalid regular expression" — `(?:\.)` is not supported in Snowflake. Fix the regex so paragraph numbers like `4.1.5` are extracted correctly.

**Outcome:**
- Changed regex from `(?:\.)` to `(\\.[0-9]+)` with double-backslash escaping for Snowflake's `REGEXP_SUBSTR`.
- REG_CHUNKS rebuilt successfully with correct PARA_REF values.

## Prompt 3: Cortex Agent Creation


**Prompt:**
Create Cortex Agent LOANWATCH.APP.LOANWATCH_AGENT with Cortex Analyst over LOANWATCH.APP.LOANWATCH_SV, Cortex Search over LOANWATCH.REF.REG_SEARCH, and four stored procedures (SP_CREATE_FINDING, SP_RFA_NOTE, SP_PROVISIONING_RETURN, SP_STR_DRAFT). Agent instructions: show evidence and CLAUSE_REF, cite RBI document and paragraph, only draft reports, all data synthetic. Test with 8 questions.

**Outcome:**
- Created `LOANWATCH.APP.LOANWATCH_AGENT` with 2 tools: Cortex Analyst (semantic view) + Cortex Search (reg docs).
- Custom tools (stored procedures) could not be attached via YAML `generic` tool_resources — Snowflake returned `"generic tool resources is nil"` and `"empty type/execution environment"` errors across multiple spec formats. Procedures remain available for manual attachment via Snowsight UI.
- SQL saved to `sql/30_agent.sql`.

**Test results (6 of 8 questions):**

| # | Question | Tool used | Brief answer |
|---|----------|-----------|--------------|
| 1 | Which borrowers over 50 lakh show EWS signals this quarter? | Analyst | **38 borrowers**. Top: Meera Traders (7 signals, ₹4.2Cr), Nandi Infra (3 signals, ₹4.0Cr). |
| 2 | Why is Meera Traders flagged? | Analyst | **7 open signals** — 5 HIGH + 2 MEDIUM. Refs: FRAUD16:AnnexII-9/15/20/28/35, FRM24:EWS. |
| 3 | Meera Traders related-party transactions last 6 months | Analyst | **4 RTGS debits totalling ₹1.96Cr** to Meera Agencies, shared director D-0042. |
| 4 | Provisioning impact this month? | Analyst | Net **+₹11.93Cr**. Three SMA-2→Substandard slippages. |
| 5 | How many SMA-2 accounts? | Analyst | **7 borrowers, 11 facilities, ₹1,387M exposure** (governed). |
| 6 | Within how many days must an RFA be reported on CRILC? | Search | **7 days** per FRM24:4.1.3. |

**Q7/Q8 tested via direct SP calls:**

| # | Action | Result |
|---|--------|--------|
| 7 | SP_CREATE_FINDING('B-P1') + SP_RFA_NOTE | Finding FND-B-P1-20260930 (RFA_RECOMMENDED, CRILC due 07-Oct). |
| 8 | SP_STR_DRAFT('B-P4') | STR-B-P4-20260930 — 11 cash deposits totalling ₹1.06Cr, structuring below CTR threshold. |

## Prompt 4: Agent Recreation Attempts (Stored Procedure Tools)


**Prompt:**
The agent's tool_resources failed to parse for stored procedures. Recreate with only Analyst + Search, then try adding SPs one at a time in `generic` tool_resources format with `procedure:`, `execution_environment:`, and `type: "procedure"`.

**Outcome:**
- Tried 4 different YAML spec formats for `generic` tool_resources. All failed with "generic tool resources is nil" or "empty type/execution environment".
- Kept agent with 2 tools (Analyst + Search). SPs called directly from Streamlit instead.

## Prompt 5: Streamlit UI


**Prompt:**
Create a Streamlit in Snowflake app LOANWATCH.APP.LOANWATCH_UI on warehouse LW_APP_XS with four pages: Chat (agent), Signals (filterable table + evidence expander), Actions (SP callers + generated text), Audit (last 50 audit rows). Footer on every page. Save under app/ and sql/40_streamlit.sql.

**Outcome:**
- Created 6 files under `app/`: `streamlit_app.py`, `environment.yml`, `pages/1_Chat.py`, `pages/2_Signals.py`, `pages/3_Actions.py`, `pages/4_Audit.py`.
- Deployed to `LOANWATCH.APP.LOANWATCH_UI` on warehouse `LW_APP_XS`.
- SQL saved to `sql/40_streamlit.sql`.

## Prompt 6: st.Page / Streamlit 1.35 Fix


**Prompt:**
The app fails with "module streamlit has no attribute Page". Fix by removing st.Page and st.navigation — SiS warehouse runtime only has streamlit 1.35.0 which predates the st.navigation API.

**Outcome:**
- Removed `st.Page` and `st.navigation` calls. Switched to `pages/` folder auto-discovery (the classic Streamlit MPA pattern).
- App loads successfully on streamlit 1.35.0.

## Prompt 7: Chat parent_message_id Fix


**Prompt:**
The Chat page returns "parent_message_id cannot be null". Fix using exactly the same stateless method and payload used successfully for the Q1–Q6 tests via DATA_AGENT_RUN.

**Outcome:**
- Removed all thread_id management and multi-turn history from the agent call.
- Each question is a fresh stateless call: `DATA_AGENT_RUN(fqn, single-message-payload, TRUE)`.
- Chat history displayed via `st.session_state` but NOT sent to the agent.

## Prompt 8: System Benchmarks and NPA Comparison


**Prompt:**
Create REF.SYSTEM_BENCHMARKS (AS_OF_DATE, METRIC, VALUE, UNIT, SOURCE) and insert gross NPA ratios for SCBs FY21-FY26 plus bank fraud stats FY26. Add to semantic view APP.LOANWATCH_SV as a benchmark fact with verified query: "How does our gross NPA ratio compare to the system-wide ratio?" Test through the agent.

**Outcome:**
- Created `REF.SYSTEM_BENCHMARKS` with 8 rows: 6 GNPA ratios (9.11% FY21 → 1.80% FY26) plus 2 fraud rows.
- Added `BENCHMARKS` as the 16th logical table in the semantic view with `BENCHMARK_VALUE` fact.
- Added VQR `Q7_NPA_VS_SYSTEM`. Initial VQR used physical column `"VALUE"` which Cortex Analyst excluded from the CTE; fixed to use logical name `BENCHMARK_VALUE`.
- Agent answer: our GNPA 5.56% vs system 1.80% — ~3x the industry average.

## Prompt 9: Sample Questions Page


**Prompt:**
Does app/pages/0_Sample_Questions.py exist and is it on the stage? If not, build it now with 3 question groups: 8 demo (verified queries), 6 "Ask anything" (generated live), 4 "RBI rules" (paragraph citations). Run each new question through the agent once; if any fails, fix synonyms or verified queries.

**Outcome:**
- Built `pages/0_Sample_Questions.py` with 18 questions in 3 groups.
- All questions tested through the agent — all returned content.
- Provenance line shows which tools were used (Analyst / Search) with citations.

## Prompt 10: Streamlit UI Overhaul — Judge-Ready Polish


**Prompt:**
Improve the LoanWatch Streamlit app so a Snowflake judge can see the Snowflake features behind every screen. Seven-point overhaul: Overview with live metric tiles and SMA-2 reconciliation; Chat with provenance; Sample Questions with 3 groups; Signals with ₹ lakh formatting and severity badges; Actions with download buttons and CRILC tiles; Audit with updated caption; sidebar features block on every page.

**Outcome:**
- Rewrote all 6 Python files. Uploaded to `@LOANWATCH.APP.LOANWATCH_STAGE/app`.
- Fixed ROOT_LOCATION: Streamlit was pointing at `app_v2/`; recreated to point at `app/`.
- Sidebar on every page lists all Snowflake features in use.

## Prompt 11: Judge Access Role and Evaluator Users


**Prompt:**
Create role LW_JUDGE with read-only access to all LoanWatch objects. Create users EVALUATOR1 (evaluator@hack2skill.com) and EVALUATOR2 (hack2skillevaluator@gmail.com) with strong generated passwords, DEFAULT_ROLE LW_JUDGE, DEFAULT_WAREHOUSE LW_APP_XS, MUST_CHANGE_PASSWORD FALSE. Save as sql/50_judge_access.sql without passwords.

**Outcome:**
- Created `LW_JUDGE` with grants on warehouse, database, all schemas/tables/views, Streamlit, agent, semantic view, search service, procedures, and SNOWFLAKE.CORTEX_USER.
- Created both users with generated passwords (communicated once).
- SQL saved to `sql/50_judge_access.sql` (passwords excluded).

## Prompt 12: Overview Rename and Metric Formatting


**Prompt:**
Rename app/streamlit_app.py to app/Overview.py, update sql/40_streamlit.sql so the Streamlit uses MAIN_FILE='Overview.py', re-create the Streamlit object, and remove the old streamlit_app.py from the stage. Format exposure and provision tiles as ₹ with thousands separator and no decimals (e.g. "₹18,738 Cr").

**Outcome:**
- Renamed to `Overview.py`, removed `streamlit_app.py` from stage, recreated Streamlit with `MAIN_FILE='Overview.py'`.
- Metrics now display as `₹18,738 Cr` and `₹229 Cr` (integer, thousands-separated).
- `sql/40_streamlit.sql` updated.

## Prompt 13: Visual Polish Pass


**Prompt:**
Visual polish, no functional changes: (1) header band on every page with navy #0B1F3A background; (2) metric cards with teal #1EBEA5 left accent; (3) SMA table Governed row highlighted with pandas Styler; (4) icon prefixes on section headers; (5) severity pills in Signals (HIGH red, MEDIUM amber, LOW grey); (6) chat_message wrappers and â„ provenance prefix; (7) monospace clause refs.

**Outcome:**
- Applied all 7 visual changes across all 7 files.
- Uploaded and recreated Streamlit. All pages load.

## Prompt 14: Overview Captions and Card Heights


**Prompt:**
Three changes on Overview: (1) caption above SMA table: "Question: how many accounts are SMA-2 (61 to 90 days overdue) today?"; (2) new explanatory caption below the table about why sources disagree; (3) status lines on exposure ("across 2,000 borrowers") and provision ("month-end 30 Sep 2026") cards for consistent height.

**Outcome:**
- Added question caption above and explanatory caption below the SMA-2 table.
- Added status lines to Total exposure and Provision required cards.

## Prompt 15: Signals Clause-Ref Fix


**Prompt:**
Clause refs like "FRAUD16:AnnexII-1(b)" render a stray "(b)" block because markdown interprets parentheses as link syntax. Fix by escaping all dynamic text with html.escape() and using pure HTML (no markdown bold) in signal cards.

**Outcome:**
- Added `html.escape()` (`esc()` helper) for all dynamic text in signal cards and detail section.
- Switched from markdown `**bold**` to HTML `<b>` tags in the signal card loop.
- Clause refs now render as a single inline `<code>` pill without splitting.

## Prompt 16: E2E Test, REBUILD.md, and README Rewrite


**Prompt:**
Write sql/99_e2e.sql that runs SP_RUN_SIGNALS, calls the agent for the 8 demo questions, checks B-P1 has 7 OPEN signals including EWS-09 and LW-GST-01, that B-P2 appears in PROVISION_MONTHLY as SMA-2→SUB, that REG_CHUNKS has FRM24 para 4.1.3 with CRILC, and prints PASS/FAIL per check. Write docs/REBUILD.md with ordered rebuild commands and expected row counts. Rewrite README.md with pitch, mermaid diagram, Track 1 mapping, 8 demo questions, "How we differ", Nov 2025 RBI note, roadmap, disclaimers, judge access, and links.

**Outcome:**
- `sql/99_e2e.sql`: 13 checks, all PASS (8 agent smoke-tests + 3 B-P1 signal checks + B-P2 provision check + REG_CHUNKS search check).
- Fixed: SP_RUN_SIGNALS uses `MAX(AS_OF_DATE) FROM CORE.CALENDAR` instead of `CURRENT_DATE()` since synthetic data ends 2026-09-30.
- `docs/REBUILD.md`: step-by-step rebuild (00→10-15→16-21→30→40→50→99) with row counts for all 50 tables.
- `README.md`: all requested sections including mermaid architecture diagram.
- `docs/sample_questions.md`: 18 questions in 3 categories.

## Prompt 17: Task DAG Run


**Prompt:**
Resume the task DAG T_LW_DAYEND_ROOT, execute it once manually, confirm all five tasks complete, record the run in OUT.AUDIT_LOG, then suspend the root again. Add a "Last day-end run" caption on the Overview page.

**Outcome:**
- Resumed T_LW_DAYEND_ROOT, executed once. All 5 tasks SUCCEEDED: ROOT (2026-09-30) → REFRESH_CORE (refreshed) → ML_SCORE (retrained:2026-04-01) → RUN_SIGNALS (52 signals) → FINALIZE.
- DAYEND_START and DAYEND_END entries written to `OUT.AUDIT_LOG`.
- Root suspended again.
- Overview page now shows "Last day-end run completed: {timestamp}" from TASK_HISTORY.

## Prompt 18: Maker-Checker Workflow


**Prompt:**
Add a STATUS workflow to OUT.RFA_NOTES and OUT.STR_DRAFTS: DRAFT, SUBMITTED, APPROVED, REJECTED, with APPROVED_BY and APPROVED_AT. Add procedures SP_SUBMIT_NOTE and SP_APPROVE_NOTE; SP_APPROVE_NOTE is executable only by role LW_PRINCIPAL_OFFICER and writes to AUDIT_LOG. On the Actions page add Submit and Approve buttons; Approve is disabled unless the current role is LW_PRINCIPAL_OFFICER.

**Outcome:**
- Added `APPROVED_BY` and `APPROVED_AT` columns to both tables (STATUS already existed).
- Created role `LW_PRINCIPAL_OFFICER`.
- Created `SP_SUBMIT_NOTE(note_type, note_id)`: DRAFT → SUBMITTED, logs to AUDIT_LOG.
- Created `SP_APPROVE_NOTE(note_type, note_id, action)`: enforces `CURRENT_ROLE() = 'LW_PRINCIPAL_OFFICER'`, SUBMITTED → APPROVED/REJECTED with timestamp, logs to AUDIT_LOG.
- Actions page updated with coloured status badges (DRAFT grey, SUBMITTED blue, APPROVED teal, REJECTED red), Submit/Approve/Reject buttons, and PO-only enforcement.

## Prompt 19: Status Check — Slide Deck Numbers


**Prompt:**
Read-only check: run SMA-2 reconciliation, Meera Traders signals, provisioning delta, Balaji Steel cash deposits, Overview tiles, and REF row counts so I can compare with my slide deck.

**Outcome:**
- SMA-2: CBS 6, LMS 0, Collections 17, Governed 7 borrowers / 11 facilities / ₹138.7 Cr.
- B-P1: 7 OPEN signals, total exposure ₹2,957.2 lakh, CRILC due 2026-10-07.
- Provisioning: delta +₹1,192.8 lakh (+₹11.93 Cr), 7 SMA-2→SUB slippages. Top: B-00878 (+₹977.6L).
- B-P4: 11 cash deposits, ₹106.2 lakh, 3 branches, Aug 3–28 2026.
- Tiles: ₹18,738 Cr exposure, 52 signals, 1 RFA candidate, ₹229 Cr provision.
- REF: 641 REG_CHUNKS, 8 SYSTEM_BENCHMARKS.

## Prompt 20: Agent Regulatory Search Test


**Prompt:**
Read-only: Show REG_CHUNKS grouped by DOC_ID. Test "When can an NPA account be upgraded to standard?" (needs IRACP2025) and "Is the 2016 Early Warning Signals list still in force?" (needs FRAUD2016) through the agent.

**Outcome:**
- REG_CHUNKS: IRACP25 (334), FRAUD16 (162), FRM24 (112), FIU (16), RSA25 (10), KYC25 (7). Total 641.
- NPA upgrade: agent cited IRACP25 paras 69, 71, 62A, 72 — full repayment of all arrears required across all facilities.
- 2016 EWS list: agent correctly answered **No** — the fixed 44-item list is illustrative and superseded by FRM 2024, where banks design their own RMCB-approved indicators. Cited FRM24:3.1.1, 3.1.3, 3.3.1, FRAUD16:AnnexII-25.

## Prompt 21: Skills Used


**Prompt:**
Three CoCo skills were loaded during the build sessions to get authoritative, up-to-date syntax and patterns.

**Outcome:**
- **cortex-ai-function-studio**: loaded when working with `AI_PARSE_DOCUMENT`. Provided LAYOUT mode syntax and `page_split: true` parameter reference.
- **agent-studio**: loaded when creating the Cortex Agent. Provided YAML specification format for tools and tool_resources, and the `execution_environment` block required for the Analyst tool.
- **developing-with-streamlit-in-snowflake**: loaded when building the Streamlit app. Confirmed warehouse runtime constraints (streamlit ≤ 1.35.0, no st.Page/st.navigation).

## Prompt 22: Complete Prompt Log


**Prompt:**
Review every session and append all missing prompts to PROMPTS.md in the established format. Add a summary table at the top. Commit and push.

**Outcome:**
- Expanded from 5 entries to 22 entries covering every prompt from the project.
- Added summary table: 22 prompts, 13/13 e2e checks, object counts by type.