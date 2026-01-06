from datetime import date
import pytest
from core.finance_store import (
    load_finance,
    save_finance,
    add_loan,
    add_payment,
    calculate_emis_paid,
)

def setup_function():
    # fresh data for every test
    save_finance({"loans": []}, tag="test_reset")


def test_emi_payment_reduces_principal():
    add_loan(
        name="Home Loan",
        principal=100000,
        rate=12,
        start_date=date(2024, 1, 1),
        tenure=12,
        emi=8885,
        loan_type="BANK",
    )

    data_before = load_finance()
    principal_before = data_before["loans"][0]["principal"]

    add_payment(
        loan_index=0,
        amount=8885,
        note="EMI",
        month_key="2024-02"
    )

    data_after = load_finance()
    loan = data_after["loans"][0]

    # ✅ principal must reduce
    assert loan["principal"] < principal_before

    # ✅ EMI count increments
    assert calculate_emis_paid(loan) == 1
def test_duplicate_emi_same_month_not_allowed():
    add_loan(
        name="Car Loan",
        principal=50000,
        rate=10,
        start_date=date(2024, 1, 1),
        tenure=10,
        emi=5200,
        loan_type="BANK",
    )

    add_payment(0, 5200, "EMI", "2024-03")

    with pytest.raises(ValueError):
        add_payment(0, 5200, "EMI", "2024-03")