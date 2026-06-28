# Barms Global — Construction Financial Tracker

A secure, multi-page financial management system built for an active **military barracks construction project** in Nigeria. Designed to replace manual tracking with a real-time, cloud-hosted platform that gives project leadership full visibility into expenditure across units, build stages, and cost categories.

> **Status: Live and in active production use by a 2-person project team.**

---

## The Problem

Large-scale construction projects generate hundreds of transactions across multiple cost categories, site units, and build phases. Without a centralised system, tracking becomes fragmented — spreadsheets get out of sync, errors are hard to trace, and leadership has no real-time view of where the budget stands.

This system solves that.

---

## What It Does

### 📊 Executive Dashboard
- Real-time KPI cards: Total Funding, Total Expenses, Current Balance
- Interactive donut chart — expense breakdown by category
- Daily spend bar chart for the last 7 days
- Full ledger view with Excel export

### 📝 Data Entry
- Validated transaction form with date, build stage, category, unit, amount, and description
- Auto-derives transaction type (credit vs. debit) based on category to eliminate data entry errors
- Clears on submission to prevent duplicate entries

### 🗂️ Manage Records
- View recent transactions with full context
- Confirmation-gated deletion flow — prevents accidental record loss
- Re-enter corrected records via the Data Entry module

### 🔍 Data Explorer
- Multi-dimensional filtering: category, build stage, unit, transaction type, and date range
- Dynamic bar chart that regroups based on the active filter dimension
- KPI summary for filtered results
- Export filtered view to Excel

---

## Architecture

```
barms_global/
├── app/
│   ├── app.py            # Streamlit UI — all page rendering and navigation
│   └── data_access.py    # Database layer — strictly decoupled from UI
├── sql/
│   └── schema.sql        # PostgreSQL schema
├── requirements.txt
└── .gitignore
```

**Key design decision:** Database operations are fully decoupled into `data_access.py`. The UI layer (`app.py`) never writes raw SQL — it calls typed functions from the data access module. This separation makes the codebase easier to test, maintain, and extend.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Charts | Plotly Express |
| Backend / Logic | Python |
| Database | PostgreSQL (hosted on Neon) |
| ORM / Queries | SQLAlchemy |
| Authentication | streamlit-authenticator (JWT-based) |
| Data Processing | Pandas |
| Excel Export | openpyxl |

---

## Data Model

Transactions are tracked across five dimensions:

- **Category** — Labour, Transport & Fuel, Professional Fees, Accommodation, Public Relation, Plumbing, Electrical, Funding, Miscellaneous
- **Build Stage** — Foundation, Substructure, Superstructure, Roofing, Finishing, External Works
- **Unit** — CBQ1, CBQ2, CBQ19, CBQ20, CBQ21, Shared
- **Transaction Type** — Debit (Expense) or Credit (Funding)
- **Date** — Full date range filtering across all views

---

## Running Locally

```bash
# Clone the repo
git clone https://github.com/hxxisq/barms_global.git
cd barms_global

# Install dependencies
pip install -r requirements.txt

# Add your database connection string
# Create a .env file or set DATABASE_URL in your environment

# Run the app
streamlit run app/app.py
```

> You will need a PostgreSQL database (local or cloud). The schema is in `sql/schema.sql`.

---

## Key Engineering Decisions

**Authentication before anything else.** The app halts completely if credentials fail or are missing — no partial access, no unauthenticated views.

**Confirmation-gated deletion.** Deleting a record requires a two-step confirmation. This protects against accidental data loss in a production environment where records represent real financial transactions.

**Decoupled data access.** All database reads and writes go through `data_access.py`. This means the UI can be redesigned or the database swapped without touching business logic.

**Excel export on every data view.** Non-technical stakeholders can extract data directly without needing database access or coding knowledge — a deliberate design choice for a team with mixed technical backgrounds.

---

## Author

**Benjamin Shado**  
[LinkedIn](https://linkedin.com/in/benjaminshado) · [GitHub](https://github.com/hxxisq) · benjamin.shado@gmail.com
