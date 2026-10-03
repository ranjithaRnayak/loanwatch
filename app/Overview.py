import streamlit as st
from db import get_session

FOOTER = "All data is synthetic. GST information is treated as an indicative external data feed. Built with CoCo CLI: see PROMPTS.md in the repo."

st.set_page_config(page_title="LoanWatch", page_icon="\U0001F3E6", layout="wide")

# -- header band --
st.markdown(
    '<div style="background:#0B1F3A;padding:12px 24px;border-radius:6px;display:flex;'
    'justify-content:space-between;align-items:center;margin-bottom:16px;">'
    '<span style="color:white;font-size:1.4rem;font-weight:700;">LoanWatch</span>'
    '<span style="color:#ffffffcc;font-size:0.9rem;">Risk, Fraud and Regulatory Intelligence'
    ' Copilot &middot; Snowflake Cortex</span></div>',
    unsafe_allow_html=True,
)

# -- sidebar features block --
st.sidebar.markdown("---")
st.sidebar.caption(
    "**Snowflake features in use:** Cortex Agent, Cortex Analyst "
    "(semantic view), Cortex Search, AI_COMPLETE, AI_PARSE_DOCUMENT, "
    "ANOMALY_DETECTION, dynamic tables, tasks, masking and row-access "
    "policies, Streamlit in Snowflake."
)

session = get_session()

st.markdown("**Early-warning copilot for a bank\u2019s live loan book, built on Snowflake Cortex**")

# -- live metric tiles --
row = session.sql("""
    SELECT
        ROUND(SUM(EXPOSURE) / 1e7, 0) AS exposure_cr,
        (SELECT COUNT(*) FROM LOANWATCH.OUT.SIGNALS WHERE STATUS = 'OPEN') AS open_signals,
        (SELECT COUNT(DISTINCT BORROWER_ID) FROM LOANWATCH.OUT.FINDINGS WHERE RECOMMENDATION = 'RFA_RECOMMENDED') AS rfa_candidates,
        ROUND((SELECT SUM(PROVISION) FROM LOANWATCH.CORE.PROVISION_MONTHLY
               WHERE MONTH_END = (SELECT MAX(MONTH_END) FROM LOANWATCH.CORE.PROVISION_MONTHLY)) / 1e7, 0) AS provision_cr
    FROM LOANWATCH.CORE.ASSET_CLASS_DAILY
    WHERE AS_OF_DATE = (SELECT MAX(AS_OF_DATE) FROM LOANWATCH.CORE.ASSET_CLASS_DAILY)
""").collect()[0]

# inject teal left accent on metric cards
st.markdown(
    '<style>[data-testid="stMetricValue"]{font-size:1.3rem;}'
    '.metric-card{border-left:4px solid #1EBEA5;padding-left:12px;}</style>',
    unsafe_allow_html=True,
)

exposure = int(row["EXPOSURE_CR"])
signals = int(row["OPEN_SIGNALS"])
rfa = int(row["RFA_CANDIDATES"])
provision = int(row["PROVISION_CR"])

c1, c2, c3, c4 = st.columns(4)
with c1:
    with st.container(border=True):
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total exposure", f"\u20b9 {exposure:,} Cr")
        st.caption("across 2,000 borrowers")
        st.markdown('</div>', unsafe_allow_html=True)
with c2:
    with st.container(border=True):
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Open signals", f"{signals}")
        if signals > 0:
            st.caption(f'<span style="color:#E8A33D;">\u26a0 {signals} need review</span>',
                       unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
with c3:
    with st.container(border=True):
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("RFA candidates", f"{rfa}")
        if rfa > 0:
            st.caption(f'<span style="color:#E8A33D;">\u26a0 {rfa} pending decision</span>',
                       unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
with c4:
    with st.container(border=True):
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Provision required", f"\u20b9 {provision:,} Cr")
        st.caption("month-end 30 Sep 2026")
        st.markdown('</div>', unsafe_allow_html=True)

# -- SMA-2 reconciliation --
st.subheader("\U0001f50e Same question, three answers")
st.caption("Question: how many accounts are SMA-2 (61 to 90 days overdue) today?")
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


def highlight_governed(row):
    if "Governed" in str(row.get("SOURCE", "")):
        return ["background-color: #1EBEA5; color: white; font-weight: bold"] * len(row)
    return [""] * len(row)


styled_sma = sma.style.apply(highlight_governed, axis=1)
st.dataframe(styled_sma, use_container_width=True, hide_index=True)
st.caption(
    "Core banking counts from the oldest unpaid due date, the loan system counts from the last payment, "
    "Collections uses its 60+ bucket. LoanWatch applies RBI IRACP 2025 paras 30\u201331 and 44 at borrower level, "
    "which is the number a regulator would accept. Ask \u201cHow many SMA-2 accounts do we have?\u201d in Chat "
    "to see the full reconciliation."
)

st.markdown("**Start here:** open **Sample Questions** and click *\u201cWhy is Meera Traders flagged?\u201d*")

# -- shortened What it does --
st.subheader("\U0001f3e6 What it does")
st.markdown(
    "LoanWatch watches every borrower for honest stress (SMA/NPA under RBI\u2019s IRACP rules) "
    "and fraud (RBI\u2019s Early Warning Signals: fund diversion, evergreening, GST mismatches). "
    "Every flag cites the source rows and the exact RBI paragraph, and the copilot drafts the "
    "regulatory paperwork \u2014 RFA note, provisioning return, STR \u2014 without filing anything."
)

st.divider()

# -- Last day-end run --
try:
    last_run = session.sql("""
        SELECT MAX(COMPLETED_TIME) AS ts
        FROM TABLE(LOANWATCH.INFORMATION_SCHEMA.TASK_HISTORY(
            TASK_NAME => 'T_LW_DAYEND_FINALIZE',
            SCHEDULED_TIME_RANGE_START => DATEADD(day, -7, CURRENT_TIMESTAMP()),
            RESULT_LIMIT => 1
        ))
        WHERE STATE = 'SUCCEEDED'
    """).collect()[0]["TS"]
    if last_run:
        st.caption(f"Last day-end run completed: {last_run}")
    else:
        st.caption("Last day-end run: no completed run in the last 7 days.")
except Exception:
    st.caption("Last day-end run: unavailable.")

st.caption(FOOTER)
