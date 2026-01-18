import streamlit as st

from modules.dashboard import render_dashboard
from modules.finance import render_finance
from modules.health import render_health
from modules.career import render_career
from modules.expenses import render_expenses

st.set_page_config(page_title="VINYA", layout="wide")

st.sidebar.title("VINYA")

page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "Finance", "Expenses", "Health", "Career"]
)

if page == "Expenses":
    render_expenses()
if page == "Dashboard":
    render_dashboard()
elif page == "Finance":
    render_finance()
elif page == "Health":
    render_health()
elif page == "Career":
    render_career()
