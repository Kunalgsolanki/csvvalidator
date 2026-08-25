from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from .config import CORS_ORIGINS, MAX_UPLOAD_BYTES
from .database import initialise_database
from .schemas import JobSummary, RecordPage
from .service import create_job, get_job, list_jobs, original_csv, process_job, records_for_job, valid_csv

app = FastAPI(title="CSV Validator API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup():
    initialise_database()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/imports", response_model=JobSummary, status_code=202)
async def upload_import(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    filename = file.filename or "upload.csv"
    if not filename.lower().endswith(".csv"):
        raise HTTPException(415, "Only .csv files are supported.")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(400, "The uploaded CSV is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File exceeds the {MAX_UPLOAD_BYTES // 1024 // 1024} MB upload limit.")
    job_id = create_job(filename, content)
    background_tasks.add_task(process_job, job_id, content)
    return get_job(job_id)


@app.get("/api/imports", response_model=list[JobSummary])
def imports():
    return list_jobs()


@app.get("/api/imports/{job_id}", response_model=JobSummary)
def import_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Import job not found.")
    return job


@app.get("/api/imports/{job_id}/records", response_model=RecordPage)
def records(job_id: str, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100), search: str = "", invalid_only: bool = False):
    if not get_job(job_id):
        raise HTTPException(404, "Import job not found.")
    items, total = records_for_job(job_id, page, page_size, search, invalid_only)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@app.get("/api/imports/{job_id}/valid-records.csv")
def download_valid_records(job_id: str):
    if not get_job(job_id):
        raise HTTPException(404, "Import job not found.")
    return Response(valid_csv(job_id), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="valid-records-{job_id}.csv"'})


@app.get("/api/imports/{job_id}/original.csv")
def download_original_csv(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Import job not found.")
    content = original_csv(job_id)
    if content is None:
        raise HTTPException(404, "The original CSV is unavailable for this import.")
    return Response(content, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="original-{job["filename"]}"'})
