# ShopKeeper — Inventory & Billing Software for Local Shops

A lightweight, offline-friendly web application built for the CEP project
*"Inventory & Billing Software for Local Shops"* (TYIT Sem 5, 2026-27).

Designed for kirana stores and small shops that currently track stock and
billing on paper. Runs entirely on the shop's own PC — no internet required
after setup, no hosting cost, no accounting background needed.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Flask (REST-style routes) |
| Database | SQLite (file-based, zero setup) — swappable to MySQL/Postgres later |
| Frontend | HTML5, Bootstrap 5, vanilla JavaScript |
| Auth | Flask-Login, hashed passwords (Werkzeug) |
| Charts | Chart.js (sales trend visualization) |

> Note: the original synopsis listed Node.js/Express — this build uses
> Python/Flask instead, which covers the same REST API + template-rendering
> architecture but keeps the whole stack in one language for easier viva
> explanation and maintenance.

---

## Features

- **Product management** — add, edit, delete products with name, category,
  price, stock quantity, and unit (pcs/kg/ltr etc.)
- **Billing** — live product search, cart builder, discount % and tax %,
  automatic total calculation, real-time stock deduction, printable receipt
- **Low-stock alerts** — dashboard flags any product at or below its
  configurable threshold
- **Dashboard** — today's sales, this month's sales, 14-day sales chart,
  top-selling products
- **Bill history** — searchable by time range, with receipt reprint
- **Login system** — one owner account (created automatically on first run)
  plus optional staff accounts the owner can create/remove
- **Stock safety** — the server always recalculates prices and checks stock
  from the database, never trusts the browser, so billing can't oversell
  or be tampered with via dev tools

---

## Project Structure

```
shopkeeper/
├── run.py                     # entry point — run this to start the app
├── seed_demo_data.py          # optional: adds 10 sample products for demos
├── requirements.txt
├── instance/
│   └── shop.db                # SQLite database (created automatically)
└── app/
    ├── __init__.py             # app factory, config, extension setup
    ├── models.py                # User, Product, Bill, BillItem
    ├── routes/
    │   ├── auth.py               # login, logout, staff management
    │   ├── inventory.py          # product CRUD + live search API
    │   ├── billing.py            # cart -> bill, stock deduction, receipts
    │   └── dashboard.py          # summary stats + chart data API
    ├── templates/               # Jinja2 + Bootstrap HTML
    └── static/
        ├── css/style.css
        └── js/billing.js         # live cart logic
```

---

## Setup & Running

**1. Install Python 3.9+** if not already installed.

**2. Install dependencies:**
```bash
cd shopkeeper
pip install -r requirements.txt
```

**3. (Optional) Load sample products for a demo:**
```bash
python seed_demo_data.py
```

**4. Run the app:**
```bash
python run.py
```

**5. Open your browser to:** `http://127.0.0.1:5000`

On first run, you'll land on a **one-time setup page** to create the shop's
owner account — enter the shop name, choose a username and password. After
that, the setup page locks itself automatically and everyone logs in through
the normal login page. Staff accounts (if needed) are created afterwards by
the owner from the **Staff** page inside the app — there's no public signup,
so random visitors can never create their own login and see the shop's data.

---

## Demoing to Multiple Local Shops

Since this app is built as **one shop per installation** (matches the real
world — each shop runs its own copy on its own PC), you need a clean slate
before demoing to a *different* shop than the one you last tested with.

**Before demoing to a new/different shop:**
```bash
python reset_for_new_shop.py
```
Type `YES` when prompted. This safely **archives** (doesn't delete) the
current shop's data as a timestamped backup file in `instance/`, and resets
the app so the next signup becomes a fresh shop's owner — complete with the
"Welcome! Let's set up your shop" screen and shop-name field, exactly like a
true first-time install.

**You do NOT need this** for normal testing/demoing to the *same* shop
multiple times — only when moving to a genuinely different shop owner.

---



Per your synopsis's plan (interview → prototype → demo → feedback →
deploy + train):

1. **Interview stage** — use the low-stock threshold, unit field (pcs/kg/ltr),
   and category field to match what the specific shop actually sells.
2. **Demo stage** — `seed_demo_data.py` gives you a ready-made kirana-style
   catalog to demo instantly without manual data entry.
3. **Deploy stage** — copy the whole `shopkeeper/` folder to the shop's PC,
   run `pip install -r requirements.txt` once, then `python run.py`. The
   owner can pin a desktop shortcut to `run.py`, or you can set it to run at
   startup.
4. **Handover/training** — the interface is intentionally simple (search →
   click to add → generate bill → print), so a 10–15 minute walkthrough
   should be enough for someone unfamiliar with computers.

