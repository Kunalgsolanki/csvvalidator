# CSV Validator

A production-minded React + FastAPI CSV import dashboard created for the OnePrism assessment.

## Features

- Async import jobs with `pending`, `processing`, `completed`, and `failed` statuses
- SQLite-backed import and row history that persists browser refreshes
- Clear CSV, required-column, encoding, size, and malformed-row failure messages
- Per-row validation: name/company required, email and phone format, and duplicate email in the uploaded file
- Search, invalid-only filter, pagination, previous-import selection, and valid-record CSV download

## Run locally

Terminal 1:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Terminal 2:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Upload `sample-data/customers.csv` to see valid, invalid, and duplicate records.

The frontend uses `frontend/.env` for local API requests (`http://localhost:8000`) and `frontend/.env.production` for production builds (`https://csv-validators.fastapicloud.dev`). The backend accepts requests from the local Vite app and the deployed Vercel app; set `CORS_ORIGINS` as a comma-separated environment variable to add other frontend domains.

Additional test files are available in `sample-data/`: `valid-customers.csv`, `invalid-customers.csv`, `duplicate-emails.csv`, `missing-required-column.csv`, and `empty-file.csv`.

## API

- `POST /api/imports` - accepts a `file` multipart field and returns `202` with an import job
- `GET /api/imports` / `GET /api/imports/{id}` - import history/status
- `GET /api/imports/{id}/records` - supports `page`, `page_size`, `search`, and `invalid_only`
- `GET /api/imports/{id}/valid-records.csv` - download only valid records

## Assumptions and trade-offs

- `name`, `email`, `phone`, and `company` are required; `city` is optional. Extra columns are rejected to surface likely template mistakes early.
- CSV must be UTF-8 (BOM allowed), be at most 5 MB, and contain all values within the supplied header shape.
- A duplicate email invalidates every occurrence in the file; duplicates are case-insensitive.
- The API uses FastAPI background tasks. For long-running or high-volume production imports, move the worker to a durable queue and use PostgreSQL/object storage.
- CORS intentionally permits the Vite development origin only; configure allowed origins through environment-specific deployment settings.

## Neon / FastAPI Cloud deployment

The service uses SQLite locally by default. In FastAPI Cloud, attach a Neon database from the app's **Integrations** tab and keep the injected secret name as `DATABASE_URL`. When that value starts with `postgresql://`, the service automatically uses Neon PostgreSQL. The original upload is stored as `BYTEA` in the import-job record (the 5 MB upload limit keeps this practical for the assessment). Do not add the database URL to source control.

## Tests

From `backend`, run `pytest tests` after installing the API dependencies plus `pytest` and `httpx`.
