# core/finance_store.py
"""
Complete, standalone finance core for Vinya Phase-1.
Drop this file at core/finance_store.py and it should work with the rest
of your project (assuming utils/dates.months_between exists).
"""

import json
import shutil
from pathlib import Path
from datetime import date, datetime
from typing import Optional, Dict, Any, List

from utils.dates import months_between

# ==================================================
# PATHS & CONSTANTS
# ==================================================
DATA_FILE = Path("data/finance.json")
BACKUP_DIR = Path("data/backups")
MAX_BACKUPS = 10

# ==================================================
# INTERNAL HELPERS
# ==================================================
def _safe_default() -> Dict[str, Any]:
    return {"loans": []}

def _ensure_dirs() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def _atomic_write(data: Any) -> None:
    tmp = DATA_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, default=str)
    tmp.replace(DATA_FILE)

def _create_backup(tag: str = "auto") -> None:
    if DATA_FILE.exists():
        name = f"finance_{_timestamp()}_{tag}.json"
        shutil.copy2(DATA_FILE, BACKUP_DIR / name)

        backups = sorted(BACKUP_DIR.glob("finance_*.json"))
        if len(backups) > MAX_BACKUPS:
            for old in backups[:-MAX_BACKUPS]:
                try:
                    old.unlink()
                except Exception:
                    pass

# ==================================================
# LOAD / SAVE
# ==================================================
def load_finance() -> Dict[str, Any]:
    _ensure_dirs()

    if not DATA_FILE.exists():
        _atomic_write(_safe_default())

    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        _create_backup(tag="corrupt")
        data = _safe_default()
        _atomic_write(data)

    # Normalize loans/payments and convert start_date strings to date
    for loan in data.get("loans", []):
        loan.setdefault("payments", [])
        if "start_date" in loan and isinstance(loan["start_date"], str):
            try:
                loan["start_date"] = datetime.fromisoformat(loan["start_date"]).date()
            except Exception:
                # if parsing fails, remove or set None (safe behavior)
                loan["start_date"] = None

    return data

def save_finance(data: Dict[str, Any], tag: str = "auto") -> None:
    _ensure_dirs()
    _create_backup(tag=tag)

    # Ensure JSON-serializable (dates -> isoformat)
    serializable = json.loads(json.dumps(data, default=str))
    _atomic_write(serializable)

# ==================================================
# EMI DERIVED CALCULATIONS (SOURCE OF TRUTH)
# ==================================================
def calculate_emis_paid(loan: Dict[str, Any]) -> int:
    return sum(1 for p in loan.get("payments", []) if p.get("note") == "EMI")

def calculate_emis_elapsed(loan: Dict[str, Any]) -> int:
    start_date = loan.get("start_date")
    if not start_date:
        return 0
    if isinstance(start_date, str):
        try:
            start_date = datetime.fromisoformat(start_date).date()
        except Exception:
            return 0
    return max(0, months_between(start_date, date.today()))

def calculate_emis_overdue(loan: Dict[str, Any]) -> int:
    return max(0, calculate_emis_elapsed(loan) - calculate_emis_paid(loan))

# ==================================================
# LOAN OPERATIONS
# ==================================================
def add_loan(
    name: str,
    principal: float,
    rate: float,
    start_date: date,
    tenure: Optional[int] = None,
    emi: Optional[float] = None,
    loan_type: str = "BANK",
    interest_frequency: str = "MONTHLY"
) -> None:
    if start_date > date.today():
        raise ValueError("Loan start date cannot be in the future")

    data = load_finance()

    loan: Dict[str, Any] = {
        "name": name,
        "principal": principal,
        "taken_amount": principal,
        "rate": rate,
        "loan_type": loan_type,
        "interest_frequency": interest_frequency,
        "start_date": start_date,
        "payments": []
    }

    if loan_type == "BANK":
        loan["tenure"] = tenure
        loan["emi"] = emi

    data["loans"].append(loan)
    save_finance(data, tag="add_loan")

def delete_loan(index: int) -> None:
    data = load_finance()
    if 0 <= index < len(data["loans"]):
        data["loans"].pop(index)
        save_finance(data, tag="delete_loan")
    else:
        raise IndexError("Loan index out of range")

