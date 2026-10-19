"""Synthetic sample household. Not anyone's real finances.

Everything is generated from a fixed random seed with dates relative to `today`, so the sample
always shows the last six complete months plus the current month. It deliberately includes card
repayments, savings transfers, a refund, a duplicate and an over-budget month, so every feature
has something to show.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

import pandas as pd

from finlife.data import storage
from finlife.data import transactions as tx
from finlife.data.planning import add_months

SEED = 360
MONTHS_OF_HISTORY = 6


def _day(year: int, month: int, day: int) -> date:
    first = date(year, month, 1)
    last = (add_months(first, 1) - timedelta(days=1)).day
    return date(year, month, min(day, last))


def sample_transactions(today: date) -> pd.DataFrame:
    rng = random.Random(SEED)
    rows: list[dict] = []

    def add(d: date, desc: str, amount: float, account: str):
        if d <= today:
            rows.append({"date": d, "description": desc, "amount": round(amount, 2), "account": account})

    start = add_months(date(today.year, today.month, 1), -MONTHS_OF_HISTORY)
    card_spend_by_month: dict[tuple[int, int], float] = {}
    for m in range(MONTHS_OF_HISTORY + 1):
        first = add_months(start, m)
        y, mo = first.year, first.month
        card = 0.0

        def card_buy(day: int, desc: str, amount: float):
            nonlocal card
            d = _day(y, mo, day)
            if d <= today:
                card += amount
            add(d, desc, -amount, "Credit Card")

        # Income: two earners paid twice a month, plus savings interest.
        for day in (1, 15):
            add(_day(y, mo, day), "PAYROLL NORTHWIND LABS DIRECT DEP", 3250.00, "Checking")
        for day in (5, 20):
            add(_day(y, mo, day), "PAYROLL CONTOSO HEALTH DIRECT DEP", 2150.00, "Checking")
        add(_day(y, mo, 28), "INTEREST EARNED", 38.0 + m * 1.7, "Savings")

        # Fixed bills from checking.
        add(_day(y, mo, 1), "RENT PAYMENT - OAK APTS", -3100.00, "Checking")
        add(_day(y, mo, 1), "LITTLE OAKS PRESCHOOL TUITION", -1350.00, "Checking")
        add(_day(y, mo, 8), "PG ELECTRIC UTILITY", -round(rng.uniform(88, 142), 2), "Checking")
        add(_day(y, mo, 12), "FIBER INTERNET CO", -70.00, "Checking")
        add(_day(y, mo, 14), "MOBILE WIRELESS PLAN", -85.00, "Checking")
        if mo % 2 == 0:
            add(_day(y, mo, 18), "CITY WATER DEPT", -round(rng.uniform(58, 76), 2), "Checking")
        add(_day(y, mo, 3), "SAMPLE AUTO INSURANCE", -128.40, "Checking")
        add(_day(y, mo, 6), "CAR LOAN AUTOPAY SAMPLE CU", -365.00, "Checking")
        add(_day(y, mo, 13), "STUDENT LOAN SERVICER", -210.00, "Checking")
        add(_day(y, mo, 2), "TRANSFER TO SAVINGS", -800.00, "Checking")
        add(_day(y, mo, 2), "TRANSFER FROM CHECKING", 800.00, "Savings")

        # Card spending.
        for week in range(4):
            store = rng.choice(["FRESH MARKET #142", "VALLEY GROCER", "SUPERMARKET 88"])
            card_buy(3 + week * 7, store, rng.uniform(105, 195))
        for _ in range(rng.randint(6, 10)):
            place = rng.choice(["BLUE BOTTLE CAFE", "SUNNY TAQUERIA", "PIZZA PLACE", "THAI RESTAURANT", "COFFEE BAR"])
            card_buy(rng.randint(1, 28), place, rng.uniform(9, 78))
        for _ in range(3):
            card_buy(rng.randint(1, 28), "SHELL FUEL", rng.uniform(44, 68))
        card_buy(rng.randint(1, 28), "RIDESHARE TRIP", rng.uniform(14, 32))
        card_buy(4, "STREAMING VIDEO CO", 15.99)
        card_buy(9, "MUSIC PLUS", 10.99)
        card_buy(10, "CLOUD STORAGE 2TB", 2.99)
        card_buy(1, "GYM MEMBERSHIP", 39.00)
        for _ in range(rng.randint(2, 4)):
            shop = rng.choice(["ONLINE STORE ORDER", "HARDWARE DEPOT", "DEPARTMENT STORE"])
            card_buy(rng.randint(1, 28), shop, rng.uniform(18, 140))
        if rng.random() < 0.6:
            card_buy(rng.randint(1, 28), "CORNER PHARMACY", rng.uniform(12, 48))
        if rng.random() < 0.7:
            card_buy(rng.randint(1, 28), "CINEMA 12", rng.uniform(24, 46))
        card_buy(rng.randint(1, 28), "CHARITY DONATION", 25.00)
        if m == 2:  # one trip, pushing Travel over budget that month
            card_buy(11, "AIRLINE TICKET", 486.20)
            card_buy(19, "HOTEL STAY", 412.75)
        if m == 3:  # a refund and a duplicate charge to review
            card_buy(7, "ONLINE STORE ORDER", 64.50)
            add(_day(y, mo, 16), "ONLINE STORE ORDER", 64.50, "Credit Card")
            card_buy(21, "THAI RESTAURANT", 42.30)
            card_buy(21, "THAI RESTAURANT", 42.30)
        if m == 4:
            card_buy(9, "BOOKSTORE", 38.40)
        card_spend_by_month[(y, mo)] = card

        # Pay last month's card balance in full from checking.
        prev = add_months(first, -1)
        owed = card_spend_by_month.get((prev.year, prev.month))
        if owed:
            add(_day(y, mo, 22), "CREDIT CARD PAYMENT", -round(owed, 2), "Checking")
            add(_day(y, mo, 22), "PAYMENT THANK YOU", round(owed, 2), "Credit Card")

    frame = tx.normalize(pd.DataFrame(rows))
    rules = [{"keyword": k, "category": c} for k, c in tx.DEFAULT_RULES]
    return tx.apply_rules(frame.sort_values("date").reset_index(drop=True), rules)


def sample_data(today: date) -> dict:
    data = storage.empty_data()
    data["transactions"] = sample_transactions(today)

    def d(days: int) -> str:
        return (today + timedelta(days=days)).isoformat()

    first_next = add_months(date(today.year, today.month, 1), 1)
    data["budgets"] = [{"category": c, "monthly_budget": float(v)} for c, v in [
        ("Housing", 3100), ("Groceries", 620), ("Dining", 300), ("Transport", 190), ("Utilities", 300),
        ("Insurance", 130), ("Healthcare", 50), ("Subscriptions", 70), ("Shopping", 220), ("Entertainment", 50),
        ("Travel", 300), ("Education", 1400), ("Gifts & donations", 40), ("Debt payments", 575)]]
    data["bills"] = [
        {"name": "Rent", "amount": 3100.0, "frequency": "Monthly", "next_due": first_next.isoformat(),
         "category": "Housing", "autopay": False, "active": True},
        {"name": "Preschool tuition", "amount": 1350.0, "frequency": "Monthly", "next_due": first_next.isoformat(),
         "category": "Education", "autopay": True, "active": True},
        {"name": "Electricity (estimate)", "amount": 115.0, "frequency": "Monthly", "next_due": d(5),
         "category": "Utilities", "autopay": True, "active": True},
        {"name": "Internet", "amount": 70.0, "frequency": "Monthly", "next_due": d(9), "category": "Utilities",
         "autopay": True, "active": True},
        {"name": "Mobile plan", "amount": 85.0, "frequency": "Monthly", "next_due": d(11), "category": "Utilities",
         "autopay": True, "active": True},
        {"name": "Auto insurance", "amount": 128.4, "frequency": "Monthly", "next_due": d(-2), "category": "Insurance",
         "autopay": False, "active": True},
        {"name": "Renters insurance", "amount": 180.0, "frequency": "Yearly", "next_due": d(40),
         "category": "Insurance", "autopay": False, "active": True},
        {"name": "Car registration", "amount": 212.0, "frequency": "Yearly", "next_due": d(75),
         "category": "Transport", "autopay": False, "active": True},
    ]
    data["accounts"] = [
        {"name": "Everyday checking", "type": "Checking", "balance": 6850.0, "emergency_fund": False},
        {"name": "High-yield savings", "type": "Savings", "balance": 14200.0, "emergency_fund": True},
        {"name": "Workplace 401(k)", "type": "Retirement", "balance": 86500.0, "emergency_fund": False},
        {"name": "Roth IRA", "type": "Retirement", "balance": 31200.0, "emergency_fund": False},
        {"name": "Brokerage index funds", "type": "Investment", "balance": 23400.0, "emergency_fund": False},
        {"name": "Car (estimated value)", "type": "Vehicle", "balance": 14000.0, "emergency_fund": False},
    ]
    data["debts"] = [
        {"name": "Credit card", "type": "Credit card", "balance": 2450.0, "apr": 22.9, "min_payment": 75.0,
         "next_due": d(4)},
        {"name": "Car loan", "type": "Car loan", "balance": 11840.0, "apr": 6.4, "min_payment": 365.0,
         "next_due": d(17)},
        {"name": "Student loan", "type": "Student loan", "balance": 18250.0, "apr": 4.99, "min_payment": 210.0,
         "next_due": d(24)},
    ]
    data["goals"] = [
        {"name": "Emergency fund (6 months)", "target": 26000.0, "saved": 14200.0, "monthly_contribution": 800.0,
         "deadline": add_months(today, 12).isoformat()},
        {"name": "Summer trip", "target": 4000.0, "saved": 1100.0, "monthly_contribution": 400.0,
         "deadline": add_months(today, 8).isoformat()},
        {"name": "Home down payment", "target": 60000.0, "saved": 9500.0, "monthly_contribution": 600.0,
         "deadline": add_months(today, 48).isoformat()},
        {"name": "New laptop", "target": 1800.0, "saved": 1800.0, "monthly_contribution": 0.0,
         "deadline": add_months(today, 2).isoformat()},
    ]
    data["insurance"] = [
        {"policy": "Renters", "provider": "Sample Mutual", "premium": 180.0, "term_months": 12.0,
         "renewal_date": d(40), "notes": "Compare quotes 30 days before"},
        {"policy": "Auto", "provider": "Sample Auto Co", "premium": 770.4, "term_months": 6.0,
         "renewal_date": d(21), "notes": "6-month policy, paid monthly"},
        {"policy": "Term life (20-year)", "provider": "Sample Life", "premium": 312.0, "term_months": 12.0,
         "renewal_date": d(160), "notes": "Check beneficiaries"},
    ]
    data["subscriptions"] = [
        {"name": "Streaming video", "amount": 15.99, "billing": "Monthly", "renewal_date": d(4), "decision": "Keep",
         "cancelled": False},
        {"name": "Music plus", "amount": 10.99, "billing": "Monthly", "renewal_date": d(8), "decision": "Review",
         "cancelled": False},
        {"name": "Cloud storage 2TB", "amount": 2.99, "billing": "Monthly", "renewal_date": d(10), "decision": "Keep",
         "cancelled": False},
        {"name": "Gym membership", "amount": 39.0, "billing": "Monthly", "renewal_date": d(14), "decision": "Review",
         "cancelled": False},
        {"name": "News app", "amount": 99.0, "billing": "Yearly", "renewal_date": d(12), "decision": "Cancel",
         "cancelled": False},
    ]
    data["documents"] = [
        {"document": "Collect W-2s and 1099s", "category": "Tax", "due_date": d(110), "done": False, "notes": ""},
        {"document": "Download year-end bank statements", "category": "Banking", "due_date": d(85), "done": False,
         "notes": ""},
        {"document": "Save insurance declarations pages", "category": "Insurance", "due_date": d(20), "done": False,
         "notes": ""},
        {"document": "Update beneficiary forms", "category": "Estate", "due_date": None, "done": True, "notes": ""},
    ]
    data["tasks"] = [
        {"task": "Check credit reports for errors", "priority": "Medium", "due_date": d(7), "done": False,
         "notes": "Free weekly reports at the official site"},
        {"task": "Raise 401(k) contribution by 1%", "priority": "High", "due_date": d(-3), "done": False,
         "notes": "Open enrollment"},
        {"task": "Shop renters insurance quotes", "priority": "Low", "due_date": d(30), "done": False, "notes": ""},
    ]
    # Six months of history climbing toward today's totals.
    from finlife.data import networth
    now = networth.totals(data["accounts"], data["debts"])
    log = []
    for i in range(MONTHS_OF_HISTORY, 0, -1):
        when = add_months(date(today.year, today.month, 1), -i)
        log.append({"date": when.isoformat(), "assets": round(now["assets"] - 2350 * i - 180 * i * i, 2),
                    "liabilities": round(now["liabilities"] + 640 * i, 2), "note": "Sample"})
    data["net_worth_log"] = networth.record_snapshot(log, data["accounts"], data["debts"], today, "Sample")
    data["settings"].update({"currency": "USD", "starting_balance": 6850.0, "is_sample": True})
    return data
