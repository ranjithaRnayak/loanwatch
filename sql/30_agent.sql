/*  ===========================================================
    30_agent.sql
    LoanWatch Cortex Agent — structured + regulatory + actions
    ===========================================================  */

USE DATABASE LOANWATCH;
USE SCHEMA   APP;
USE WAREHOUSE LW_XS;

-- ============================================================
-- Agent with Cortex Analyst + Cortex Search tools
-- Custom tools (stored procedures) to be added via Snowsight UI
-- once the generic tool_resources YAML format is clarified.
-- ============================================================
CREATE OR REPLACE AGENT LOANWATCH.APP.LOANWATCH_AGENT
  COMMENT = 'LoanWatch: Risk, Fraud and Regulatory Intelligence Copilot'
  PROFILE = '{"display_name": "LoanWatch Copilot", "color": "blue"}'
  FROM SPECIFICATION
  $$
  models:
    orchestration: auto

  orchestration:
    tool_not_accessible: accept
    budget:
      seconds: 120
      tokens: 32000

  instructions:
    response: >
      You are LoanWatch Copilot, a risk, fraud and regulatory intelligence assistant
      for a commercial bank.  ALL DATA IS SYNTHETIC — never claim any output is real.
      Rules you MUST follow:
      1. Always show the EVIDENCE rows (transactions, signals, metrics) behind every answer.
      2. Always cite the CLAUSE_REF (e.g. IRACP25:44, FRM24:4.1.3, FRAUD16:AnnexII-15).
      3. When answering regulatory questions, cite the RBI document name and paragraph.
      4. You only DRAFT reports; never say anything has been filed or submitted.
      5. Use LoanWatch_Analyst for structured data queries.
      6. Use RegSearch for regulatory questions about RBI circulars.
    orchestration: >
      Route structured data questions to LoanWatch_Analyst.
      Route regulatory and compliance questions to RegSearch.
    sample_questions:
      - question: "Which borrowers over 50 lakh show early-warning signals this quarter?"
      - question: "Why is Meera Traders flagged?"
      - question: "What is our provisioning impact this month?"
      - question: "Within how many days must a Red Flagged Account be reported on CRILC?"
      - question: "Create the finding and prepare the RFA note for Meera Traders."
      - question: "Prepare the STR draft for Balaji Steel Traders."

  tools:
    - tool_spec:
        type: "cortex_analyst_text_to_sql"
        name: "LoanWatch_Analyst"
        description: "Query the governed LoanWatch loan-book: borrowers, loan accounts, daily DPD, IRAC asset classification, provisioning, EWS signals, bank transactions, GST filings, related-party edges, ML anomaly scores."
    - tool_spec:
        type: "cortex_search"
        name: "RegSearch"
        description: "Search RBI regulatory documents: IRACP 2025, FRM 2024, Fraud Directions 2016, FIU-IND guidelines. Returns DOC_ID and PARA_REF for citation."

  tool_resources:
    LoanWatch_Analyst:
      execution_environment:
        type: "warehouse"
        warehouse: "LW_XS"
      semantic_view: "LOANWATCH.APP.LOANWATCH_SV"
    RegSearch:
      search_service: "LOANWATCH.REF.REG_SEARCH"
      max_results: 5
  $$;

-- ============================================================
-- Stored procedures available for manual tool attachment:
--   LOANWATCH.OUT.SP_CREATE_FINDING(VARCHAR, DATE, BOOLEAN)
--   LOANWATCH.OUT.SP_RFA_NOTE(VARCHAR, BOOLEAN)
--   LOANWATCH.OUT.SP_PROVISIONING_RETURN(DATE, BOOLEAN)
--   LOANWATCH.OUT.SP_STR_DRAFT(VARCHAR, DATE, BOOLEAN)
-- ============================================================
