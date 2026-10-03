import streamlit as st
import json
from db import get_session

session = get_session()

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

STATUS_COLORS = {
    "DRAFT": ("#888", "white"),
    "SUBMITTED": ("#1976D2", "white"),
    "APPROVED": ("#1EBEA5", "white"),
    "REJECTED": ("#D64545", "white"),
}


def status_badge(status):
    bg, fg = STATUS_COLORS.get(status, ("#888", "white"))
    return (f'<span style="background:{bg};color:{fg};padding:2px 10px;'
            f'border-radius:12px;font-size:0.8rem;font-weight:600;">{status}</span>')


current_role = session.sql("SELECT CURRENT_ROLE()").collect()[0][0]
is_po = (current_role == "LW_PRINCIPAL_OFFICER")

st.subheader("\U0001f4c4 Actions")
st.caption(
    "Generate the regulatory paperwork for a borrower. Each button calls a **stored procedure** "
    "that uses **AI_COMPLETE** to draft the output and logs the action to the **audit trail**. "
    "All outputs are drafts for a human to review."
)


@st.cache_data(ttl=600)
def load_borrowers():
    return session.sql("""
        SELECT DISTINCT s.BORROWER_ID, s.BORROWER_NAME
        FROM LOANWATCH.OUT.SIGNALS s WHERE s.STATUS = 'OPEN'
        ORDER BY s.BORROWER_NAME
    """).to_pandas()


borrowers_df = load_borrowers()
borrower_options = dict(zip(borrowers_df["BORROWER_NAME"], borrowers_df["BORROWER_ID"]))

sel_name = st.selectbox("Borrower (with open signals)", list(borrower_options.keys()))
sel_id = borrower_options.get(sel_name, "")

# -- CRILC / decision-due metric tiles --
try:
    metrics = session.sql(f"""
        SELECT
            (SELECT COUNT(*) FROM LOANWATCH.OUT.FINDINGS
             WHERE BORROWER_ID = '{sel_id}' AND RECOMMENDATION = 'RFA_RECOMMENDED') AS rfa_findings,
            (SELECT MIN(CRILC_DUE_DATE) FROM LOANWATCH.OUT.FINDINGS
             WHERE BORROWER_ID = '{sel_id}' AND CRILC_DUE_DATE IS NOT NULL) AS next_crilc,
            (SELECT MIN(EXAMINE_BY_DATE) FROM LOANWATCH.OUT.FINDINGS
             WHERE BORROWER_ID = '{sel_id}' AND EXAMINE_BY_DATE IS NOT NULL) AS examine_by
    """).collect()[0]
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("RFA findings", metrics["RFA_FINDINGS"])
    mc2.metric("CRILC due", str(metrics["NEXT_CRILC"] or "None"))
    mc3.metric("Examine by", str(metrics["EXAMINE_BY"] or "None"))
except Exception:
    pass

if "finding_id" not in st.session_state:
    st.session_state.finding_id = None

st.divider()

col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("Create Finding", use_container_width=True):
        with st.spinner("Creating finding..."):
            try:
                row = session.sql(
                    f"CALL LOANWATCH.OUT.SP_CREATE_FINDING('{sel_id}', NULL, TRUE)"
                ).collect()[0]
                result = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                st.session_state.finding_id = result.get("finding_id")
                st.session_state.finding_result = result
            except Exception as e:
                st.error(f"Error: {e}")

with col2:
    if st.button("Prepare RFA Note", use_container_width=True):
        fid = st.session_state.finding_id
        if not fid:
            st.warning("Create a Finding first.")
        else:
            with st.spinner("Preparing RFA note..."):
                try:
                    row = session.sql(
                        f"CALL LOANWATCH.OUT.SP_RFA_NOTE('{fid}', TRUE)"
                    ).collect()[0]
                    result = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                    st.session_state.rfa_result = result
                except Exception as e:
                    st.error(f"Error: {e}")

