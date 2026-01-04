import streamlit as st

from modules.dashboard import render_dashboard
from modules.finance import render_finance

st.set_page_config(page_title="VINYA", layout="wide")

st.sidebar.title("VINYA")

page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "Finance"]
)

if page == "Dashboard":
    render_dashboard()
else:
    render_finance()
