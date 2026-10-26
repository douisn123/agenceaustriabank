import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

from babel.numbers import format_currency
from dotenv import load_dotenv
from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for, make_response
from flask_babel import Babel, format_date, format_datetime, format_decimal, gettext as _
from werkzeug.exceptions import NotFound
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash

load_dotenv(Path(__file__).parent / ".env")
from docs import receipt_pdf, send_confirmation, statement_pdf  # noqa: E402
from seed import reset_user, seed_user, uid, update_demo_balances # noqa: E402
from minidb import Database, ReturnDocument  # noqa: E402

LANGS = {"de": "de_AT", "nl": "nl_NL"}
DAILY_TRANSFER_LIMIT = float("inf")
EMAIL_DAILY_LIMIT = int(os.environ.get("EMAIL_DAILY_LIMIT", "50"))
NOID = {"_id": 0}
HAS_EMAIL_LOGO = (Path(__file__).parent / "static" / "logo-email.png").exists()

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.config.update(SECRET_KEY=os.environ["SECRET_KEY"], PERMANENT_SESSION_LIFETIME=timedelta(days=30),
                  SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", BABEL_DEFAULT_LOCALE="de")
if os.environ.get("VERCEL"):
    db = Database(os.environ["TURSO_DATABASE_URL"], os.environ.get("TURSO_AUTH_TOKEN"))
else:
    DB_PATH = os.environ.get("DB_PATH") or str(Path(__file__).parent / "danubia.db")
    db = Database(f"file:{DB_PATH}")


def get_lang():
    return session.get("lang", "de")


babel = Babel(app, locale_selector=lambda: get_lang())
seed_user(db)
update_demo_balances(db)


def now():
    return datetime.now(timezone.utc)


def money(v):
    return format_currency(v or 0, "EUR", locale=LANGS[get_lang()])


def fdate(iso, time=False):
    d = datetime.fromisoformat(iso) if isinstance(iso, str) else iso
    return format_datetime(d, "medium") if time else format_date(d, "medium")


def fiban(s):
    return re.sub(r"(.{4})", r"\1 ", s or "").strip()


def month_name(m):
    return format_date(datetime.strptime(m + "-01", "%Y-%m-%d"), "MMMM yyyy")


app.jinja_env.filters.update(money=money, fdate=fdate, iban=fiban, num=lambda v: format_decimal(v), month=month_name)


def valid_iban(iban):
    s = iban.replace(" ", "").upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", s):
        return False
    return int("".join(str(int(c, 36)) for c in s[4:] + s[:4])) % 97 == 1


def category_label(c):
    return {"transfer": _("Überweisung"), "standing": _("Dauerauftrag"), "card": _("Kartenzahlung"), "debit": _("Lastschrift"),
            "salary": _("Gehalt"), "savings": _("Umbuchung"), "loan": _("Kreditrate")}.get(c, c)


def note_text(n):
    p = {**n.get("params", {})}
    if "amount" in p:
        p["amount"] = money(p["amount"])
    msgs = {
        "transfer_done": _("Überweisung über %(amount)s an %(name)s durchgeführt."),
        "email_sent": _("Bestätigung an %(name)s (%(email)s) gesendet."),
        "email_failed": _("Bestätigung an %(name)s konnte nicht gesendet werden."),
        "card_used": _("Karte ****%(last4)s bei %(merchant)s verwendet: %(amount)s."),
        "loan_due": _("Nächste Rate %(name)s: %(amount)s wird in Kürze fällig."),
        "salary": _("Gehaltseingang: %(amount)s."),
        "card_blocked": _("Karte ****%(last4)s wurde gesperrt."),
        "card_unblocked": _("Karte ****%(last4)s wurde entsperrt."),
        "savings_moved": _("%(amount)s auf %(name)s umgebucht.") if p.get("direction") == "deposit" else _("%(amount)s von %(name)s umgebucht."),
        "loan_applied": _("Kreditanfrage über %(amount)s eingereicht."),
    }
    return msgs.get(n["type"], n["type"]) % p


app.jinja_env.globals.update(category_label=category_label, note_text=note_text)


def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        u = session.get("uid") and db.users.find_one({"id": session["uid"]}, {"_id": 0, "password_hash": 0})
        if not u:
            session.pop("uid", None)
            return redirect(url_for("login"))
        g.user = u
        return f(*a, **kw)
    return wrapper


@app.context_processor
def inject():
    unread = db.notifications.count_documents({"user_id": g.user["id"], "read": False}) if "user" in g else 0
    return {"lang": get_lang(), "unread": unread}


def own(col, id_):
    doc = db[col].find_one({"id": id_, "user_id": g.user["id"]}, NOID)
    if not doc:
        abort(404)
    return doc


def notify(type_, params):
    db.notifications.insert_one({"id": uid(), "user_id": g.user["id"], "type": type_, "params": params, "read": False, "date": now().isoformat()})


def to_float(v):
    try:
        return round(float(str(v).replace(",", ".")), 2)
    except (TypeError, ValueError):
        return 0.0


def back(default="dashboard"):
    nxt = request.values.get("next", "")
    return redirect(url_for(nxt) if nxt in app.view_functions else url_for(default))


# ---------- Language & auth ----------
@app.route("/lang/<code>")
def set_lang(code):
    if code in LANGS:
        session.permanent = True
        session["lang"] = code
    ref = request.referrer or ""
    return redirect(ref if ref.startswith(request.host_url) else url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = db.users.find_one({"customer_number": request.form.get("customer_number", "").strip()}, NOID)
        if u and check_password_hash(u["password_hash"], request.form.get("password", "")):
            session.permanent = True
            session["uid"] = u["id"]
            return redirect(url_for("dashboard"))
        flash(_("Verfügernummer oder Passwort ist falsch."), "error")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("uid", None)
    return redirect(url_for("login"))


@app.route("/demo/reset", methods=["POST"])
@login_required
def demo_reset():
    reset_user(db, g.user["id"])
    flash(_("Demo-Daten zurückgesetzt"), "success")
    return redirect(url_for("dashboard"))


# ---------- Dashboard & profile ----------
@app.route("/")
@login_required
def dashboard():
    run_due_standing_orders()
    accounts = list(db.accounts.find({"user_id": g.user["id"]}, NOID))
    recent = list(db.transactions.find({"user_id": g.user["id"]}, NOID).sort("date", -1).limit(8))
    notes = list(db.notifications.find({"user_id": g.user["id"], "read": False}, NOID).sort("date", -1).limit(3))
    return render_template("dashboard.html", accounts=accounts, recent=recent, notes=notes, total=sum(a["balance"] for a in accounts))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        data = {k: request.form.get(k, "").strip()[:120] for k in ["name", "address", "zip", "city", "email", "phone"]}
        if not all(data.values()) or not re.fullmatch(r"\S+@\S+\.\S+", data["email"]):
            flash(_("Bitte alle Felder korrekt ausfüllen."), "error")
        else:
            db.users.update_one({"id": g.user["id"]}, {"$set": data})
            flash(_("Gespeichert"), "success")
        return redirect(url_for("profile"))
    return render_template("profile.html", accounts=list(db.accounts.find({"user_id": g.user["id"]}, NOID)), edit=request.args.get("edit"))


# ---------- Beneficiaries ----------
def ben_from_form():
    f = {k: request.form.get(k, "").strip() for k in ["name", "iban", "bic", "bank", "email", "address", "label"]}
    f["iban"], f["bic"] = f["iban"].replace(" ", "").upper(), f["bic"].replace(" ", "").upper()[:11]
    if len(f["name"]) < 2:
        return None, _("Name ist ein Pflichtfeld.")
    if not valid_iban(f["iban"]):
        return None, _("Ungültige IBAN")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", f["email"]):
        return None, _("Ungültige E-Mail-Adresse")
    return f, None


@app.route("/beneficiaries")
@login_required
def beneficiaries():
    q = request.args.get("q", "").strip()
    f = {"user_id": g.user["id"]}
    if q:
        f["name"] = {"$regex": re.escape(q), "$options": "i"}
    bens = list(db.beneficiaries.find(f, NOID).sort("name", 1))
    editing = request.args.get("edit") and own("beneficiaries", request.args["edit"])
    return render_template("beneficiaries.html", bens=bens, q=q, editing=editing)


@app.route("/beneficiaries/save", methods=["POST"])
@login_required
def ben_save():
    data, err = ben_from_form()
    if err:
        flash(err, "error")
        return back("beneficiaries")
    bid = request.form.get("id")
    if bid:
        own("beneficiaries", bid)
        db.beneficiaries.update_one({"id": bid}, {"$set": data})
    else:
        bid = uid()
        db.beneficiaries.insert_one({"id": bid, "user_id": g.user["id"], **data, "created_at": now().isoformat()})
    flash(_("Empfänger gespeichert"), "success")
    if request.form.get("next") == "transfer":
        return redirect(url_for("transfer", beneficiary_id=bid))
    return redirect(url_for("beneficiaries"))


@app.route("/beneficiaries/<bid>/delete", methods=["POST"])
@login_required
def ben_delete(bid):
    own("beneficiaries", bid)
    db.beneficiaries.delete_one({"id": bid})
    db.standing_orders.delete_many({"beneficiary_id": bid, "user_id": g.user["id"]})
    flash(_("Gelöscht"), "success")
    return redirect(url_for("beneficiaries"))


# ---------- Transfers ----------
class TransferError(Exception):
    pass


def execute_transfer(account, ben, amount, purpose, category="transfer"):
    lang = get_lang()
    if amount <= 0:
        raise TransferError(_("Bitte einen gültigen Betrag eingeben."))
    if account["balance"] < amount:
        raise TransferError(_("Nicht genügend Guthaben auf dem Konto."))
    day = now().date().isoformat()
    spent = list(db.transactions.aggregate([
        {"$match": {"user_id": g.user["id"], "category": {"$in": ["transfer", "standing"]}, "date": {"$gte": day}, "amount": {"$lt": 0}}},
        {"$group": {"_id": None, "s": {"$sum": "$amount"}}}]))
    if (-spent[0]["s"] if spent else 0) + amount > DAILY_TRANSFER_LIMIT:
        raise TransferError(_("Tageslimit von € 3.000 überschritten."))
    res = db.accounts.find_one_and_update({"id": account["id"], "balance": {"$gte": amount}}, {"$inc": {"balance": -amount}},
                                          projection=NOID, return_document=ReturnDocument.AFTER)
    if not res:
        raise TransferError(_("Nicht genügend Guthaben auf dem Konto."))
    db.accounts.update_one({"id": account["id"]}, {"$set": {"balance": round(res["balance"], 2)}})
    u = g.user
    tx = {
        "id": uid(), "user_id": u["id"], "account_id": account["id"], "amount": -amount, "counterparty": ben["name"],
        "purpose": purpose, "category": category, "date": now().isoformat(), "lang": lang,
        "reference": f"DNB{secrets.randbelow(9 * 10**9) + 10**9}",
        "beneficiary": {k: ben.get(k, "") for k in ["id", "name", "iban", "bic", "bank", "email", "address"]},
        "sender": {"name": u["name"], "address": u["address"], "zip": u["zip"], "city": u["city"], "iban": account["iban"], "bic": account["bic"]},
        "pdf_token": secrets.token_urlsafe(24), "pdf_expires": (now() + timedelta(days=30)).isoformat(),
    }
    pdf_url = url_for("receipt", token=tx["pdf_token"], _external=True)
    sent_today = db.transactions.count_documents({"user_id": u["id"], "email_status": "sent", "date": {"$gte": day}})
    if sent_today >= EMAIL_DAILY_LIMIT:
        status, email_id = "rate_limited", None
    else:
        status, email_id = send_confirmation(tx, tx["sender"], lang, receipt_pdf(tx, tx["sender"], lang), pdf_url,
                                              url_for("static", filename="logo-email.png", _external=True) if HAS_EMAIL_LOGO else None)
    tx.update(email_status=status, email_id=email_id)
    db.transactions.insert_one(tx)
    notify("transfer_done", {"amount": amount, "name": ben["name"]})
    notify("email_sent" if status == "sent" else "email_failed", {"name": ben["name"], "email": ben["email"]})
    return tx


@app.route("/transfer", methods=["GET", "POST"])
@login_required
def transfer():
    accounts = list(db.accounts.find({"user_id": g.user["id"], "type": "checking"}, NOID))
    bens = list(db.beneficiaries.find({"user_id": g.user["id"]}, NOID).sort("name", 1))
    orders = list(db.standing_orders.find({"user_id": g.user["id"]}, NOID).sort("next_date", 1))
    form = {**request.args, **request.form}

    def page():
        return render_template("transfer.html", accounts=accounts, bens=bens, orders=orders, form=form, ben_map={b["id"]: b["name"] for b in bens})

    if request.method == "POST":
        account, ben = own("accounts", form.get("account_id")), own("beneficiaries", form.get("beneficiary_id"))
        if account["type"] != "checking":
            abort(400)
        amount, purpose = to_float(form.get("amount")), form.get("purpose", "").strip()[:140]
        if amount <= 0 or not purpose:
            flash(_("Bitte Betrag und Verwendungszweck angeben."), "error")
            return page()
        if form.get("step") == "edit":
            return page()
        if form.get("step") == "confirm":
            try:
                tx = execute_transfer(account, ben, amount, purpose)
            except TransferError as e:
                flash(str(e), "error")
                return page()
            return redirect(url_for("transfer_done", tx_id=tx["id"]))
        return render_template("transfer_review.html", account=account, ben=ben, tx_amount=amount, purpose=purpose)
    return page()


@app.route("/transfer/done/<tx_id>")
@login_required
def transfer_done(tx_id):
    tx = own("transactions", tx_id)
    return render_template("transfer_done.html", tx=tx, account=own("accounts", tx["account_id"]))


@app.route("/receipts/<token>")
def receipt(token):
    tx = db.transactions.find_one({"pdf_token": token}, NOID)
    if not tx or tx["pdf_expires"] < now().isoformat():
        abort(404)
    resp = make_response(receipt_pdf(tx, tx["sender"], tx.get("lang", "de")))
    resp.headers.update({"Content-Type": "application/pdf", "Content-Disposition": f'inline; filename="{tx["reference"]}.pdf"'})
    return resp


# ---------- Standing orders ----------
def advance(d, interval):
    dt = datetime.fromisoformat(d)
    if interval == "weekly":
        return (dt + timedelta(days=7)).date().isoformat()
    return dt.replace(year=dt.year + (dt.month == 12), month=dt.month % 12 + 1, day=min(dt.day, 28)).date().isoformat()


def run_order(o):
    tx = execute_transfer(own("accounts", o["account_id"]), own("beneficiaries", o["beneficiary_id"]), o["amount"], o["purpose"], "standing")
    db.standing_orders.update_one({"id": o["id"]}, {"$set": {"next_date": advance(o["next_date"], o["interval"])}})
    return tx


def run_due_standing_orders():
    for o in db.standing_orders.find({"user_id": g.user["id"], "active": True, "next_date": {"$lte": now().date().isoformat()}}, NOID):
        try:
            run_order(o)
        except (TransferError, NotFound):
            pass


@app.route("/standing-orders/add", methods=["POST"])
@login_required
def order_add():
    f = request.form
    own("accounts", f.get("account_id"))
    own("beneficiaries", f.get("beneficiary_id"))
    amount = to_float(f.get("amount"))
    if not (0 < amount <= DAILY_TRANSFER_LIMIT) or not f.get("purpose") or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", f.get("next_date", "")):
        flash(_("Bitte alle Felder korrekt ausfüllen."), "error")
    else:
        db.standing_orders.insert_one({"id": uid(), "user_id": g.user["id"], "account_id": f["account_id"], "beneficiary_id": f["beneficiary_id"], "amount": amount,
                                       "purpose": f["purpose"][:140], "interval": "weekly" if f.get("interval") == "weekly" else "monthly", "next_date": f["next_date"], "active": True})
        flash(_("Dauerauftrag angelegt"), "success")
    return redirect(url_for("transfer") + "#standing")


@app.route("/standing-orders/<oid>/<action>", methods=["POST"])
@login_required
def order_action(oid, action):
    o = own("standing_orders", oid)
    if action == "toggle":
        db.standing_orders.update_one({"id": oid}, {"$set": {"active": not o["active"]}})
    elif action == "delete":
        db.standing_orders.delete_one({"id": oid})
        flash(_("Gelöscht"), "success")
    elif action == "execute":
        try:
            return redirect(url_for("transfer_done", tx_id=run_order(o)["id"]))
        except TransferError as e:
            flash(str(e), "error")
    return redirect(url_for("transfer") + "#standing")


# ---------- Cards ----------
@app.route("/cards", methods=["GET", "POST"])
@login_required
def cards():
    if request.method == "POST":
        card = own("cards", request.form.get("card_id"))
        action = request.form.get("action")
        if action == "block":
            db.cards.update_one({"id": card["id"]}, {"$set": {"blocked": not card["blocked"]}})
            notify("card_unblocked" if card["blocked"] else "card_blocked", {"last4": card["last4"]})
            flash(_("Karte entsperrt") if card["blocked"] else _("Karte gesperrt"), "success")
        elif action == "non_eu":
            db.cards.update_one({"id": card["id"]}, {"$set": {"non_eu": not card["non_eu"]}})
            flash(_("Aktualisiert"), "success")
        elif action == "limit":
            limit = int(to_float(request.form.get("limit_daily")))
            if 50 <= limit <= 5000:
                db.cards.update_one({"id": card["id"]}, {"$set": {"limit_daily": limit}})
                flash(_("Aktualisiert"), "success")
            else:
                flash(_("Limit muss zwischen 50 und 5.000 liegen."), "error")
        return redirect(url_for("cards"))
    return render_template("cards.html", cards=list(db.cards.find({"user_id": g.user["id"]}, NOID)))


# ---------- Direct debits ----------
@app.route("/debits", methods=["GET", "POST"])
@login_required
def debits():
    if request.method == "POST":
        d = own("direct_debits", request.form.get("debit_id"))
        status = request.form.get("status")
        if d["status"] != "revoked" and status in ("active", "suspended", "revoked"):
            db.direct_debits.update_one({"id": d["id"]}, {"$set": {"status": status}})
            flash(_("Aktualisiert"), "success")
        return redirect(url_for("debits"))
    return render_template("debits.html", debits=list(db.direct_debits.find({"user_id": g.user["id"]}, NOID)))


# ---------- Savings ----------
@app.route("/savings", methods=["GET", "POST"])
@login_required
def savings():
    if request.method == "POST":
        sav = own("accounts", request.form.get("savings_id"))
        if request.form.get("action") == "goal":
            amt = to_float(request.form.get("goal_amount"))
            name = request.form.get("goal_name", "").strip()[:40]
            if amt > 0 and name:
                db.accounts.update_one({"id": sav["id"]}, {"$set": {"goal_name": name, "goal_amount": amt}})
                flash(_("Gespeichert"), "success")
            return redirect(url_for("savings"))
        giro = db.accounts.find_one({"user_id": g.user["id"], "type": "checking"}, NOID)
        deposit = request.form.get("action") == "deposit"
        src, dst = (giro, sav) if deposit else (sav, giro)
        amt = to_float(request.form.get("amount"))
        if sav["type"] != "savings" or amt <= 0 or src["balance"] < amt:
            flash(_("Nicht genügend Guthaben auf dem Konto.") if amt > 0 else _("Bitte einen gültigen Betrag eingeben."), "error")
            return redirect(url_for("savings"))
        if not db.accounts.find_one_and_update({"id": src["id"], "balance": {"$gte": amt}}, {"$inc": {"balance": -amt}}):
            flash(_("Nicht genügend Guthaben auf dem Konto."), "error")
            return redirect(url_for("savings"))
        db.accounts.update_one({"id": dst["id"]}, {"$inc": {"balance": amt}})
        ts = now().isoformat()
        for acc, other, sign in [(src, dst, -1), (dst, src, 1)]:
            db.transactions.insert_one({"id": uid(), "user_id": g.user["id"], "account_id": acc["id"], "amount": sign * amt, "counterparty": other["name"],
                                        "purpose": f"{src['name']} → {dst['name']}", "category": "savings", "date": ts, "reference": f"DNB{secrets.randbelow(9 * 10**9) + 10**9}"})
        notify("savings_moved", {"amount": amt, "name": sav["name"], "direction": "deposit" if deposit else "withdraw"})
        flash(_("Umbuchung durchgeführt"), "success")
        return redirect(url_for("savings"))
    accs = list(db.accounts.find({"user_id": g.user["id"]}, NOID))
    return render_template("savings.html", savings=[a for a in accs if a["type"] == "savings"], giro=next(a for a in accs if a["type"] == "checking"))


# ---------- Credit ----------
def annuity(amount, months, rate):
    r = rate / 1200
    return round(amount * r / (1 - (1 + r) ** -months), 2) if r else round(amount / months, 2)


@app.route("/credit", methods=["GET", "POST"])
@login_required
def credit():
    if request.method == "POST":
        amount, months, rate = to_float(request.form.get("amount")), int(to_float(request.form.get("months"))), to_float(request.form.get("rate"))
        purpose = request.form.get("purpose", "").strip()[:80]
        if not (1000 <= amount <= 500000 and 6 <= months <= 360 and 0 < rate <= 20 and purpose):
            flash(_("Bitte alle Felder korrekt ausfüllen."), "error")
        else:
            db.loan_applications.insert_one({"id": uid(), "user_id": g.user["id"], "amount": amount, "months": months, "rate": rate, "purpose": purpose,
                                             "monthly": annuity(amount, months, rate), "status": "in_review", "date": now().isoformat()})
            notify("loan_applied", {"amount": amount})
            flash(_("Kreditanfrage eingereicht"), "success")
        return redirect(url_for("credit"))
    return render_template("credit.html", loans=list(db.loans.find({"user_id": g.user["id"]}, NOID)),
                           apps=list(db.loan_applications.find({"user_id": g.user["id"]}, NOID).sort("date", -1)))


# ---------- Notifications ----------
@app.route("/notifications", methods=["GET", "POST"])
@login_required
def notifications():
    if request.method == "POST":
        nid = request.form.get("id")
        db.notifications.update_many({"user_id": g.user["id"], **({"id": nid} if nid else {})}, {"$set": {"read": True}})
        return redirect(url_for("notifications"))
    return render_template("notifications.html", notes=list(db.notifications.find({"user_id": g.user["id"]}, NOID).sort("date", -1)))


# ---------- Statements ----------
@app.route("/statements")
@login_required
def statements():
    a = request.args
    f = {"user_id": g.user["id"]}
    if a.get("q"):
        rx = {"$regex": re.escape(a["q"]), "$options": "i"}
        f["$or"] = [{"counterparty": rx}, {"purpose": rx}, {"reference": rx}]
    t = a.get("type", "")
    if t == "in":
        f["amount"] = {"$gt": 0}
    elif t == "out":
        f["amount"] = {"$lt": 0}
    elif t:
        f["category"] = t
    if a.get("date_from") or a.get("date_to"):
        f["date"] = {**({"$gte": a["date_from"]} if a.get("date_from") else {}), **({"$lte": a["date_to"] + "T23:59:59"} if a.get("date_to") else {})}
    if a.get("account_id"):
        f["account_id"] = a["account_id"]
    lo, hi = to_float(a.get("min")) if a.get("min") else None, to_float(a.get("max")) if a.get("max") else None
    rows = [r for r in db.transactions.find(f, NOID).sort("date", -1).limit(1000)
            if (lo is None or abs(r["amount"]) >= lo) and (hi is None or abs(r["amount"]) <= hi)]
    months = sorted({d[:7] for d in db.transactions.distinct("date", {"user_id": g.user["id"]})}, reverse=True)
    accounts = list(db.accounts.find({"user_id": g.user["id"]}, NOID))
    return render_template("statements.html", rows=rows, months=months, accounts=accounts, a=a)


@app.route("/statements/<month>.pdf")
@login_required
def statement(month):
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        abort(404)
    acc = own("accounts", request.args["account_id"]) if request.args.get("account_id") else db.accounts.find_one({"user_id": g.user["id"], "type": "checking"}, NOID)
    txs = list(db.transactions.find({"account_id": acc["id"], "date": {"$regex": f"^{month}"}}, NOID).sort("date", 1))
    later = db.transactions.find({"account_id": acc["id"], "date": {"$gt": f"{month}-31T23:59:59"}}, NOID)
    closing = round(acc["balance"] - sum(x["amount"] for x in later), 2)
    resp = make_response(statement_pdf(g.user, acc, txs, month, closing, get_lang()))
    resp.headers.update({"Content-Type": "application/pdf", "Content-Disposition": f'attachment; filename="Danubia-{month}.pdf"'})
    return resp


if __name__ == "__main__":
    app.run(debug=True)