# ==================================================
# PAYMENTS (MONTH-SAFE)
# ==================================================
def add_payment(loan_index: int, amount: float, note: str, month_key: Optional[str] = None) -> None:
    data = load_finance()
    loans = data.get("loans", [])

    if loan_index < 0 or loan_index >= len(loans):
        raise IndexError("Loan index out of range")

    loan = loans[loan_index]

    if month_key is None:
        month_key = datetime.utcnow().strftime("%Y-%m")

    payment_date = datetime.strptime(month_key + "-01", "%Y-%m-%d").date()

    if payment_date > date.today():
        raise ValueError("Future payments are not allowed")

    # 🚫 one EMI per month
    if loan["loan_type"] == "BANK" and note == "EMI":
        for p in loan.get("payments", []):
            if p.get("note") == "EMI" and p.get("date", "").startswith(month_key):
                raise ValueError(f"EMI already paid for {month_key}")

    # 💸 PRINCIPAL reduction for interest-only
    if loan["loan_type"] == "INTEREST_ONLY" and note == "PRINCIPAL":
        loan["principal"] = max(0, loan["principal"] - amount)

    # 💰 EMI principal reduction (BANK)
    if loan["loan_type"] == "BANK" and note == "EMI":
        rate = loan["rate"] / 12 / 100
        interest = loan["principal"] * rate
        principal_component = max(0, amount - interest)
        loan["principal"] = round(
            max(0, loan["principal"] - principal_component), 2
        )

    # ✅ ✅ ✅ THIS WAS MISSING
    loan.setdefault("payments", []).append({
        "date": payment_date.isoformat(),
        "amount": amount,
        "note": note
    })

    save_finance(data, tag=f"payment_{note.lower()}")

# ==================================================
# FINANCIAL CALCULATIONS & SCHEDULES
# ==================================================
def calculate_emi(principal: float, rate: float, tenure: int) -> float:
    r = rate / 12 / 100
    if r == 0:
        return principal / tenure
    return (principal * r * (1 + r) ** tenure) / ((1 + r) ** tenure - 1)

def calculate_interest_only(principal: float, rate: float, frequency: str) -> float:
    if frequency == "YEARLY":
        return round(principal * rate / 100, 2)
    return round((principal * rate / 100) / 12, 2)

def build_amortization_schedule(loan: Dict[str, Any]):
    principal = float(loan.get("principal", 0))
    rate = float(loan.get("rate", 0)) / 12 / 100
    emi = float(loan.get("emi", 0))
    tenure = int(loan.get("tenure", 0))

    schedule = []
    balance = principal

    emi_paid = sum(1 for p in loan.get("payments", []) if p.get("note") == "EMI")

    for month in range(1, tenure + 1):
        if balance <= 0:
            break

        opening = balance
        interest = opening * rate
        principal_component = min(emi - interest, opening)
        closing = opening - principal_component

        schedule.append({
            "month": month,
            "opening_balance": round(opening, 2),
            "emi": round(emi, 2),
            "interest": round(interest, 2),
            "principal": round(principal_component, 2),
            "closing_balance": round(closing, 2)
        })

        balance = closing

    remaining = (
        schedule[emi_paid - 1]["closing_balance"]
        if emi_paid > 0 and emi_paid <= len(schedule)
        else principal
    )

    return schedule, round(remaining, 2)

def forecast_prepayment(loan: Dict[str, Any], prepay_amount: float):
    """
    Simulate prepayment on a BANK loan.
    Does NOT modify stored data.
    """
    if loan.get("loan_type") != "BANK":
        return None

    schedule, remaining = build_amortization_schedule(loan)

    if prepay_amount <= 0 or prepay_amount >= remaining:
        return None

    rate = loan.get("rate", 0) / 12 / 100
    emi = loan.get("emi", 0)

    new_balance = remaining - prepay_amount
    months = 0
    total_interest = 0.0

    while new_balance > 0:
        interest = new_balance * rate
        principal_component = min(emi - interest, new_balance)
        new_balance -= principal_component
        total_interest += interest
        months += 1

    original_interest = sum(row.get("interest", 0) for row in schedule)

    return {
        "new_remaining_months": months,
        "interest_saved": round(original_interest - total_interest, 2)
    }

