from typing import Literal
from pydantic import BaseModel


class JobSummary(BaseModel):
    id: str
    filename: str
    file_size: int
    status: Literal["pending", "processing", "completed", "failed"]
    error_message: str | None = None
    total_records: int
    valid_records: int
    invalid_records: int
    duplicate_records: int
    created_at: str
    completed_at: str | None = None


class RecordResult(BaseModel):
    row_number: int
    name: str
    email: str
    phone: str
    company: str
    city: str
    reasons: list[str]
    is_valid: bool


class RecordPage(BaseModel):
    items: list[RecordResult]
    total: int
    page: int
    page_size: int