**Future scope you can mention in your report:** multi-branch support via
switching `DATABASE_URL` to MySQL/Postgres, barcode scanner integration,
WhatsApp receipt sharing, GST-compliant invoice formatting.

---

## Turning This Into Real, Launchable Software

Running `python run.py` from a terminal is fine for development, but a real
shop owner shouldn't need to open VS Code or type commands. There are two
levels of "productizing" this app, from quickest to most polished:

### Level 1 — One-click launcher (already done, works today)

- `run.py` now uses **Waitress** (a production-grade server) instead of
  Flask's development server — no more "do not use in production" warning.
- The shop owner's browser **opens automatically** when the program starts.
- Double-click **`Start ShopKeeper.bat`** instead of using a terminal at
  all — it sets up everything on first run (creates a virtual environment,
  installs requirements) and just runs the app on every run after that.
- You can right-click this `.bat` file → "Create shortcut", drag that
  shortcut to the Desktop, rename it to "ShopKeeper", and optionally give
  it a custom icon (right-click shortcut → Properties → Change Icon) —
  now it looks and feels like a real installed program.

**This still requires Python to be installed on the shop's PC** — the batch
file handles the rest, but Python itself needs to exist first.

### Level 2 — A true standalone `.exe` (no Python installation needed at all)

This bundles Python itself, every dependency, and your app into one
folder with a single `.exe` — the shop's PC doesn't need Python installed
at all. **This must be built ON a Windows PC** (a build tool like
PyInstaller packages for whatever OS it's currently running on — it can't
cross-build a Windows .exe from Mac/Linux).

```bash
# On your Windows PC, inside the shopkeeper folder, with your venv active:
pip install pyinstaller
pyinstaller ShopKeeper.spec
```

This produces `dist/ShopKeeper/ShopKeeper.exe`. Give the shop owner the
whole `dist/ShopKeeper/` folder (not just the .exe alone — it needs the
files alongside it), and a desktop shortcut to the `.exe` inside it.

**Important: test this yourself before the actual handover.** Specifically
check that:
1. Double-clicking the `.exe` opens the browser and the app works
2. Add a product, close the program, reopen it — **the product should
   still be there** (this confirms the database is saving to a stable
   folder next to the .exe, not getting wiped — see the `_get_instance_path()`
   function in `app/__init__.py` for how this is handled)

If you'd rather not deal with PyInstaller before your viva, **Level 1
alone is already a completely reasonable answer** if a teacher asks "how
would a shop owner actually use this" — a desktop shortcut that one-click
launches a real production server is a legitimate deployment, and you can
mention Level 2 (.exe packaging) as documented future-scope work.

---

## Getting a Real Public Link (for your teacher/report)

This is **separate** from the offline version above — this gives you an
actual internet URL like `https://shopkeeper-payal.onrender.com` that
works from anywhere, anytime, without your PC being on. Useful for your
report and for your teacher to try it themselves. The real shop deployment
still uses the offline version described earlier — these are two different
things for two different purposes.

**Honest limitation to know about:** on Render's free tier, the database
resets whenever the app restarts/redeploys (the free tier's storage isn't
permanent). That's completely fine for a demo link — just re-run
`seed_demo_data.py`-style setup (or sign up fresh) if it ever resets before
a demo. If you ever need it to never reset, that requires a paid persistent
disk — not necessary for a CEP demo link.

### Steps

1. **Push your project to GitHub** (if you haven't already):
   - Create a free account at github.com
   - Create a new repository (e.g. `shopkeeper`)
   - In your project folder: `git init`, `git add .`, `git commit -m "Initial commit"`, then follow GitHub's instructions to push

2. **Create a free Render account** at render.com (sign in with GitHub — no credit card needed for the free tier)

3. **New Web Service** → connect your `shopkeeper` GitHub repo

4. **Fill in these settings:**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn run:app` (already set up in the `Procfile`, Render usually detects this automatically)
   - **Instance Type:** Free

5. **Add an environment variable** (Render's dashboard → Environment):
   - `SECRET_KEY` = any random long string (don't use the default dev one for a public link)

6. Click **Deploy**. After a few minutes, Render gives you a live URL — that's your real, shareable link.

---

## Security Notes (for your report)

- Passwords are never stored in plain text (Werkzeug's `generate_password_hash`)
- All billing calculations happen server-side from the database — the
  client cannot fake a lower total or bypass stock checks
- Only the owner role can create/delete staff accounts
- Session-based auth via Flask-Login; login required on every page except
  the login screen itself
