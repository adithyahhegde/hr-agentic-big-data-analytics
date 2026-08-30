from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.models import DatasetProfile
from app.services.csv_ingestion import CsvValidationError, parse_csv
from app.services.profiling import profile_dataset

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/api/health")
def health() -> dict[str, object]:
    return {"status": "ok", "service": settings.app_name, "local_llm_enabled": settings.allow_local_llm}


@app.post("/api/datasets/profile", response_model=DatasetProfile)
async def upload_and_profile_dataset(file: UploadFile = File(...)) -> DatasetProfile:
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Only .csv files are supported in this MVP.")
    payload = await file.read(settings.max_upload_bytes + 1)
    try:
        headers, rows = parse_csv(payload, max_bytes=settings.max_upload_bytes, max_rows=settings.max_profile_rows, max_columns=settings.max_columns)
        return profile_dataset(headers, rows)
    except CsvValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
