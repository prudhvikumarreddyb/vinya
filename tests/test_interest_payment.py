# tests/test_interest_payment.py

import os
import json
from datetime import date

from core.finance_store import (
    load_finance,
    save_finance,
    add_loan,
    add_payment,
    calculate_interest_only
)

TEST_DATA_FILE = "data/finance.json"


def setup_function():
    """
    Runs before each test.
    Ensures clean finance state.
    """
    os.makedirs("data", exist_ok=True)
    with open(TEST_DATA_FILE, "w") as f:
        json.dump({"loans": []}, f)


def test_family_loan_interest_payment_does_not_reduce_principal():
    """
    REGRESSION TEST:
    Paying interest for INTEREST_ONLY loan:
    - must record payment
    - must NOT reduce principal
    """

    # -------------------------------
    # 1️⃣ Add family loan
    # -------------------------------
    add_loan(
        name="Test Family Loan",
        principal=100000,
        rate=12,
        start_date=date(2024, 1, 1),
        loan_type="INTEREST_ONLY",
        interest_frequency="MONTHLY"
    )

    data = load_finance()
    loan = data["loans"][0]

    original_principal = loan["principal"]

    # -------------------------------
    # 2️⃣ Calculate interest
    # -------------------------------
    interest = calculate_interest_only(
        principal=loan["principal"],
        rate=loan["rate"],
        frequency=loan["interest_frequency"]
    )

    # -------------------------------
    # 3️⃣ Pay interest
    # -------------------------------
    add_payment(
        loan_index=0,
        amount=interest,
        note="INTEREST",
        month_key="2024-02"
    )

    data = load_finance()
    loan = data["loans"][0]

    # -------------------------------
    # 4️⃣ Assertions (THIS IS THE GUARD)
    # -------------------------------

    # ✅ Payment recorded
    assert len(loan["payments"]) == 1
    assert loan["payments"][0]["note"] == "INTEREST"

    # ✅ Principal unchanged
    assert loan["principal"] == original_principal

    # ✅ Amount correct
    assert loan["payments"][0]["amount"] == interest
