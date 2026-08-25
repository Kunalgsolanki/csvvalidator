import csv
import io
import json
import re
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from .config import ALLOWED_COLUMNS, REQUIRED_COLUMNS
from .database import connection, initialise_database

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9 .()\-]{6,19}$")


def now() -> str:
    return datetime.now(UTC).isoformat()


def job_dict(row):
    return dict(row)


JOB_COLUMNS = "id, filename, file_size, status, error_message, total_records, valid_records, invalid_records, duplicate_records, created_at, completed_at"


def create_job(filename: str, content: bytes) -> str:
    # FastAPI Cloud can attach a database between deployments. Ensure a newly
    # attached Neon database has the schema before accepting its first upload.
    initialise_database()
    job_id = str(uuid.uuid4())
    with connection() as db:
        db.execute("INSERT INTO import_jobs (id, filename, file_size, original_csv, status, created_at) VALUES (?, ?, ?, ?, 'pending', ?)", (job_id, filename, len(content), content, now()))
    return job_id


def get_job(job_id: str):
    with connection() as db:
        row = db.execute(f"SELECT {JOB_COLUMNS} FROM import_jobs WHERE id = ?", (job_id,)).fetchone()
    return job_dict(row) if row else None


def list_jobs():
    with connection() as db:
        rows = db.execute(f"SELECT {JOB_COLUMNS} FROM import_jobs ORDER BY created_at DESC").fetchall()
    return [job_dict(row) for row in rows]


def normalise(row: dict[str, str | None]) -> dict[str, str]:
    return {column: (row.get(column) or "").strip() for column in ALLOWED_COLUMNS}


def validate_csv(content: bytes) -> list[dict[str, str]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("The CSV must be UTF-8 encoded.") from exc
    if not text.strip():
        raise ValueError("The uploaded CSV is empty.")
    try:
        reader = csv.DictReader(io.StringIO(text))
        headers = [header.strip().lower() for header in (reader.fieldnames or [])]
        missing = sorted(set(REQUIRED_COLUMNS) - set(headers))
        if missing:
            raise ValueError(f"Missing required column(s): {', '.join(missing)}.")
        unexpected = set(headers) - set(ALLOWED_COLUMNS)
        if unexpected:
            raise ValueError(f"Unexpected column(s): {', '.join(sorted(unexpected))}.")
        rows = []
        for raw in reader:
            if None in raw:
                raise ValueError("A row contains more values than the header defines.")
            rows.append(normalise({key.strip().lower(): value for key, value in raw.items()}))
        return rows
    except csv.Error as exc:
        raise ValueError("The file contains malformed CSV data.") from exc


def process_job(job_id: str, content: bytes) -> None:
    with connection() as db:
        db.execute("UPDATE import_jobs SET status = 'processing' WHERE id = ?", (job_id,))
    try:
        rows = validate_csv(content)
        email_counts = Counter(row['email'].lower() for row in rows if row['email'])
        results = []
        duplicates = 0
        for index, row in enumerate(rows, start=2):
            reasons = []
            if not row['name']:
                reasons.append('Name is required.')
            if not row['email'] or not EMAIL_PATTERN.match(row['email']):
                reasons.append('Email address is invalid.')
            elif email_counts[row['email'].lower()] > 1:
                reasons.append('Email is duplicated in this file.')
                duplicates += 1
            if not row['phone'] or not PHONE_PATTERN.match(row['phone']):
                reasons.append('Phone number is invalid.')
            if not row['company']:
                reasons.append('Company is required.')
            # `is_valid` is stored as INTEGER so the same schema works in
            # SQLite and PostgreSQL. Psycopg does not implicitly cast bool to
            # integer, therefore pass the database representation explicitly.
            results.append((job_id, index, row['name'], row['email'], row['phone'], row['company'], row['city'], json.dumps(reasons), int(not reasons)))
        valid = sum(1 for result in results if result[-1])
        with connection() as db:
            db.executemany("""INSERT INTO import_records
              (job_id,row_number,name,email,phone,company,city,reasons,is_valid)
              VALUES (?,?,?,?,?,?,?,?,?)""", results)
            db.execute("""UPDATE import_jobs SET status='completed', total_records=?, valid_records=?, invalid_records=?, duplicate_records=?, completed_at=? WHERE id=?""", (len(results), valid, len(results) - valid, duplicates, now(), job_id))
    except Exception as exc:
        with connection() as db:
            db.execute("UPDATE import_jobs SET status='failed', error_message=?, completed_at=? WHERE id=?", (str(exc), now(), job_id))


def records_for_job(job_id: str, page: int, page_size: int, search: str, invalid_only: bool):
    conditions, params = ["job_id = ?"], [job_id]
    if invalid_only:
        conditions.append("is_valid = 0")
    if search:
        conditions.append("(name LIKE ? OR email LIKE ? OR company LIKE ? OR city LIKE ?)")
        needle = f"%{search}%"
        params.extend([needle] * 4)
    where = " AND ".join(conditions)
    with connection() as db:
        # SQLite rows and Psycopg's dict rows both support column-name access;
        # only SQLite supports the positional ``[0]`` form used previously.
        total = db.execute(f"SELECT COUNT(*) AS total FROM import_records WHERE {where}", params).fetchone()["total"]
        rows = db.execute(f"SELECT * FROM import_records WHERE {where} ORDER BY row_number LIMIT ? OFFSET ?", [*params, page_size, (page - 1) * page_size]).fetchall()
    return [{**dict(row), "reasons": json.loads(row['reasons']), "is_valid": bool(row['is_valid'])} for row in rows], total


def valid_csv(job_id: str) -> str:
    with connection() as db:
        rows = db.execute("SELECT name,email,phone,company,city FROM import_records WHERE job_id=? AND is_valid=1 ORDER BY row_number", (job_id,)).fetchall()
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=ALLOWED_COLUMNS)
    writer.writeheader()
    writer.writerows(map(dict, rows))
    return out.getvalue()


def original_csv(job_id: str) -> bytes | None:
    with connection() as db:
        row = db.execute("SELECT original_csv FROM import_jobs WHERE id = ?", (job_id,)).fetchone()
    if not row or row["original_csv"] is None:
        return None
    return bytes(row["original_csv"])
