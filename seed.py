import random
import uuid
from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

DEMO_CUSTOMER = "990303"
DEMO_PASSWORD = "0275"


def uid():
    return str(uuid.uuid4())


def make_iban(country, bban):
    num = "".join(str(int(ch, 36)) for ch in bban + country + "00")
    return f"{country}{98 - int(num) % 97:02d}{bban}"


def iso(d):
    return d.isoformat()


def seed_user(db, user_id=None):
    existing = db.users.find_one({"customer_number": DEMO_CUSTOMER})
    if existing:
        if not existing["password_hash"].startswith(("scrypt:", "pbkdf2:")):
            db.users.update_one({"id": existing["id"]}, {"$set": {"password_hash": generate_password_hash(DEMO_PASSWORD)}})
        return
    now = datetime.now(timezone.utc)
    u = user_id or uid()
    db.users.insert_one({
        "id": u, "customer_number": DEMO_CUSTOMER,
        "password_hash": generate_password_hash(DEMO_PASSWORD),
        "name": "ALLABAUER SIEGLINDE", "address": "Praterstraße 42/7", "zip": "1020", "city": "Wien",
        "email": "habibdjaton1@gmail.com", "phone": "+43 660 1234567",
    })
    bic = "DNBAATWWXXX"
    giro, spar, bonus = uid(), uid(), uid()
    db.accounts.insert_many([
        {"id": giro, "user_id": u, "type": "checking", "name": "Gehaltskonto", "iban": make_iban("AT", "1900012345678901"), "bic": bic, "balance": 70147},
        {"id": spar, "user_id": u, "type": "savings", "name": "Online-Sparen", "iban": make_iban("AT", "1900098765432101"), "bic": bic, "balance": 412010.01, "rate": 1.75, "goal_name": "Japan-Reise", "goal_amount": 20000.0},
        {"id": bonus, "user_id": u, "type": "savings", "name": "Bonus-Sparen", "iban": make_iban("AT", "1900055501234501"), "bic": bic, "balance": 300200, "rate": 2.25, "goal_name": "Notgroschen", "goal_amount": 5000.0},
    ])
    db.cards.insert_many([
        {"id": uid(), "user_id": u, "account_id": giro, "kind": "debit", "brand": "Debit Mastercard", "holder": "ALLABAUER SIEGLINDE", "last4": "4829", "expiry": "09/28", "blocked": False, "non_eu": False, "limit_daily": 400, "limit_monthly": 3000},
        {"id": uid(), "user_id": u, "account_id": giro, "kind": "credit", "brand": "Visa Gold", "holder": "ALLABAUER SIEGLINDE", "last4": "7731", "expiry": "03/27", "blocked": False, "non_eu": True, "limit_daily": 1500, "limit_monthly": 5000},
    ])
    bens = [
        ("Anna Huber", make_iban("AT", "2011182221219800"), "GIBAATWWXXX", "Erste Bank", "delivered+anna@resend.dev", "Mariahilfer Straße 101, 1060 Wien", "Schwester"),
        ("Hausverwaltung Leopoldstadt GmbH", make_iban("AT", "1200050094950200"), "BKAUATWWXXX", "UniCredit", "delivered+miete@resend.dev", "Taborstraße 18, 1020 Wien", "Miete"),
        ("Jan de Vries", make_iban("NL", "ABNA0417164300"), "ABNANL2AXXX", "ABN AMRO", "delivered+jan@resend.dev", "Prinsengracht 263, Amsterdam", ""),
        ("Lena Schmidt", make_iban("DE", "370400440532013000"), "COBADEFFXXX", "Commerzbank", "delivered+lena@resend.dev", "Kastanienallee 9, 10435 Berlin", "Studienfreundin"),
    ]
    ben_docs = [{"id": uid(), "user_id": u, "name": n, "iban": i, "bic": b, "bank": k, "email": e, "address": a, "label": l, "created_at": iso(now)} for n, i, b, k, e, a, l in bens]
    db.beneficiaries.insert_many(ben_docs)
    nxt = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
    db.standing_orders.insert_one({"id": uid(), "user_id": u, "account_id": giro, "beneficiary_id": ben_docs[1]["id"], "amount": 950.0, "purpose": "Miete Top 7", "interval": "monthly", "next_date": nxt.date().isoformat(), "active": True})
    debits = [("Stadtwerk Donau Energie", 89.40), ("Alpen Mobilfunk", 24.90), ("Vindobona Versicherung AG", 47.15), ("Fitnessclub Prater", 39.00)]
    db.direct_debits.insert_many([{"id": uid(), "user_id": u, "account_id": giro, "creditor": c, "creditor_id": f"AT{98 - i}ZZZ000000{i:04d}", "mandate_ref": f"MDT-{2021 + i}-{i:05d}", "amount": a, "status": "active"} for i, (c, a) in enumerate(debits)])
    db.loans.insert_many([
        {"id": uid(), "user_id": u, "name": "Wohnkredit", "principal": 180000.0, "remaining": 148300.0, "monthly": 812.40, "rate": 3.4, "end_date": "2041-06-30"},
        {"id": uid(), "user_id": u, "name": "Autokredit", "principal": 18000.0, "remaining": 9450.0, "monthly": 345.00, "rate": 5.9, "end_date": "2028-09-30"},
    ])
    rnd = random.Random(42)
    shops = ["Markthalle Donau", "Café Ringstraße", "Tankstelle A2 Süd", "Buchhandlung Wieden", "Apotheke zum Hirschen", "Alpenmode Online", "Bäckerei am Karmeliterplatz", "Kino Leopoldstadt"]
    txs = []
    for m in range(3):
        base = (now.replace(day=1) - timedelta(days=m * 30)).replace(day=1, hour=9)
        txs.append({"amount": 3420.00, "counterparty": "Technik Wien GmbH", "purpose": "Gehalt", "category": "salary", "date": base})
        txs.append({"amount": -950.00, "counterparty": "Hausverwaltung Leopoldstadt GmbH", "purpose": "Miete Top 7", "category": "standing", "date": base + timedelta(days=1)})
        txs.append({"amount": -812.40, "counterparty": "UniCredit Bank Austria", "purpose": "Rate Wohnkredit", "category": "loan", "date": base + timedelta(days=4)})
        for j, (c, a) in enumerate(debits):
            txs.append({"amount": -a, "counterparty": c, "purpose": "SEPA-Lastschrift", "category": "debit", "date": base + timedelta(days=5 + j)})
        for _ in range(9):
            txs.append({"amount": -round(rnd.uniform(4, 140), 2), "counterparty": rnd.choice(shops), "purpose": "Kartenzahlung Debit ****4829", "category": "card", "date": base + timedelta(days=rnd.randint(2, 27), hours=rnd.randint(0, 9))})
    txs.append({"amount": -150.00, "counterparty": "Anna Huber", "purpose": "Geburtstagsgeschenk", "category": "transfer", "date": now - timedelta(days=12)})
    txs = [t for t in txs if t["date"] <= now]
    db.transactions.insert_many([{**t, "id": uid(), "user_id": u, "account_id": giro, "date": iso(t["date"]), "reference": f"DNB{rnd.randint(10**9, 10**10 - 1)}"} for t in txs])
    notes = [
        ("loan_due", {"name": "Wohnkredit", "amount": 812.40}, 1, False),
        ("card_used", {"amount": 64.20, "merchant": "Markthalle Donau", "last4": "4829"}, 2, False),
        ("transfer_done", {"amount": 150.0, "name": "Anna Huber"}, 12, False),
        ("salary", {"amount": 3420.0}, 15, True),
        ("card_used", {"amount": 18.90, "merchant": "Café Ringstraße", "last4": "4829"}, 20, True),
    ]
    db.notifications.insert_many([{"id": uid(), "user_id": u, "type": ty, "params": p, "read": r, "date": iso(now - timedelta(days=d))} for ty, p, d, r in notes])


def reset_user(db, user_id):
    for col in ["users", "accounts", "cards", "beneficiaries", "standing_orders", "direct_debits", "loans", "transactions", "notifications", "loan_applications"]:
        db[col].delete_many({"user_id": user_id} if col != "users" else {"id": user_id})
    seed_user(db, user_id)
def update_demo_balances(db):
    account_balances = {
        "Gehaltskonto": 70147,
        "Online-Sparen": 412010.01,
        "Bonus-Sparen": 300200,
    }

    user = db.users.find_one({"customer_number": DEMO_CUSTOMER})
    if not user:
        return

    for account_name, balance in account_balances.items():
        db.accounts.update_one(
            {
                "user_id": user["id"],
                "name": account_name,
            },
            {"$set": {"balance": balance}},
        )
