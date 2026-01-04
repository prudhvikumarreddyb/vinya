from datetime import date

def months_between(start: date, end: date) -> int:
    """
    Inclusive month difference.
    Example:
      start = 2024-01-01
      end   = 2024-03-15
      → 3 months
    """
    return (end.year - start.year) * 12 + (end.month - start.month) + 1
