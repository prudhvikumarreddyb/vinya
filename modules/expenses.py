import streamlit as st
import pandas as pd
from datetime import date, datetime
from core.expense_store import list_expenses
from core.expense_store import (
    add_expense,
    delete_expense,
    list_expenses,
    monthly_summary,
    monthly_expenses,
)

# ==================================================
# MAIN UI
# ==================================================
def render_expenses():
    st.subheader("💳 Monthly Expenses")

    # ==================================================
    # 📅 MONTH SELECTOR
    # ==================================================
    today = date.today()
    current_month = today.strftime("%Y-%m")

    # Fetch all expenses
    all_expenses = list_expenses()

    # Extract unique months from data
    months = sorted(
        {
            e["date"][:7]
            for e in all_expenses
            if e.get("date")
        },
        reverse=True,
    )

    # Ensure current month always exists
    if current_month not in months:
        months.insert(0, current_month)

    selected_month = st.selectbox(
        "📅 Select Month",
        months,
        index=0,
    )

    # ==================================================
    # 📊 SUMMARY
    # ==================================================
    summary = monthly_summary(selected_month)

    c1, c2, c3 = st.columns(3)

    c1.metric("💰 Total Spent", f"₹ {summary['total']:,.0f}")
    c2.metric("🧾 Transactions", summary["count"])

    if summary["by_category"]:
        top_cat, top_amt = next(iter(summary["by_category"].items()))
        c3.metric("🏷️ Top Category", f"{top_cat} — ₹ {top_amt:,.0f}")
    else:
        c3.metric("🏷️ Top Category", "—")

    # ==================================================
    # 📊 CATEGORY BREAKDOWN
    # ==================================================
    if summary["by_category"]:
        st.markdown("### 📊 Category Breakdown")

        cat_df = pd.DataFrame(
            [
                {"Category": k, "Amount (₹)": round(v, 2)}
                for k, v in summary["by_category"].items()
            ]
        )

        st.dataframe(cat_df, use_container_width=True, hide_index=True)

    # ==================================================
    # ➕ ADD EXPENSE
    # ==================================================
    st.markdown("---")
    st.markdown("### ➕ Add Expense")

    with st.form("add_expense_form", clear_on_submit=True):
        c1, c2 = st.columns(2)

        with c1:
            expense_date = st.date_input("Date *", value=today)
            category = st.selectbox(
                "Category *",
                [
                    "Food",
                    "Travel",
                    "Groceries",
                    "Rent",
                    "Utilities",
                    "Entertainment",
                    "Health",
                    "Shopping",
                    "Education",
                    "Misc",
                ],
            )

        with c2:
            amount = st.number_input(
                "Amount (₹) *",
                min_value=1.0,
                step=50.0,
            )
            mode = st.selectbox(
                "Payment Mode",
                ["UPI", "Card", "Cash", "NetBanking", "Wallet"],
            )

        note = st.text_input("Note (optional)")

        valid = amount > 0 and category

        submitted = st.form_submit_button("Save Expense")

        if submitted:
            if not valid:
                st.error("Please enter valid amount and category.")
            else:
                add_expense(
                    expense_date=expense_date,
                    category=category,
                    amount=amount,
                    mode=mode,
                    note=note,
                )
                st.success("Expense added ✅")
                st.rerun()

    # ==================================================
    # 📋 EXPENSE LIST
    # ==================================================
    st.markdown("---")
    st.markdown("### 📋 Expenses")

    expenses = monthly_expenses(selected_month)

    if not expenses:
        st.info("No expenses for this month yet.")
        return

    rows = []
    for e in expenses:
        rows.append({
            "Date": e.get("date"),
            "Category": e.get("category"),
            "Amount (₹)": round(float(e.get("amount", 0)), 2),
            "Mode": e.get("mode"),
            "Note": e.get("note"),
            "ID": e.get("id"),
        })

    df = pd.DataFrame(rows)

    st.dataframe(
        df.drop(columns=["ID"]),
        use_container_width=True,
        hide_index=True,
    )

    # ==================================================
    # 🗑️ DELETE EXPENSE
    # ==================================================
    st.markdown("### 🗑️ Delete Expense")

    options = {
        f"{r['Date']} | {r['Category']} | ₹{r['Amount (₹)']}": r["ID"]
        for _, r in df.iterrows()
    }

    selected_label = st.selectbox(
        "Select expense to delete",
        list(options.keys()),
        key="delete_expense_select",
    )

    if st.button("Delete Selected Expense", key="delete_expense_btn"):
        deleted = delete_expense(options[selected_label])

        if deleted:
            st.warning("Expense deleted")
            st.rerun()
        else:
            st.error("Could not delete expense.")
