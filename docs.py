import base64
import logging
import os
from html import escape
from io import BytesIO

import resend
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from brand import draw_logo

logger = logging.getLogger(__name__)
BRAND = "UniCredit Bank Austria"
NAVY = colors.HexColor("#0B192C")
GOLD = colors.HexColor("#D4AF37")

T = {
    "de": {
        "receipt": "Überweisungsbestätigung", "sender": "Auftraggeber", "recipient": "Empfänger",
        "amount": "Betrag", "purpose": "Verwendungszweck", "date": "Datum", "reference": "Referenz",
        "name": "Name", "address": "Adresse", "city": "Ort", "iban": "IBAN", "bic": "BIC", "bank": "Bank",
        "demo": "Demo-Dokument – kein echter Zahlungsverkehr. Erstellt von UniCredit Bank Austria (fiktiv).",
        "statement": "Kontoauszug", "account": "Konto", "period": "Zeitraum", "opening": "Anfangssaldo",
        "closing": "Endsaldo", "counterparty": "Gegenpartei", "none": "Keine Umsätze in diesem Zeitraum.",
        "subject": "Überweisungsbestätigung {ref} – {amount}",
        "hello": "Guten Tag {name},",
        "intro": "{sender} hat Ihnen über UniCredit Bank Austria eine Überweisung gesendet. Hier ist die Zusammenfassung:",
        "pdf_note": "Die Bestätigung ist als PDF angehängt.",
        "download": "PDF herunterladen",
        "footer": "Diese Nachricht wurde automatisch von UniCredit Bank Austria (Demo-Anwendung) versendet. Bitte antworten Sie nicht auf diese E-Mail. UniCredit Bank Austria fordert niemals vertrauliche Daten per E-Mail an.",
    },
    "nl": {
        "receipt": "Overschrijvingsbevestiging", "sender": "Opdrachtgever", "recipient": "Begunstigde",
        "amount": "Bedrag", "purpose": "Omschrijving", "date": "Datum", "reference": "Referentie",
        "name": "Naam", "address": "Adres", "city": "Plaats", "iban": "IBAN", "bic": "BIC", "bank": "Bank",
        "demo": "Demodocument – geen echt betalingsverkeer. Aangemaakt door UniCredit Bank Austria (fictief).",
        "statement": "Rekeningafschrift", "account": "Rekening", "period": "Periode", "opening": "Beginsaldo",
        "closing": "Eindsaldo", "counterparty": "Tegenpartij", "none": "Geen transacties in deze periode.",
        "subject": "Overschrijvingsbevestiging {ref} – {amount}",
        "hello": "Beste {name},",
        "intro": "{sender} heeft u via UniCredit Bank Austria een overschrijving gestuurd. Hier is het overzicht:",
        "pdf_note": "De bevestiging is als pdf bijgevoegd.",
        "download": "Pdf downloaden",
        "footer": "Dit bericht is automatisch verzonden door UniCredit Bank Austria(demo-applicatie). Beantwoord deze e-mail niet. UniCredit Bank Austriavraagt nooit vertrouwelijke gegevens per e-mail.",
    },
}


def tr(lang):
    return T.get(lang, T["de"])


def money(v, lang):
    s = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{'-' if v < 0 else ''}€ {s}" if lang == "de" else f"{'-' if v < 0 else ''}€ {s}"


def fdate(iso, lang):
    d = iso[:10].split("-")
    return f"{d[2]}.{d[1]}.{d[0]}" if lang == "de" else f"{d[2]}-{d[1]}-{d[0]}"


def _header(c, title):
    w, h = A4
    c.setFillColor(NAVY)
    c.rect(0, h - 90, w, 90, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.rect(0, h - 94, w, 4, fill=1, stroke=0)
    draw_logo(c, 40, h - 67, 44, light=True)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 11)
    c.drawRightString(w - 40, h - 52, title)
    return h - 130


def _footer(c, t):
    c.setFillColor(colors.grey)
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(40, 30, t["demo"])


def receipt_pdf(tx, sender, lang):
    t = tr(lang)
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"{t['receipt']} {tx['reference']}")
    y = _header(c, t["receipt"])
    ben = tx["beneficiary"]

    def block(title, rows, y):
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, title)
        y -= 6
        c.setStrokeColor(GOLD)
        c.line(40, y, 555, y)
        y -= 18
        for label, val in rows:
            c.setFont("Helvetica", 9)
            c.setFillColor(colors.grey)
            c.drawString(40, y, label)
            c.setFont("Helvetica", 10)
            c.setFillColor(colors.black)
            c.drawString(170, y, str(val or "–"))
            y -= 16
        return y - 14

    y = block(t["sender"], [(t["name"], sender["name"]), (t["address"], sender["address"]),
                            (t["city"], f"{sender['zip']} {sender['city']}"), (t["iban"], sender["iban"]),
                            (t["bic"], sender["bic"])], y)
    y = block(t["recipient"], [(t["name"], ben["name"]), (t["iban"], ben["iban"]), (t["bic"], ben.get("bic")),
                               (t["bank"], ben.get("bank"))], y)
    y = block(t["receipt"], [(t["amount"], money(abs(tx["amount"]), lang)), (t["purpose"], tx["purpose"]),
                             (t["date"], fdate(tx["date"], lang)), (t["reference"], tx["reference"])], y)
    _footer(c, t)
    c.save()
    return buf.getvalue()


