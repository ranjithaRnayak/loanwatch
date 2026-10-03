import streamlit as st
from snowflake.snowpark.context import get_active_session

FOOTER = "All data is synthetic. GST information is treated as an indicative external data feed. Built with CoCo CLI: see PROMPTS.md in the repo."

st.set_page_config(page_title="LoanWatch", page_icon="\U0001F3E6", layout="wide")

# -- sidebar features block --
st.sidebar.markdown("---")
st.sidebar.caption(
    "**Snowflake features in use:** Cortex Agent, Cortex Analyst "
    "(semantic view), Cortex Search, AI_COMPLETE, AI_PARSE_DOCUMENT, "
    "ANOMALY_DETECTION, dynamic tables, tasks, masking and row-access "
    "policies, Streamlit in Snowflake."
)

session = get_active_session()

st.title("LoanWatch")
st.markdown("**Early-warning copilot for a bank's live loan book, built on Snowflake Cortex**")

# -- live metric tiles --
row = session.sql("""
    SELECT
        ROUND(SUM(EXPOSURE) / 1e7, 1) AS exposure_cr,
        (SELECT COUNT(*) FROM LOANWATCH.OUT.SIGNALS WHERE STATUS = 'OPEN') AS open_signals,
        (SELECT COUNT(DISTINCT BORROWER_ID) FROM LOANWATCH.OUT.FINDINGS WHERE RECOMMENDATION = 'RFA_RECOMMENDED') AS rfa_candidates,
        ROUND((SELECT SUM(PROVISION) FROM LOANWATCH.CORE.PROVISION_MONTHLY
               WHERE MONTH_END = (SELECT MAX(MONTH_END) FROM LOANWATCH.CORE.PROVISION_MONTHLY)) / 1e7, 1) AS provision_cr
    FROM LOANWATCH.CORE.ASSET_CLASS_DAILY
    WHERE AS_OF_DATE = (SELECT MAX(AS_OF_DATE) FROM LOANWATCH.CORE.ASSET_CLASS_DAILY)
""").collect()[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total exposure", f"\u20b9 {row['EXPOSURE_CR']} Cr")
c2.metric("Open signals", f"{row['OPEN_SIGNALS']}")
c3.metric("RFA candidates", f"{row['RFA_CANDIDATES']}")
c4.metric("Provision required", f"\u20b9 {row['PROVISION_CR']} Cr")

# -- SMA-2 reconciliation --
st.subheader("Same question, three answers")
sma = session.sql("""
    SELECT 'CBS snapshot' AS SOURCE,
           COUNT(DISTINCT l.BORROWER_ID) AS BORROWERS, COUNT(*) AS FACILITIES
    FROM LOANWATCH.RAW.CBS_ACCOUNT_SNAPSHOT c JOIN LOANWATCH.RAW.LOAN_ACCOUNTS l ON l.LOAN_ID = c.LOAN_ID
    WHERE c.ASSET_CLASS_CBS = 'SMA-2' AND c.AS_OF_DATE = (SELECT MAX(AS_OF_DATE) FROM LOANWATCH.RAW.CBS_ACCOUNT_SNAPSHOT)
    UNION ALL
    SELECT 'LMS snapshot', COUNT(DISTINCT l.BORROWER_ID), COUNT(*)
    FROM LOANWATCH.RAW.LMS_ACCOUNT_SNAPSHOT m JOIN LOANWATCH.RAW.LOAN_ACCOUNTS l ON l.LOAN_ID = m.LOAN_ID
    WHERE m.ASSET_CLASS_LMS = 'SMA-2' AND m.AS_OF_DATE = (SELECT MAX(AS_OF_DATE) FROM LOANWATCH.RAW.LMS_ACCOUNT_SNAPSHOT)
    UNION ALL
    SELECT 'Collections 60+ bucket', COUNT(DISTINCT k.BORROWER_ID), COUNT(*)
    FROM LOANWATCH.RAW.COLLECTIONS_CASES k
    WHERE k.BUCKET = '60+' AND k.AS_OF_DATE = (SELECT MAX(AS_OF_DATE) FROM LOANWATCH.RAW.COLLECTIONS_CASES)
    UNION ALL
    SELECT 'Governed (LoanWatch)', COUNT(*), (SELECT COUNT(*) FROM LOANWATCH.CORE.LOAN_DPD_DAILY f
        JOIN LOANWATCH.CORE.ASSET_CLASS_DAILY a2 ON a2.BORROWER_ID = f.BORROWER_ID AND a2.AS_OF_DATE = f.AS_OF_DATE
        WHERE a2.ASSET_CLASS = 'SMA-2' AND f.AS_OF_DATE = (SELECT MAX(AS_OF_DATE) FROM LOANWATCH.CORE.ASSET_CLASS_DAILY))
    FROM LOANWATCH.CORE.ASSET_CLASS_DAILY WHERE ASSET_CLASS = 'SMA-2'
      AND AS_OF_DATE = (SELECT MAX(AS_OF_DATE) FROM LOANWATCH.CORE.ASSET_CLASS_DAILY)
""").to_pandas()
st.dataframe(sma, use_container_width=True, hide_index=True)
st.caption("The governed answer applies RBI IRACP 2025 paras 30\u201331 and 44. Ask \u201cHow many SMA-2 accounts do we have?\u201d in Chat to see the reconciliation.")

st.markdown("**Start here:** open **Sample Questions** and click *\u201cWhy is Meera Traders flagged?\u201d*")

# -- shortened What it does --
st.subheader("What it does")
st.markdown(
    "LoanWatch watches every borrower for honest stress (SMA/NPA under RBI\u2019s IRACP rules) "
    "and fraud (RBI\u2019s Early Warning Signals: fund diversion, evergreening, GST mismatches). "
    "Every flag cites the source rows and the exact RBI paragraph, and the copilot drafts the "
    "regulatory paperwork \u2014 RFA note, provisioning return, STR \u2014 without filing anything."
)

st.divider()
st.caption(FOOTER)
