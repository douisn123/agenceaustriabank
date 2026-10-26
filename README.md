# UniCredit Bank Austria – Wir erledigen lhre Bankgeschafte (Flask)

Démo fictive de banque en ligne (DE-AT / NL). Aucune donnée réelle, aucun argent réel.

## Structure
```
app.py              routes Flask (connexion, virements, cartes, épargne, crédit, relevés…)
docs.py             PDF (reportlab) + email de confirmation (Resend, PDF joint)
seed.py             compte de démo prérempli
templates/          vues Jinja2
static/style.css
babel.cfg           config d'extraction Babel
messages.pot        catalogue source (msgids en allemand)
translations/       de/ et nl/ (.po + .mo compilés) ; fill_nl.py = dictionnaire NL
brand.py            logo dessiné en vectoriel dans les PDF
static/logo-mark.png  logo (site + favicon) ; logo-email.png = en-tête des emails
static/fonts/       Plus Jakarta Sans (OFL) pour les PDF
tools/make_logo.py  régénère les PNG du logo depuis le SVG (Chrome headless)
api/index.py        point d'entrée Vercel
vercel.json         redirige toutes les routes vers api/index
requirements.txt
.env.example
```

## Lancer en local
```bash
pip install -r requirements.txt
cp .env.example .env    # remplir SECRET_KEY, RESEND_API_KEY, EMAIL_FROM
flask --app app run --debug
```
Connexion démo : `990303` / `0275`

## Traductions
```bash
pybabel extract -F babel.cfg -k _ -k gettext -o messages.pot .
pybabel update -i messages.pot -d translations
python translations/fill_nl.py        # remplit le néerlandais depuis le dictionnaire
pybabel compile -d translations       # commiter les .mo (Vercel ne compile pas)
```

## Déployer sur Vercel
1. Pousser ce dossier comme racine du projet Vercel.
2. Dans *Settings → Environment Variables* : `SECRET_KEY`, `RESEND_API_KEY`, `EMAIL_FROM`, `EMAIL_DAILY_LIMIT`.
3. `vercel --prod`.

`EMAIL_FROM` doit utiliser un domaine vérifié dans Resend ; sinon Resend n'envoie qu'à l'adresse du titulaire du compte.

## Base de données
Aucune installation : les données sont dans un fichier SQLite `danubia.db` (créé automatiquement à côté de `app.py`, voir `minidb.py`).
Sur Vercel, le fichier est écrit dans `/tmp` : les données de démo repartent de zéro quand Vercel redémarre l'application.
