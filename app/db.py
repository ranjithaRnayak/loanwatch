import streamlit as st
from snowflake.snowpark import Session

_session = None


def get_session() -> Session:
    global _session
    if _session is not None:
        return _session
    try:
        from snowflake.snowpark.context import get_active_session
        _session = get_active_session()
    except Exception:
        _session = Session.builder.configs(st.secrets["snowflake"]).create()
    return _session