# ==================================================
# DASHBOARD SUMMARY — “YOU’RE SAFE THIS MONTH?”
# ==================================================
def dashboard_summary() -> Dict[str, Any]:
    data = load_finance()
    loans = data.get("loans", [])

    total_emi = sum(l.get("emi", 0) for l in loans if l.get("loan_type") == "BANK")
    total_outstanding = sum(l.get("principal", 0) for l in loans)

    overdue = any(calculate_emis_overdue(l) > 0 for l in loans if l.get("loan_type") == "BANK")

    if overdue:
        status = "CRITICAL"
        message = "🔴 Payment overdue. Immediate action needed."
    elif total_emi == 0:
        status = "SAFE"
        message = "🟢 No EMI burden currently."
    elif total_emi < total_outstanding * 0.02:
        status = "SAFE"
        message = "🟢 You’re safe this month."
    else:
        status = "TIGHT"
        message = "🟡 Finances are tight. One prepayment can help."

    return {
        "status": status,
        "message": message,
        "total_emi": round(total_emi, 2),
        "total_outstanding": round(total_outstanding, 2),
        "overdue": overdue
    }

# ==================================================
# MONTHLY / YEARLY INSIGHTS
# ==================================================
def spending_insights(year: int, month: Optional[int] = None) -> Dict[str, Any]:
    data = load_finance()
    loans = data.get("loans", [])

    total_paid = 0.0
    interest_paid = 0.0
    principal_paid = 0.0
    by_loan: Dict[str, float] = {}

    for loan in loans:
        rate = loan.get("rate", 0) / 12 / 100

        for p in loan.get("payments", []):
            try:
                d = datetime.fromisoformat(p["date"])
            except Exception:
                continue
            if d.year != year or (month and d.month != month):
                continue

            amt = p.get("amount", 0)
            total_paid += amt

            interest = loan.get("principal", 0) * rate
            principal = max(amt - interest, 0)

            interest_paid += interest
            principal_paid += principal

            by_loan.setdefault(loan.get("name", "Unknown"), 0.0)
            by_loan[loan.get("name", "Unknown")] += amt

    top_drain = max(by_loan, key=by_loan.get) if by_loan else None

    return {
        "total_paid": round(total_paid, 2),
        "interest_paid": round(interest_paid, 2),
        "principal_paid": round(principal_paid, 2),
        "top_drain": top_drain
    }

# ==================================================
# PREPAYMENT → STRESS SIMULATION
# ==================================================
def prepay_stress_simulation(loan_index: int, amount: float) -> Optional[Dict[str, Any]]:
    data = load_finance()
    loans = data.get("loans", [])
    if loan_index < 0 or loan_index >= len(loans):
        raise IndexError("Loan index out of range")

    loan = loans[loan_index]

    if loan.get("loan_type") != "BANK":
        return None

    before = dashboard_summary()

    remaining = max(0, loan.get("principal", 0) - amount)
    rate = loan.get("rate", 0) / 12 / 100
    emi = loan.get("emi", 0)

    balance = remaining
    months = 0
    future_interest = 0.0

    # If EMI is zero or invalid, return None
    if not emi or emi <= 0:
        return None

    while balance > 0:
        interest = balance * rate
        principal_component = min(emi - interest, balance)
        # guard against infinite loops in edge cases
        if principal_component <= 0:
            # EMI too small to cover interest; cannot amortize
            months = float("inf")
            break
        balance -= principal_component
        future_interest += interest
        months += 1

    stress_after = "SAFE" if isinstance(months, int) and months < loan.get("tenure", months + 1) else before["status"]

    return {
        "stress_change": f"{before['status']} → {stress_after}",
        "new_remaining_months": months if isinstance(months, int) else None,
        "interest_future_estimate": round(future_interest, 2),
        "interest_saved_estimate": None  # calculating saved requires original future calc; keep simple here
    }

# ==================================================
# BACKUP MANAGEMENT
# ==================================================
def list_backups() -> List[Path]:
    _ensure_dirs()
    return sorted(BACKUP_DIR.glob("finance_*.json"), reverse=True)

def restore_backup(backup_path: Path) -> None:
    _ensure_dirs()
    if not backup_path.exists():
        raise FileNotFoundError("Backup file not found")

    _create_backup(tag="before_restore")
    shutil.copy2(backup_path, DATA_FILE)
