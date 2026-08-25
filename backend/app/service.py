import csv
import io
import json
import uuid
from datetime import UTC, datetime
from .config import ALLOWED_COLUMNS
from .database import connection, initialise_database
from .validation import parse_csv, validate_rows


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


def process_job(job_id: str, content: bytes) -> None:
    with connection() as db:
        db.execute("UPDATE import_jobs SET status = 'processing' WHERE id = ?", (job_id,))
    try:
        rows = parse_csv(content)
        results, duplicates = validate_rows(job_id, rows)
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
