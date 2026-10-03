/*  ===========================================================
    99_e2e.sql
    End-to-end validation for LoanWatch
    Prints PASS / FAIL per check.
    ===========================================================  */

USE DATABASE LOANWATCH;
USE WAREHOUSE LW_XS;

-- ============================================================
-- 0. Results table (recreated each run)
-- ============================================================
CREATE OR REPLACE TEMPORARY TABLE _E2E_CHECKS (
    SEQ        INT,
    CHECK_NAME VARCHAR,
    RESULT     VARCHAR,   -- PASS or FAIL
    DETAIL     VARCHAR
);

-- ============================================================
-- 1. Refresh signals
-- ============================================================
-- Use the latest date in the calendar (synthetic data ends 2026-09-30)
SET E2E_AS_OF = (SELECT MAX(AS_OF_DATE) FROM LOANWATCH.CORE.CALENDAR);
CALL LOANWATCH.OUT.SP_RUN_SIGNALS($E2E_AS_OF);

-- ============================================================
-- 2. Agent smoke-tests (8 demo questions)
--    Each must return a response with a "content" array.
-- ============================================================
EXECUTE IMMEDIATE $$
DECLARE
    questions ARRAY := ARRAY_CONSTRUCT(
        'Which borrowers over 50 lakh show early-warning signals this quarter?',
        'Why is Meera Traders flagged?',
        'Show the transactions between Meera Traders and its related parties in the last 6 months.',
        'What is our provisioning impact this month, and which accounts drove it?',
        'How many SMA-2 accounts do we have?',
        'Within how many days must a Red Flagged Account be reported on CRILC?',
        'How does our gross NPA ratio compare to the system-wide ratio?',
        'What are the system-wide bank fraud statistics for FY26?'
    );
    i        INT := 0;
    q        VARCHAR;
    payload  VARCHAR;
    resp     VARCHAR;
    parsed   VARIANT;
    has_content BOOLEAN;
    result   VARCHAR;
    detail   VARCHAR;
BEGIN
    FOR i IN 0 TO 7 DO
        q := questions[i]::VARCHAR;
        payload := '{"messages":[{"role":"user","content":[{"type":"text","text":"' || REPLACE(REPLACE(q, '"', '\\"'), '''', '\\''') || '"}]}]}';
        BEGIN
            resp := (SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN(
                        'LOANWATCH.APP.LOANWATCH_AGENT',
                        :payload,
                        TRUE));
            parsed := PARSE_JSON(resp);
            has_content := (parsed:content IS NOT NULL AND ARRAY_SIZE(parsed:content) > 0);
            IF (has_content) THEN
                result := 'PASS';
                detail := 'content blocks: ' || ARRAY_SIZE(parsed:content)::VARCHAR;
            ELSE
                result := 'FAIL';
                detail := 'no content array in response';
            END IF;
        EXCEPTION
            WHEN OTHER THEN
                result := 'FAIL';
                detail := SQLERRM;
        END;
        INSERT INTO _E2E_CHECKS VALUES (:i + 1, 'AGENT_Q' || (:i + 1)::VARCHAR || ': ' || LEFT(:q, 60), :result, :detail);
    END FOR;
END;
$$;

-- ============================================================
-- 3. B-P1 signal checks
-- ============================================================
-- 3a. Exactly 7 OPEN signals
INSERT INTO _E2E_CHECKS
SELECT 10, 'B-P1: exactly 7 OPEN signals',
       IFF(cnt = 7, 'PASS', 'FAIL'),
       'found ' || cnt::VARCHAR
FROM (SELECT COUNT(*) AS cnt FROM LOANWATCH.OUT.SIGNALS WHERE BORROWER_ID = 'B-P1' AND STATUS = 'OPEN');

-- 3b. EWS-09 present
INSERT INTO _E2E_CHECKS
SELECT 11, 'B-P1: EWS-09 present',
       IFF(cnt > 0, 'PASS', 'FAIL'),
       'count ' || cnt::VARCHAR
FROM (SELECT COUNT(*) AS cnt FROM LOANWATCH.OUT.SIGNALS WHERE BORROWER_ID = 'B-P1' AND EWS_CODE = 'EWS-09' AND STATUS = 'OPEN');

-- 3c. LW-GST-01 present
INSERT INTO _E2E_CHECKS
SELECT 12, 'B-P1: LW-GST-01 present',
       IFF(cnt > 0, 'PASS', 'FAIL'),
       'count ' || cnt::VARCHAR
FROM (SELECT COUNT(*) AS cnt FROM LOANWATCH.OUT.SIGNALS WHERE BORROWER_ID = 'B-P1' AND EWS_CODE = 'LW-GST-01' AND STATUS = 'OPEN');

-- ============================================================
-- 4. B-P2 provisioning check: SMA-2 → SUBSTANDARD
-- ============================================================
INSERT INTO _E2E_CHECKS
SELECT 20, 'B-P2: SMA-2 to SUBSTANDARD in PROVISION_MONTHLY',
       IFF(cnt > 0, 'PASS', 'FAIL'),
       'matching rows: ' || cnt::VARCHAR
FROM (SELECT COUNT(*) AS cnt FROM LOANWATCH.CORE.PROVISION_MONTHLY
      WHERE BORROWER_ID = 'B-P2' AND ASSET_CLASS = 'SUBSTANDARD' AND PREV_ASSET_CLASS = 'SMA-2');

-- ============================================================
-- 5. REG_SEARCH data check: FRM24 para 4.1.3 mentions CRILC
-- ============================================================
INSERT INTO _E2E_CHECKS
SELECT 30, 'REG_CHUNKS: FRM24 para 4.1.3 contains CRILC',
       IFF(cnt > 0, 'PASS', 'FAIL'),
       'matching chunks: ' || cnt::VARCHAR
FROM (SELECT COUNT(*) AS cnt FROM LOANWATCH.REF.REG_CHUNKS
      WHERE DOC_CODE = 'FRM24' AND PARA_REF = '4.1.3' AND CHUNK_TEXT ILIKE '%CRILC%');

-- ============================================================
-- 6. Print results
-- ============================================================
SELECT SEQ, CHECK_NAME, RESULT, DETAIL
FROM _E2E_CHECKS
ORDER BY SEQ;
