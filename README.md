# db theory project - Quick Setup

This project shows a small web UI and some backend code that talks to a database.

Languages used
- Python — backend and tests (`server.py`, `api_test.py`, `test_system.py`)
- JavaScript — frontend logic (`index.js`)
- HTML — UI (`index.html`)
- CSS — styles (`index.css`)
- SQL — schema and example queries (`schema_postgres.sql`, `schema_sqlite.sql`, `queries.sql`)

Quick local setup (assumes you have Python 3.11 installed)

1. Create and activate a virtual environment (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install test dependencies (if any). If you don't have a `requirements.txt`, skip this step.

```powershell
pip install -r requirements.txt
```

3. Set up a local database (quick options):
- SQLite: run `schema_sqlite.sql` using `sqlite3` or a GUI tool.
- Postgres: create a DB and run `schema_postgres.sql` using `psql`.

4. Run the server (if `server.py` is an entrypoint):

```powershell
python server.py
```

5. Open the UI: visit `http://localhost:8000/` (or the URL shown in the server logs).

Notes about the database logic (simple):
- Look at `schema_*.sql` to see tables and relationships.
- Look at `queries.sql` for example SELECT/INSERT/UPDATE statements.
- `server.py` shows how the app runs queries and returns results to the frontend.

Simple checks to run
- Run unit tests: `python -m pytest` (if tests exist and pytest is installed).
- Test queries from `queries.sql` in your local DB and check results.
- Use `EXPLAIN` on slow queries to see why they're slow.

If you want, I can:
- Add a `requirements.txt` with needed Python packages.
- Add a small script to load sample data into the DB.
- Create a short page describing each SQL file in this repo.