with col3:
    if st.button("Provisioning Return", use_container_width=True):
        with st.spinner("Generating provisioning return..."):
            try:
                row = session.sql(
                    "CALL LOANWATCH.OUT.SP_PROVISIONING_RETURN(NULL, TRUE)"
                ).collect()[0]
                result = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                st.session_state.prov_result = result
            except Exception as e:
                st.error(f"Error: {e}")

with col4:
    if st.button("Draft STR", use_container_width=True):
        with st.spinner("Drafting STR..."):
            try:
                row = session.sql(
                    f"CALL LOANWATCH.OUT.SP_STR_DRAFT('{sel_id}', NULL, TRUE)"
                ).collect()[0]
                result = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                st.session_state.str_result = result
            except Exception as e:
                st.error(f"Error: {e}")

st.divider()

# -- results with download, submit, approve buttons and status badges --
if "finding_result" in st.session_state:
    r = st.session_state.finding_result
    with st.expander(f"Finding: {r.get('finding_id', '')} ({r.get('recommendation', '')})", expanded=True):
        st.markdown(f"**Status:** {r.get('status')} | **CRILC due:** {r.get('crilc_due_date', 'N/A')} | **Examine by:** {r.get('examine_by_date', 'N/A')}")
        narrative = r.get("narrative", "")
        if not narrative:
            frow = session.sql(
                f"SELECT NARRATIVE FROM LOANWATCH.OUT.FINDINGS WHERE FINDING_ID = '{r.get('finding_id')}'"
            ).collect()
            narrative = frow[0]["NARRATIVE"] if frow else ""
        if narrative:
            st.markdown(narrative)
            st.download_button("Download finding (.md)", narrative,
                               file_name=f"finding_{r.get('finding_id', 'unknown')}.md",
                               mime="text/markdown", key="dl_finding")

if "rfa_result" in st.session_state:
    r = st.session_state.rfa_result
    note_id = r.get("note_id", "")
    # fetch current status from DB
    rfa_row = session.sql(
        f"SELECT STATUS, APPROVED_BY, APPROVED_AT FROM LOANWATCH.OUT.RFA_NOTES WHERE NOTE_ID = '{note_id}'"
    ).collect()
    rfa_status = rfa_row[0]["STATUS"] if rfa_row else "DRAFT"
    with st.expander(f"RFA Note: {note_id}", expanded=True):
        st.markdown(f"Status: {status_badge(rfa_status)}", unsafe_allow_html=True)
        if rfa_row and rfa_row[0]["APPROVED_BY"]:
            st.caption(f"Approved by {rfa_row[0]['APPROVED_BY']} at {rfa_row[0]['APPROVED_AT']}")
        note = r.get("note", "")
        if not note:
            nrow = session.sql(
                f"SELECT NOTE_TEXT FROM LOANWATCH.OUT.RFA_NOTES WHERE NOTE_ID = '{note_id}'"
            ).collect()
            note = nrow[0]["NOTE_TEXT"] if nrow else ""
        if note:
            st.markdown(note)
            bc1, bc2, bc3, bc4 = st.columns(4)
            with bc1:
                st.download_button("Download (.md)", note,
                                   file_name=f"rfa_note_{note_id}.md",
                                   mime="text/markdown", key="dl_rfa")
            with bc2:
                if rfa_status == "DRAFT":
                    if st.button("Submit for approval", key="submit_rfa", use_container_width=True):
                        res = session.sql(f"CALL LOANWATCH.OUT.SP_SUBMIT_NOTE('RFA', '{note_id}')").collect()[0]
                        st.rerun()
            with bc3:
                if rfa_status == "SUBMITTED":
                    if st.button("Approve", key="approve_rfa", use_container_width=True,
                                 disabled=not is_po):
                        res = session.sql(f"CALL LOANWATCH.OUT.SP_APPROVE_NOTE('RFA', '{note_id}', 'APPROVE')").collect()[0]
                        st.rerun()
            with bc4:
                if rfa_status == "SUBMITTED":
                    if st.button("Reject", key="reject_rfa", use_container_width=True,
                                 disabled=not is_po):
                        res = session.sql(f"CALL LOANWATCH.OUT.SP_APPROVE_NOTE('RFA', '{note_id}', 'REJECT')").collect()[0]
                        st.rerun()
            if not is_po and rfa_status == "SUBMITTED":
                st.caption("Approve/Reject requires role LW_PRINCIPAL_OFFICER.")

