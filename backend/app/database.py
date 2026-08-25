import sqlite3
from contextlib import contextmanager
from . import config


def using_postgres() -> bool:
    return bool(config.DATABASE_URL and config.DATABASE_URL.startswith(("postgres://", "postgresql://")))


class PostgresConnection:
    """Small compatibility wrapper so repositories use one parameter style locally and in Neon."""
    def __init__(self, raw):
        self.raw = raw

    def execute(self, query, params=()):
        return self.raw.execute(query.replace("?", "%s"), params)

    def executemany(self, query, params):
        # Psycopg 3 exposes ``executemany`` on a cursor, not on the
        # connection (unlike sqlite3). Keep the SQLite-like interface used by
        # the service layer while issuing the batch through a PostgreSQL cursor.
        with self.raw.cursor() as cursor:
            return cursor.executemany(query.replace("?", "%s"), params)

    def executescript(self, script):
        for statement in script.split(";"):
            if statement.strip():
                self.raw.execute(statement)

    def commit(self):
        self.raw.commit()

    def close(self):
        self.raw.close()


def initialise_database() -> None:
    with connection() as db:
        if not using_postgres():
            config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        id_column = "BIGSERIAL PRIMARY KEY" if using_postgres() else "INTEGER PRIMARY KEY AUTOINCREMENT"
        blob_column = "BYTEA" if using_postgres() else "BLOB"
        db.executescript(f"""
        CREATE TABLE IF NOT EXISTS import_jobs (
          id TEXT PRIMARY KEY, filename TEXT NOT NULL, file_size INTEGER NOT NULL,
          original_csv {blob_column},
          status TEXT NOT NULL, error_message TEXT, total_records INTEGER NOT NULL DEFAULT 0,
          valid_records INTEGER NOT NULL DEFAULT 0, invalid_records INTEGER NOT NULL DEFAULT 0,
          duplicate_records INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
          completed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS import_records (
          id {id_column}, job_id TEXT NOT NULL, row_number INTEGER NOT NULL,
          name TEXT, email TEXT, phone TEXT, company TEXT, city TEXT,
          reasons TEXT NOT NULL DEFAULT '[]', is_valid INTEGER NOT NULL,
          FOREIGN KEY(job_id) REFERENCES import_jobs(id)
        );
        CREATE INDEX IF NOT EXISTS idx_records_job_valid ON import_records(job_id, is_valid);
        CREATE INDEX IF NOT EXISTS idx_records_job_email ON import_records(job_id, email);
        """)
        # Existing deployments created before file retention need this small migration.
        # PostgreSQL marks the whole transaction as failed after a duplicate-column
        # exception, so use its idempotent DDL instead of catching that exception.
        if using_postgres():
            db.execute("ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS original_csv BYTEA")
        else:
            columns = db.execute("PRAGMA table_info(import_jobs)").fetchall()
            if "original_csv" not in {column["name"] for column in columns}:
                db.execute("ALTER TABLE import_jobs ADD COLUMN original_csv BLOB")


@contextmanager
def connection():
    if using_postgres():
        import psycopg
        from psycopg.rows import dict_row
        raw = psycopg.connect(config.DATABASE_URL, row_factory=dict_row)
        db = PostgresConnection(raw)
    else:
        db = sqlite3.connect(config.DATABASE_PATH)
        db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    finally:
        db.close()
