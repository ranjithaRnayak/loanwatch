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
        if block.get("type") == "tool_use":
            tu = block.get("tool_use", {})
            if tu.get("name") == "system_execute_sql":
                used_analyst = True
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
                        j = c.get("json", {})
                        if j.get("semantic_model_path"):
                            used_analyst = True
    if used_analyst:
        parts.append("Cortex Analyst on semantic view **LOANWATCH_SV**")
    if used_search:
        parts.append(f"Cortex Search on **REG_SEARCH**{search_cite}")
    parts.append(f"{elapsed:.1f}s")
    return " \u00b7 ".join(parts)


def render_agent_response(resp):
    for block in resp.get("content", []):
        btype = block.get("type", "")
        if btype == "text":
            txt = block.get("text", "")
            if txt.strip():
                clean = txt.replace("Synthetic data - LoanWatch demo.", "").strip()
                if clean:
                    st.markdown(clean)
        elif btype == "table":
            tbl = block.get("table", {})
            rs = tbl.get("result_set", {})
            meta = rs.get("resultSetMetaData", {})
            cols = [c["name"] for c in meta.get("rowType", [])]
            data = rs.get("data", [])
            title = tbl.get("title", "")
            if title:
                st.caption(title)
            if cols and data:
                st.dataframe(
                    [dict(zip(cols, r)) for r in data],
                    use_container_width=True, hide_index=True,
                )
        elif btype == "tool_result":
            tr = block.get("tool_result", {})
            for c in tr.get("content", []):
                if c.get("type") == "json":
                    j = c.get("json", {})
                    sql_text = j.get("sql", "")
                    if sql_text:
                        with st.expander("Generated SQL"):
                            st.code(sql_text, language="sql")


st.subheader("\U0001f4ac Chat")
st.caption("Ask about borrowers, signals, provisioning or RBI rules. Every answer cites its evidence.")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["display"], unsafe_allow_html=True)

prompt = st.chat_input("Ask LoanWatch anything...")

if prompt:
    st.session_state.chat_history.append({"role": "user", "display": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    payload = json.dumps({
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    })
    sql = f"SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN('{AGENT_FQN}',$${payload}$$,TRUE) AS RESP"

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            t0 = time.time()
            try:
                row = session.sql(sql).collect()[0]
                resp = json.loads(row["RESP"])
            except Exception as e:
                st.error(f"Agent error: {e}")
                st.stop()
            elapsed = time.time() - t0

        if "message" in resp and "content" not in resp:
            st.error(resp["message"])
            st.session_state.chat_history.append({"role": "assistant", "display": resp["message"]})
            st.stop()

        answer_parts = []
        for block in resp.get("content", []):
            if block.get("type") == "text":
                txt = block.get("text", "").replace("Synthetic data - LoanWatch demo.", "").strip()
                if txt:
                    st.markdown(txt)
                    answer_parts.append(txt)
            elif block.get("type") == "table":
                tbl = block["table"]
                rs = tbl.get("result_set", {})
                cols = [c["name"] for c in rs.get("resultSetMetaData", {}).get("rowType", [])]
                data = rs.get("data", [])
                if tbl.get("title"):
                    st.caption(tbl["title"])
                if cols and data:
                    st.dataframe([dict(zip(cols, r)) for r in data], use_container_width=True, hide_index=True)
            elif block.get("type") == "tool_result":
                tr = block["tool_result"]
                for c in tr.get("content", []):
                    if c.get("type") == "json":
                        sql_text = c["json"].get("sql", "")
                        if sql_text:
                            with st.expander("Generated SQL"):
                                st.code(sql_text, language="sql")

        st.caption(build_provenance(resp, elapsed))

        st.session_state.chat_history.append({
            "role": "assistant",
            "display": "\n\n".join(answer_parts) if answer_parts else "(see table / SQL above)",
        })

st.divider()
st.caption(FOOTER)
