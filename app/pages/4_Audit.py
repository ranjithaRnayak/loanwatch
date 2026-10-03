import streamlit as st
from snowflake.snowpark.context import get_active_session

session = get_active_session()

FOOTER = "All data is synthetic. GST information is treated as an indicative external data feed. Built with CoCo CLI: see PROMPTS.md in the repo."

# -- header band --
st.markdown(
    '<div style="background:#0B1F3A;padding:12px 24px;border-radius:6px;display:flex;'
    'justify-content:space-between;align-items:center;margin-bottom:16px;">'
    '<span style="color:white;font-size:1.4rem;font-weight:700;">LoanWatch</span>'
    '<span style="color:#ffffffcc;font-size:0.9rem;">Risk, Fraud and Regulatory Intelligence'
    ' Copilot &middot; Snowflake Cortex</span></div>',
    unsafe_allow_html=True,
)

st.subheader("\U0001f9fe Audit")
st.caption(
    "Every signal, finding and report is logged with the rule and clause behind it. "
    "This table reads from **LOANWATCH.OUT.AUDIT_LOG**, which is written by each stored procedure "
    "and by the signal-generation task."
)

df = session.sql("""
    SELECT EVENT_TS, EVENT_TYPE, ACTOR, ACTOR_ROLE, OBJECT_NAME, QUERY_ID, DETAILS
    FROM LOANWATCH.OUT.AUDIT_LOG
    ORDER BY EVENT_TS DESC
    LIMIT 50
""").to_pandas()

st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()
st.caption(FOOTER)
