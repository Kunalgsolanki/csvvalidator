from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", DATA_DIR / "imports.db"))
DATABASE_URL = os.getenv("DATABASE_URL")
CORS_ORIGINS = tuple(
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,https://csv-validator-pied.vercel.app",
    ).split(",")
    if origin.strip()
)
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 5 * 1024 * 1024))
ALLOWED_COLUMNS = ("name", "email", "phone", "company", "city")
REQUIRED_COLUMNS = ("name", "email", "phone", "company")
