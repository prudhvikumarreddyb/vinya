import json
from pathlib import Path
from datetime import datetime, date
import shutil
import uuid
from collections import defaultdict

# ==================================================
# PATHS & CONSTANTS
# ==================================================
EXPENSE_DATA_FILE = Path("data/expenses.json")
BACKUP_DIR = Path("data/backups")
MAX_BACKUPS = 10

# ==================================================
# INTERNAL HELPERS
# ==================================================
def _safe_default():
    return {
        "expenses": []
    }


def _ensure_dirs():
    EXPENSE_DATA_FILE.parent.mkdir(exist_ok=True)
    BACKUP_DIR.mkdir(exist_ok=True)


def _timestamp():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _atomic_write(data):
    tmp = EXPENSE_DATA_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(EXPENSE_DATA_FILE)


def _create_backup(tag="auto"):
    if EXPENSE_DATA_FILE.exists():
        name = f"expenses_{_timestamp()}_{tag}.json"
        shutil.copy2(EXPENSE_DATA_FILE, BACKUP_DIR / name)

        backups = sorted(BACKUP_DIR.glob("expenses_*.json"))
        if len(backups) > MAX_BACKUPS:
            for old in backups[:-MAX_BACKUPS]:
                old.unlink()


def _validate_schema(data):
    """
    Ensures required structure exists.
    Repairs silently if corrupted.
    """
    if not isinstance(data, dict):
        return _safe_default()

    if "expenses" not in data or not isinstance(data["expenses"], list):
        data["expenses"] = []

    # normalize fields
    for e in data["expenses"]:
        e.setdefault("id", str(uuid.uuid4()))
        e.setdefault("date", date.today().isoformat())
        e.setdefault("category", "Misc")
        e.setdefault("amount", 0)
        e.setdefault("mode", "UPI")
        e.setdefault("note", "")

    return data

# ==================================================
# LOAD / SAVE
# ==================================================
def load_expenses():
    _ensure_dirs()

    if not EXPENSE_DATA_FILE.exists():
        _atomic_write(_safe_default())

    try:
        with open(EXPENSE_DATA_FILE, "r") as f:
            data = json.load(f)
    except Exception:
        _create_backup(tag="corrupt")
        data = _safe_default()
        _atomic_write(data)

    data = _validate_schema(data)
    return data


def save_expenses(data, tag="auto"):
    _ensure_dirs()
    _create_backup(tag=tag)
    _atomic_write(data)

# ==================================================
# CRUD OPERATIONS
# ==================================================
def add_expense(
    expense_date,
    category,
    amount,
    mode="UPI",
    note=""
):
    """
    expense_date: datetime.date OR ISO string
    """
    data = load_expenses()

    if isinstance(expense_date, date):
        expense_date = expense_date.isoformat()

    expense = {
        "id": str(uuid.uuid4()),
        "date": expense_date,
        "category": category,
        "amount": float(amount),
        "mode": mode,
        "note": note or "",
        "created_at": datetime.utcnow().isoformat(),
    }

    data["expenses"].append(expense)
    save_expenses(data, tag="add_expense")

    return expense


def delete_expense(expense_id):
    data = load_expenses()
    before = len(data["expenses"])

    data["expenses"] = [
        e for e in data["expenses"]
        if e.get("id") != expense_id
    ]

    if len(data["expenses"]) != before:
        save_expenses(data, tag="delete_expense")
        return True

    return False


def list_expenses():
    data = load_expenses()
    return sorted(
        data.get("expenses", []),
        key=lambda e: e.get("date", ""),
        reverse=True
    )

# ==================================================
# 📊 ANALYTICS
# ==================================================
def monthly_expenses(month_key=None):
    """
    month_key format: YYYY-MM
    Defaults to current month.
    """
    if month_key is None:
        month_key = date.today().strftime("%Y-%m")

    expenses = list_expenses()
    return [
        e for e in expenses
        if e.get("date", "").startswith(month_key)
    ]


def monthly_summary(month_key=None):
    """
    Returns:
    {
        total: float,
        by_category: {category: total},
        count: int
    }
    """
    items = monthly_expenses(month_key)

    by_category = defaultdict(float)
    total = 0.0

    for e in items:
        amt = float(e.get("amount", 0))
        cat = e.get("category", "Misc")

        by_category[cat] += amt
        total += amt

    return {
        "month": month_key or date.today().strftime("%Y-%m"),
        "total": round(total, 2),
        "count": len(items),
        "by_category": dict(sorted(by_category.items(), key=lambda x: -x[1])),
    }


def top_category(month_key=None):
    summary = monthly_summary(month_key)
    if not summary["by_category"]:
        return None

    category, amount = next(iter(summary["by_category"].items()))
    return {
        "category": category,
        "amount": amount
    }

# ==================================================
# 🧪 QUICK SELF TEST (manual)
# ==================================================
if __name__ == "__main__":
    add_expense(date.today(), "Food", 250, "UPI", "Lunch")
    add_expense(date.today(), "Travel", 120, "Card", "Auto")

    print(monthly_summary())
