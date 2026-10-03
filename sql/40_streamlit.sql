/*  ===========================================================
    40_streamlit.sql
    Deploy LoanWatch Streamlit UI to Snowflake
    ===========================================================  */

USE DATABASE LOANWATCH;
USE SCHEMA   APP;
USE WAREHOUSE LW_APP_XS;

-- ============================================================
-- 1. Stage for Streamlit files
-- ============================================================
CREATE STAGE IF NOT EXISTS LOANWATCH.APP.LOANWATCH_STAGE
  ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE');

-- ============================================================
-- 2. Upload app files
-- ============================================================
PUT 'file://app/Overview.py'                @LOANWATCH.APP.LOANWATCH_STAGE/app/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT 'file://app/environment.yml'            @LOANWATCH.APP.LOANWATCH_STAGE/app/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT 'file://app/pages/0_Sample_Questions.py' @LOANWATCH.APP.LOANWATCH_STAGE/app/pages/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT 'file://app/pages/1_Chat.py'            @LOANWATCH.APP.LOANWATCH_STAGE/app/pages/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT 'file://app/pages/2_Signals.py'         @LOANWATCH.APP.LOANWATCH_STAGE/app/pages/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT 'file://app/pages/3_Actions.py'         @LOANWATCH.APP.LOANWATCH_STAGE/app/pages/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT 'file://app/pages/4_Audit.py'           @LOANWATCH.APP.LOANWATCH_STAGE/app/pages/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

-- ============================================================
-- 3. Create or replace the Streamlit app
-- ============================================================
CREATE OR REPLACE STREAMLIT LOANWATCH.APP.LOANWATCH_UI
  ROOT_LOCATION  = '@LOANWATCH.APP.LOANWATCH_STAGE/app'
  MAIN_FILE      = 'Overview.py'
  QUERY_WAREHOUSE = LW_APP_XS
  COMMENT = 'LoanWatch: Risk, Fraud and Regulatory Intelligence copilot. Synthetic data.'
  TITLE = 'LoanWatch';
