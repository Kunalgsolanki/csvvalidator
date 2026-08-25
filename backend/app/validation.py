"""CSV parsing and customer-record validation rules.

This module has no database code. Keeping it separate makes the validation
rules easy to test and explain independently from the import workflow.
"""

import csv
import io
import json
import re
from collections import Counter

from .config import ALLOWED_COLUMNS, REQUIRED_COLUMNS

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9 .()\-]{6,19}$")


def parse_csv(content: bytes) -> list[dict[str, str]]:
    """Decode a CSV upload, check its column shape, and normalise each row."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("The CSV must be UTF-8 encoded.") from exc

    if not text.strip():
        raise ValueError("The uploaded CSV is empty.")

    try:
        reader = csv.DictReader(io.StringIO(text))
        headers = [header.strip().lower() for header in (reader.fieldnames or [])]
        _validate_headers(headers)

        rows = []
        for raw_row in reader:
            if None in raw_row:
                raise ValueError("A row contains more values than the header defines.")
            rows.append(_normalise_row(raw_row))
        return rows
    except csv.Error as exc:
        raise ValueError("The file contains malformed CSV data.") from exc


def validate_rows(job_id: str, rows: list[dict[str, str]]) -> tuple[list[tuple], int]:
    """Return database-ready record values and the number of duplicate rows."""
    email_counts = Counter(row["email"].lower() for row in rows if row["email"])
    records = []
    duplicate_records = 0

    for row_number, row in enumerate(rows, start=2):
        reasons = _validation_reasons(row, email_counts)
        if "Email is duplicated in this file." in reasons:
            duplicate_records += 1

        # is_valid is an INTEGER in both SQLite and PostgreSQL: 1 = valid,
        # 0 = invalid. Explicit integers avoid a PostgreSQL bool/int mismatch.
        records.append(
            (
                job_id,
                row_number,
                row["name"],
                row["email"],
                row["phone"],
                row["company"],
                row["city"],
                json.dumps(reasons),
                int(not reasons),
            )
        )

    return records, duplicate_records


def _validate_headers(headers: list[str]) -> None:
    missing = sorted(set(REQUIRED_COLUMNS) - set(headers))
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(missing)}.")

    unexpected = set(headers) - set(ALLOWED_COLUMNS)
    if unexpected:
        raise ValueError(f"Unexpected column(s): {', '.join(sorted(unexpected))}.")


def _normalise_row(raw_row: dict[str, str | None]) -> dict[str, str]:
    cleaned_row = {key.strip().lower(): value for key, value in raw_row.items()}
    return {column: (cleaned_row.get(column) or "").strip() for column in ALLOWED_COLUMNS}


def _validation_reasons(row: dict[str, str], email_counts: Counter[str]) -> list[str]:
    reasons = []

    if not row["name"]:
        reasons.append("Name is required.")
    if not row["email"] or not EMAIL_PATTERN.match(row["email"]):
        reasons.append("Email address is invalid.")
    elif email_counts[row["email"].lower()] > 1:
        reasons.append("Email is duplicated in this file.")
    if not row["phone"] or not PHONE_PATTERN.match(row["phone"]):
        reasons.append("Phone number is invalid.")
    if not row["company"]:
        reasons.append("Company is required.")

    return reasons