def statement_pdf(user, account, txs, month, closing, lang):
    t = tr(lang)
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    y = _header(c, f"{t['statement']} {month}")
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    for line in [user["name"], user["address"], f"{user['zip']} {user['city']}", "",
                 f"{t['account']}: {account['name']} · {account['iban']}", f"{t['period']}: {month}"]:
        c.drawString(40, y, line)
        y -= 14
    total = sum(x["amount"] for x in txs)
    y -= 10
    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, y, t["date"]); c.drawString(110, y, t["counterparty"]); c.drawString(300, y, t["purpose"])
    c.drawRightString(555, y, t["amount"])
    y -= 6
    c.setStrokeColor(GOLD); c.line(40, y, 555, y); y -= 14
    c.setFont("Helvetica", 9)
    if not txs:
        c.drawString(40, y, t["none"]); y -= 14
    for x in txs:
        if y < 80:
            _footer(c, t); c.showPage(); y = _header(c, f"{t['statement']} {month}"); c.setFont("Helvetica", 9)
        c.setFillColor(colors.black)
        c.drawString(40, y, fdate(x["date"], lang))
        c.drawString(110, y, (x.get("counterparty") or "")[:34])
        c.drawString(300, y, (x.get("purpose") or "")[:38])
        c.setFillColor(colors.HexColor("#16A34A") if x["amount"] > 0 else colors.HexColor("#DC2626"))
        c.drawRightString(555, y, money(x["amount"], lang))
        y -= 14
    y -= 10
    c.setFillColor(NAVY); c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, f"{t['opening']}: {money(closing - total, lang)}")
    c.drawRightString(555, y, f"{t['closing']}: {money(closing, lang)}")
    _footer(c, t)
    c.save()
    return buf.getvalue()


def _row(label, val):
    return (f'<tr><td style="padding:4px 12px 4px 0;color:#64748b;font-size:13px;vertical-align:top">{escape(label)}</td>'
            f'<td style="padding:4px 0;color:#0B192C;font-size:13px;font-weight:600">{escape(str(val or "–"))}</td></tr>')


def email_html(tx, sender, lang, pdf_url, logo_url=None):
    t = tr(lang)
    brand = BRAND
    if logo_url and logo_url.startswith("https://"):
        brand = (f'<img src="{escape(logo_url)}" width="170" height="48" alt="UniCredit Bank Austria" '
                 f'style="display:block;border:0;outline:none;width:170px;height:48px">')
    ben = tx["beneficiary"]
    rows = "".join([
        _row(t["sender"], sender["name"]), _row(t["address"], sender["address"]),
        _row(t["city"], f"{sender['zip']} {sender['city']}"), _row(t["iban"], sender["iban"]),
        _row(t["bic"], sender["bic"]), _row(t["amount"], money(abs(tx["amount"]), lang)),
        _row(t["purpose"], tx["purpose"]), _row(t["date"], fdate(tx["date"], lang)),
        _row(t["reference"], tx["reference"]),
    ])
    button = ""
    if pdf_url and pdf_url.startswith("https://"):
        button = (f'<p style="margin:24px 0"><a href="{escape(pdf_url)}" style="background:#0B192C;color:#ffffff;'
                  f'padding:12px 22px;border-radius:6px;text-decoration:none;font-weight:600;font-size:14px">'
                  f'{escape(t["download"])}</a></p>')
    return (
        '<table role="presentation" width="100%" style="background:#F8FAFC;padding:24px 0"><tr><td align="center">'
        '<table role="presentation" width="560" style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;font-family:Arial,sans-serif">'
        f'<tr><td style="background:#0B192C;padding:20px 28px;border-bottom:4px solid #D4AF37;color:#ffffff;font-size:20px;font-weight:700">{brand}</td></tr>'
        f'<tr><td style="padding:28px"><h2 style="margin:0 0 16px;color:#0B192C;font-size:18px">{escape(t["receipt"])}</h2>'
        f'<p style="color:#0B192C;font-size:14px">{escape(t["hello"].format(name=ben["name"]))}</p>'
        f'<p style="color:#0B192C;font-size:14px">{escape(t["intro"].format(sender=sender["name"]))}</p>'
        f'<table role="presentation" style="margin:12px 0">{rows}</table>'
        f'<p style="color:#0B192C;font-size:14px">{escape(t["pdf_note"])}</p>{button}'
        f'<p style="color:#94a3b8;font-size:11px;margin-top:28px">{escape(t["footer"])}</p></td></tr></table>'
        '</td></tr></table>'
    )

def send_confirmation(tx, sender, lang, pdf_bytes, pdf_url, logo_url=None):
    key = os.environ.get("RESEND_API_KEY")
    sender_addr = os.environ.get("EMAIL_FROM") or os.environ.get("MAIL_FROM")

    if not key or not sender_addr:
        return "not_configured", None

    t = tr(lang)
    resend.api_key = key

    logger.info(
        "Destinataire de la confirmation : %s",
        tx.get("beneficiary", {}).get("email")
    )

    params = {
        "from": sender_addr,
        "to": [tx["beneficiary"]["email"]],
        "subject": t["subject"].format(
            ref=tx["reference"],
            amount=money(abs(tx["amount"]), lang)
        ),
        "html": email_html(tx, sender, lang, pdf_url, logo_url),
        "attachments": [{
            "filename": f"{tx['reference']}.pdf",
            "content": base64.b64encode(pdf_bytes).decode()
        }],
    }

    try:
        res = resend.Emails.send(params)
        return "sent", res.get("id")
    except Exception as e:
        logger.error("Resend send failed for %s: %s", tx["reference"], e)
        return "failed", None
