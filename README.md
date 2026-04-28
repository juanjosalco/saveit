# SaveIt — Personal Finance Dashboard

Fully local web app to upload PDF statements, categorize transactions, and visualize spending.

## Supported Statements (Phase 1)
- **American Express** (Gold/Personal cards)
- **Chase** (credit cards)

Phase 2: Santander (Mexico) via Azure Document Intelligence — not yet implemented.

## Architecture
- **Backend**: FastAPI + SQLAlchemy + SQLite (data lives in `~/.finapp/finapp.db`)
- **Frontend**: React + Vite + TypeScript + Tailwind + TanStack Query + Recharts
- **PDF parsing**: `pypdf`, per-issuer parsers with auto-detection
- **Categorization**: rule-based with priority ordering + per-transaction manual override
- 100% local. No telemetry. No auth (single-user, localhost-only).

## Quick start

### One-time install
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cd ../frontend
npm install
```

### Run (two terminals)
```bash
# Terminal 1 — backend on :8000
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload

# Terminal 2 — frontend on :5173
cd frontend && npm run dev
```

Open http://localhost:5173

### Or use the Makefile
```bash
make dev    # runs both via foreman-style process
```

## Usage
1. Go to **Upload**, drag in PDF statements (one or many).
2. Open **Dashboard** for charts.
3. Use **Transactions** to filter and override categories per transaction.
4. Manage matching rules under **Rules** — click *Re-run* to recategorize existing transactions (manual overrides preserved).

## Data
- SQLite DB: `~/.finapp/finapp.db`
- Override location: set `FINAPP_DB_DIR=/some/path`
- Reset: `rm ~/.finapp/finapp.db` (data will be re-seeded on next start)

## Tests
```bash
cd backend && source .venv/bin/activate && pytest
```
Parser tests run against PDFs in `~/Downloads/` if present, otherwise skip.

## Roadmap
- **Phase 2**: Santander OCR via Azure Document Intelligence
- **Phase 3**: Budgets/alerts, MoM comparisons, generic CSV import, encrypted DB
