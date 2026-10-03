/*  ===========================================================
    20_reg_search.sql
    Parse regulatory PDFs → paragraph chunks → Cortex Search
    ===========================================================  */

USE DATABASE LOANWATCH;
USE SCHEMA   REF;
USE WAREHOUSE LW_XS;

-- ============================================================
-- 0. Ensure stage exists (idempotent)
-- ============================================================
CREATE STAGE IF NOT EXISTS REG_STAGE
  DIRECTORY  = (ENABLE = TRUE)
  ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE');

ALTER STAGE REG_STAGE REFRESH;

-- ============================================================
-- 1. Create the chunks table
-- ============================================================
CREATE OR REPLACE TABLE REG_CHUNKS (
    DOC_ID     VARCHAR   COMMENT 'Document identifier derived from file name (e.g. IRACP2025)',
    PARA_REF   VARCHAR   COMMENT 'Paragraph number extracted from text, else page number',
    PAGE       INT       COMMENT '1-based page number',
    CHUNK_TEXT VARCHAR   COMMENT 'Paragraph / chunk text'
);

-- ============================================================
-- 2. Parse every PDF with AI_PARSE_DOCUMENT (LAYOUT mode)
--    and split into paragraph chunks
-- ============================================================
INSERT INTO REG_CHUNKS (DOC_ID, PARA_REF, PAGE, CHUNK_TEXT)
WITH parsed AS (
    SELECT
        REPLACE(RELATIVE_PATH, '.pdf', '')  AS DOC_ID,
        AI_PARSE_DOCUMENT(
            TO_FILE('@REG_STAGE', RELATIVE_PATH),
            {'mode': 'LAYOUT', 'page_split': true}
        ) AS parsed_json
    FROM DIRECTORY(@REG_STAGE)
    WHERE RELATIVE_PATH LIKE '%.pdf'
),
pages AS (
    SELECT
        DOC_ID,
        p.value:index::INT + 1              AS PAGE_NUM,
        p.value:content::VARCHAR             AS page_content
    FROM parsed,
    LATERAL FLATTEN(input => parsed_json:pages) p
),
paragraphs AS (
    SELECT
        DOC_ID,
        PAGE_NUM,
        para.index + 1                      AS para_seq,
        TRIM(para.value::VARCHAR)            AS chunk_text
    FROM pages,
    LATERAL FLATTEN(input => SPLIT(page_content, '\n\n')) para
    WHERE TRIM(para.value::VARCHAR) <> ''
      AND LENGTH(TRIM(para.value::VARCHAR)) > 10
)
SELECT
    DOC_ID,
    COALESCE(
        REGEXP_SUBSTR(chunk_text, '^([0-9]+(\\.[0-9]+)*)[\\.\\s]', 1, 1, 'e'),
        PAGE_NUM::VARCHAR
    )                                       AS PARA_REF,
    PAGE_NUM                                AS PAGE,
    chunk_text                              AS CHUNK_TEXT
FROM paragraphs;

-- ============================================================
-- 3. Create Cortex Search service
-- ============================================================
CREATE OR REPLACE CORTEX SEARCH SERVICE REG_SEARCH
  ON CHUNK_TEXT
  ATTRIBUTES DOC_ID, PARA_REF
  WAREHOUSE = LW_XS
  TARGET_LAG = '1 day'
AS (
  SELECT DOC_ID, PARA_REF, PAGE, CHUNK_TEXT
  FROM REG_CHUNKS
);

-- ============================================================
-- 4. Smoke-test query
-- ============================================================
SELECT PARSE_JSON(
    SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
        'LOANWATCH.REF.REG_SEARCH',
        '{
            "query":   "within how many days must a Red Flagged Account be reported on CRILC",
            "columns": ["DOC_ID", "PARA_REF", "CHUNK_TEXT"],
            "limit":   3
        }'
    )
)['results'] AS results;
