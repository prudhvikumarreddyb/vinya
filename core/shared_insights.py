def finance_health_insight(finance_summary, health_status):
    """
    Gentle, non-judgmental insight.
    """
    if health_status == "PROTECT" and finance_summary.get("overdue"):
        return "🫶 Tough day. Avoid financial decisions today if possible."

    if health_status == "PROTECT":
        return "🫶 Low-energy day. Keep finances in maintenance mode."

    if health_status == "STEADY" and finance_summary.get("total_emi", 0) > 0:
        return "🙂 Steady day. Good for light financial check-ins."

    if health_status == "BUILD":
        return "💪 Strong day. If needed, plan or optimize finances."

    return None
