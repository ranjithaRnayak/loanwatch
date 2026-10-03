import streamlit as st
import json
import time
from snowflake.snowpark.context import get_active_session

session = get_active_session()

AGENT_FQN = "LOANWATCH.APP.LOANWATCH_AGENT"
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


def build_provenance(resp, elapsed):
    parts = ["\u2744\ufe0f Answered by **Cortex Agent** LOANWATCH_AGENT"]
    used_analyst = False
    used_search = False
    search_cite = ""
    for block in resp.get("content", []):
        if block.get("type") == "tool_result":
            tr = block.get("tool_result", {})
            if tr.get("name") == "system_cortex_search_query":
                used_search = True
                for c in tr.get("content", []):
                    if c.get("type") == "json":
                        results = c.get("json", {}).get("results", [])
                        if results and isinstance(results, list):
                            first = results[0] if results else {}
                            doc = first.get("DOC_ID", "")
                            para = first.get("PARA_REF", "")
                            if doc and para:
                                search_cite = f" ({doc} p.{para})"
            if tr.get("name") == "system_execute_sql":
                for c in tr.get("content", []):
                    if c.get("type") == "json":
                        if c.get("json", {}).get("semantic_model_path"):
                            used_analyst = True
    if used_analyst:
        parts.append("Cortex Analyst on semantic view **LOANWATCH_SV**")
    if used_search:
        parts.append(f"Cortex Search on **REG_SEARCH**{search_cite}")
    parts.append(f"{elapsed:.1f}s")
    return " \u00b7 ".join(parts)


def render_and_provenance(resp, elapsed):
    if "message" in resp and "content" not in resp:
        st.error(resp["message"])
        return

    with st.chat_message("assistant"):
        for block in resp.get("content", []):
            btype = block.get("type", "")
            if btype == "text":
                txt = block.get("text", "").replace("Synthetic data - LoanWatch demo.", "").strip()
                if txt:
                    st.markdown(txt)
            elif btype == "table":
                tbl = block.get("table", {})
                rs = tbl.get("result_set", {})
                cols = [c["name"] for c in rs.get("resultSetMetaData", {}).get("rowType", [])]
                data = rs.get("data", [])
                if tbl.get("title"):
                    st.caption(tbl["title"])
                if cols and data:
                    st.dataframe([dict(zip(cols, r)) for r in data], use_container_width=True, hide_index=True)
            elif btype == "tool_result":
                tr = block.get("tool_result", {})
                for c in tr.get("content", []):
                    if c.get("type") == "json":
                        sql_text = c.get("json", {}).get("sql", "")
                        if sql_text:
                            with st.expander("Generated SQL"):
                                st.code(sql_text, language="sql")

    st.caption(build_provenance(resp, elapsed))


def run_question(q):
    payload = json.dumps({"messages": [{"role": "user", "content": [{"type": "text", "text": q}]}]})
    sql = f"SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN('{AGENT_FQN}',$${payload}$$,TRUE) AS RESP"
    t0 = time.time()
    try:
        row = session.sql(sql).collect()[0]
        resp = json.loads(row["RESP"])
        elapsed = time.time() - t0
        return resp, elapsed
    except Exception as e:
        return {"message": str(e)}, time.time() - t0


st.subheader("\u2753 Sample Questions")
st.caption("Click any question to run it through the agent. Each answer is generated live.")

DEMO = [
    "Which borrowers over 50 lakh show early-warning signals this quarter?",
    "Why is Meera Traders flagged?",
    "Show the transactions between Meera Traders and its related parties in the last 6 months.",
    "What is our provisioning impact this month, and which accounts drove it?",
    "How many SMA-2 accounts do we have?",
    "Within how many days must a Red Flagged Account be reported on CRILC?",
    "How does our gross NPA ratio compare to the system-wide ratio?",
    "What are the system-wide bank fraud statistics for FY26?",
]

FREEFORM = [
    "Which borrowers in Karnataka have a GST-to-bank gap above 50%?",
    "List loans that moved from SMA-1 to SMA-2 in September 2026.",
    "Which borrowers paid EMIs from inflows received the same day from another bank?",
    "Show all counterparties that share a director with Nandi Infra.",
    "What is the total exposure of borrowers with two or more early-warning signals?",
    "Which branch has the highest number of open signals?",
]

REGULATORY = [
    "How long does a bank have to decide whether an RFA is fraud?",
    "When can an NPA account be upgraded to standard?",
    "What is the CTR threshold for cash transactions?",
    "Is the 2016 Early Warning Signals list still in force?",
]

if "sq_resp" not in st.session_state:
    st.session_state.sq_resp = None
    st.session_state.sq_elapsed = 0
    st.session_state.sq_question = None

st.subheader("Demo questions (verified queries)")
for i, q in enumerate(DEMO):
    if st.button(q, key=f"d_{i}", use_container_width=True):
        st.session_state.sq_question = q
        with st.spinner("Running..."):
            st.session_state.sq_resp, st.session_state.sq_elapsed = run_question(q)

st.subheader("Ask anything (generated live)")
for i, q in enumerate(FREEFORM):
    if st.button(q, key=f"f_{i}", use_container_width=True):
        st.session_state.sq_question = q
        with st.spinner("Running..."):
            st.session_state.sq_resp, st.session_state.sq_elapsed = run_question(q)

st.subheader("RBI rules (answered from the loaded directions with paragraph citations)")
for i, q in enumerate(REGULATORY):
    if st.button(q, key=f"r_{i}", use_container_width=True):
        st.session_state.sq_question = q
        with st.spinner("Running..."):
            st.session_state.sq_resp, st.session_state.sq_elapsed = run_question(q)

if st.session_state.sq_resp:
    st.divider()
    with st.chat_message("user"):
        st.markdown(st.session_state.sq_question)
    render_and_provenance(st.session_state.sq_resp, st.session_state.sq_elapsed)

st.divider()
st.caption(FOOTER)