if "prov_result" in st.session_state:
    r = st.session_state.prov_result
    with st.expander(f"Provisioning Return: {r.get('report_id', '')}", expanded=True):
        commentary = r.get("commentary", "")
        if not commentary:
            prow = session.sql(
                f"SELECT REPORT_TEXT FROM LOANWATCH.OUT.REPORTS WHERE REPORT_ID = '{r.get('report_id')}'"
            ).collect()
            commentary = prow[0]["REPORT_TEXT"] if prow else ""
        if commentary:
            st.markdown(commentary)
            st.download_button("Download provisioning return (.md)", commentary,
                               file_name=f"provisioning_{r.get('report_id', 'unknown')}.md",
                               mime="text/markdown", key="dl_prov")

if "str_result" in st.session_state:
    r = st.session_state.str_result
    str_id = r.get("str_id", "")
    # fetch current status
    str_row = session.sql(
        f"SELECT STATUS, APPROVED_BY, APPROVED_AT FROM LOANWATCH.OUT.STR_DRAFTS WHERE STR_ID = '{str_id}'"
    ).collect() if str_id else []
    str_status = str_row[0]["STATUS"] if str_row else "DRAFT"
    with st.expander(f"STR Draft: {str_id}", expanded=True):
        if "error" in r:
            st.warning(r["error"])
            if "clause_ref" in r:
                st.markdown(f"**Clause ref:** {r['clause_ref']}")
        else:
            st.markdown(f"Status: {status_badge(str_status)}", unsafe_allow_html=True)
            if str_row and str_row[0]["APPROVED_BY"]:
                st.caption(f"Approved by {str_row[0]['APPROVED_BY']} at {str_row[0]['APPROVED_AT']}")
            draft = r.get("draft", "")
            if not draft:
                srow = session.sql(
                    f"SELECT DRAFT_TEXT FROM LOANWATCH.OUT.STR_DRAFTS WHERE STR_ID = '{str_id}'"
                ).collect()
                draft = srow[0]["DRAFT_TEXT"] if srow else ""
            if draft:
                st.markdown(draft)
                sc1, sc2, sc3, sc4 = st.columns(4)
                with sc1:
                    st.download_button("Download (.md)", draft,
                                       file_name=f"str_draft_{str_id}.md",
                                       mime="text/markdown", key="dl_str")
                with sc2:
                    if str_status == "DRAFT":
                        if st.button("Submit for approval", key="submit_str", use_container_width=True):
                            res = session.sql(f"CALL LOANWATCH.OUT.SP_SUBMIT_NOTE('STR', '{str_id}')").collect()[0]
                            st.rerun()
                with sc3:
                    if str_status == "SUBMITTED":
                        if st.button("Approve", key="approve_str", use_container_width=True,
                                     disabled=not is_po):
                            res = session.sql(f"CALL LOANWATCH.OUT.SP_APPROVE_NOTE('STR', '{str_id}', 'APPROVE')").collect()[0]
                            st.rerun()
                with sc4:
                    if str_status == "SUBMITTED":
                        if st.button("Reject", key="reject_str", use_container_width=True,
                                     disabled=not is_po):
                            res = session.sql(f"CALL LOANWATCH.OUT.SP_APPROVE_NOTE('STR', '{str_id}', 'REJECT')").collect()[0]
                            st.rerun()
                if not is_po and str_status == "SUBMITTED":
                    st.caption("Approve/Reject requires role LW_PRINCIPAL_OFFICER.")

st.divider()
st.caption(FOOTER)
