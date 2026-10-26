"""Fills translations/nl/LC_MESSAGES/messages.po from this dictionary (German source -> Dutch)."""
from babel.messages.pofile import read_po, write_po

NL = {
    "Überweisung": "Overschrijving", "Dauerauftrag": "Periodieke opdracht", "Kartenzahlung": "Kaartbetaling", "Lastschrift": "Incasso",
    "Gehalt": "Salaris", "Umbuchung": "Overboeking", "Kreditrate": "Kredietaflossing",
    "Überweisung über %(amount)s an %(name)s durchgeführt.": "Overschrijving van %(amount)s naar %(name)s uitgevoerd.",
    "Bestätigung an %(name)s (%(email)s) gesendet.": "Bevestiging verzonden naar %(name)s (%(email)s).",
    "Bestätigung an %(name)s konnte nicht gesendet werden.": "Bevestiging naar %(name)s kon niet worden verzonden.",
    "Karte ****%(last4)s bei %(merchant)s verwendet: %(amount)s.": "Kaart ****%(last4)s gebruikt bij %(merchant)s: %(amount)s.",
    "Nächste Rate %(name)s: %(amount)s wird in Kürze fällig.": "Volgende termijn %(name)s: %(amount)s vervalt binnenkort.",
    "Gehaltseingang: %(amount)s.": "Salaris ontvangen: %(amount)s.",
    "Karte ****%(last4)s wurde gesperrt.": "Kaart ****%(last4)s is geblokkeerd.",
    "Karte ****%(last4)s wurde entsperrt.": "Kaart ****%(last4)s is gedeblokkeerd.",
    "%(amount)s auf %(name)s umgebucht.": "%(amount)s overgeboekt naar %(name)s.",
    "%(amount)s von %(name)s umgebucht.": "%(amount)s overgeboekt van %(name)s.",
    "Kreditanfrage über %(amount)s eingereicht.": "Kredietaanvraag van %(amount)s ingediend.",
    "Verfügernummer oder Passwort ist falsch.": "Klantnummer of wachtwoord is onjuist.",
    "Demo-Daten zurückgesetzt": "Demogegevens gereset", "Bitte alle Felder korrekt ausfüllen.": "Vul alle velden correct in.",
    "Gespeichert": "Opgeslagen", "Name ist ein Pflichtfeld.": "Naam is verplicht.", "Ungültige IBAN": "Ongeldige IBAN",
    "Ungültige E-Mail-Adresse": "Ongeldig e-mailadres", "Empfänger gespeichert": "Begunstigde opgeslagen", "Gelöscht": "Verwijderd",
    "Bitte einen gültigen Betrag eingeben.": "Voer een geldig bedrag in.", "Nicht genügend Guthaben auf dem Konto.": "Onvoldoende saldo op de rekening.",
    "Tageslimit von € 3.000 überschritten.": "Daglimiet van € 3.000 overschreden.", "Bitte Betrag und Verwendungszweck angeben.": "Vul bedrag en omschrijving in.",
    "Dauerauftrag angelegt": "Periodieke opdracht aangemaakt", "Karte entsperrt": "Kaart gedeblokkeerd", "Karte gesperrt": "Kaart geblokkeerd",
    "Aktualisiert": "Bijgewerkt", "Limit muss zwischen 50 und 5.000 liegen.": "Limiet moet tussen 50 en 5.000 liggen.",
    "Umbuchung durchgeführt": "Overboeking uitgevoerd", "Kreditanfrage eingereicht": "Kredietaanvraag ingediend",
    "Name": "Naam", "Bank": "Bank", "E-Mail": "E-mail", "Adresse": "Adres", "Bezeichnung (optional)": "Label (optioneel)", "Speichern": "Opslaan",
    "Online-Banking": "Online bankieren", "Demo – alle Daten sind fiktiv, es wird kein echtes Geld bewegt.": "Demo – alle gegevens zijn fictief, er wordt geen echt geld verplaatst.",
    "Demo zurücksetzen": "Demo resetten", "Übersicht": "Overzicht", "Empfänger": "Begunstigde", "Karten": "Kaarten", "Lastschriften": "Incasso's",
    "Sparen": "Sparen", "Kredit": "Krediet", "Umsätze & Auszüge": "Transacties & afschriften", "Mitteilungen": "Meldingen", "Meine Daten": "Mijn gegevens",
    "Abmelden": "Uitloggen", "IBAN kopiert": "IBAN gekopieerd", "Verwalten Sie Ihre gespeicherten Zahlungsempfänger.": "Beheer uw opgeslagen begunstigden.",
    "Suchen…": "Zoeken…", "Überweisen": "Overschrijven", "Bearbeiten": "Bewerken", "Empfänger wirklich löschen?": "Begunstigde echt verwijderen?",
    "Löschen": "Verwijderen", "Noch keine Empfänger.": "Nog geen begunstigden.", "Empfänger bearbeiten": "Begunstigde bewerken",
    "Empfänger hinzufügen": "Begunstigde toevoegen", "Abbrechen": "Annuleren", "Limits, Sperre und Auslandseinsatz verwalten.": "Limieten, blokkering en gebruik in het buitenland beheren.",
    "Gültig bis": "Geldig tot", "Gesperrt": "Geblokkeerd", "Tageslimit": "Daglimiet", "Monatslimit": "Maandlimiet",
    "Zahlungen außerhalb Europas": "Betalingen buiten Europa", "Karte entsperren": "Kaart deblokkeren", "Karte sperren": "Kaart blokkeren",
    "Laufende Kredite, Rechner und Kreditanfrage.": "Lopende kredieten, rekenhulp en kredietaanvraag.", "Laufende Kredite": "Lopende kredieten",
    "Restschuld": "Openstaand", "Monatliche Rate": "Maandtermijn", "Laufzeitende": "Einddatum", "Kreditrechner": "Kredietcalculator", "Betrag": "Bedrag",
    "Laufzeit (Monate)": "Looptijd (maanden)", "Zinssatz p.a.": "Rente per jaar", "Zinsen gesamt": "Totale rente", "Gesamtkosten": "Totale kosten",
    "Verwendungszweck": "Omschrijving", "Kredit anfragen": "Krediet aanvragen", "Meine Anfragen": "Mijn aanvragen", "In Prüfung": "In behandeling",
    "Grüß Gott": "Goedendag", "Gesamtsaldo": "Totaal saldo", "Kontoauszüge": "Afschriften", "Ungelesene Mitteilungen": "Ongelezen meldingen",
    "Alle anzeigen": "Alles tonen", "Keine neuen Mitteilungen.": "Geen nieuwe meldingen.", "Meine Konten": "Mijn rekeningen", "Girokonto": "Betaalrekening",
    "Sparkonto": "Spaarrekening", "Letzte Umsätze": "Recente transacties", "Aktive SEPA-Lastschriftmandate.": "Actieve SEPA-incassomachtigingen.",
    "Aktiv": "Actief", "Ausgesetzt": "Opgeschort", "Widerrufen": "Ingetrokken", "Gläubiger-ID": "Incassant-ID", "Mandatsreferenz": "Machtigingskenmerk",
    "Letzter Betrag": "Laatste bedrag", "Aussetzen": "Opschorten", "Fortsetzen": "Hervatten", "Mandat endgültig widerrufen?": "Machtiging definitief intrekken?",
    "Anmelden": "Inloggen", "Banking an der Donau – klar, sicher, jederzeit.": "Bankieren aan de Donau – helder, veilig, altijd.",
    "Willkommen im Online-Banking": "Welkom bij Online Bankieren", "Melden Sie sich mit Ihrer Verfügernummer an.": "Log in met uw klantnummer.",
    "Verfügernummer": "Klantnummer", "Passwort": "Wachtwoord", "Demo-Zugang": "Demo-toegang", "Alle als gelesen markieren": "Alles als gelezen markeren",
    "Neu": "Nieuw", "Gelesen": "Gelezen", "Diese Angaben erscheinen als Auftraggeber in Ihren Überweisungsbestätigungen.": "Deze gegevens verschijnen als opdrachtgever in uw overschrijvingsbevestigingen.",
    "PLZ": "Postcode", "Ort": "Plaats", "Telefon": "Telefoon", "Bankverbindung": "Bankgegevens", "IBAN kopieren": "IBAN kopiëren",
    "Zinsen, Sparziele und Umbuchungen.": "Rente, spaardoelen en overboekingen.", "Zinssatz": "Rente", "Sparziel": "Spaardoel", "erreicht": "bereikt",
    "von": "van", "Einzahlen": "Storten", "Abheben": "Opnemen", "Ziel ändern": "Doel wijzigen", "Name des Ziels": "Naam van het doel", "Zielbetrag": "Doelbedrag",
    "Umsätze & Kontoauszüge": "Transacties & afschriften", "Durchsuchen, filtern und als PDF herunterladen.": "Zoeken, filteren en als pdf downloaden.",
    "Art": "Soort", "Alle": "Alle", "Eingänge": "Inkomend", "Ausgänge": "Uitgaand", "Von": "Van", "Bis": "Tot", "Betrag min.": "Bedrag min.",
    "Betrag max.": "Bedrag max.", "Filtern": "Filteren", "Filter zurücksetzen": "Filters wissen", "Keine Umsätze gefunden.": "Geen transacties gevonden.",
    "Monatliche Kontoauszüge": "Maandelijkse afschriften", "SEPA-Überweisung an einen gespeicherten Empfänger.": "SEPA-overschrijving naar een opgeslagen begunstigde.",
    "Tageslimit: € 3.000": "Daglimiet: € 3.000", "Auftraggeberkonto": "Van rekening", "Empfänger wählen": "Kies begunstigde", "Weiter": "Verder",
    "Neuer Empfänger": "Nieuwe begunstigde", "Daueraufträge": "Periodieke opdrachten", "Monatlich": "Maandelijks", "Wöchentlich": "Wekelijks",
    "Nächste Ausführung": "Volgende uitvoering", "Pausiert": "Gepauzeerd", "Jetzt ausführen": "Nu uitvoeren", "Pausieren": "Pauzeren",
    "Keine Daueraufträge.": "Geen periodieke opdrachten.", "Dauerauftrag anlegen": "Periodieke opdracht aanmaken", "Anlegen": "Aanmaken",
    "Überweisung durchgeführt": "Overschrijving uitgevoerd", "Referenz": "Referentie", "Datum": "Datum", "Neuer Kontostand": "Nieuw saldo",
    "Bestätigung per E-Mail gesendet an": "Bevestiging per e-mail verzonden naar", "E-Mail-Versand ist noch nicht eingerichtet.": "E-mailverzending is nog niet ingesteld.",
    "Tageslimit für E-Mails erreicht.": "Daglimiet voor e-mails bereikt.", "E-Mail-Bestätigung konnte nicht gesendet werden.": "E-mailbevestiging kon niet worden verzonden.",
    "PDF herunterladen": "Pdf downloaden", "Neue Überweisung": "Nieuwe overschrijving", "Überweisung prüfen": "Overschrijving controleren",
    "Jetzt überweisen": "Nu overschrijven", "Zurück": "Terug",
}

if __name__ == "__main__":
    path = "translations/nl/LC_MESSAGES/messages.po"
    with open(path, "rb") as f:
        cat = read_po(f, locale="nl")
    missing = []
    for m in cat:
        if m.id:
            m.string = NL.get(m.id, m.string)
            m.flags.discard("fuzzy")
            if not m.string:
                missing.append(m.id)
    with open(path, "wb") as f:
        write_po(f, cat)
    print("missing:", missing)
