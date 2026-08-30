from __future__ import annotations

from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.models import DatasetProfile, SchemaAcceptanceRequest, SchemaAcceptanceResponse
from app.services.capabilities import determine_capabilities
from app.services.csv_ingestion import CsvValidationError, parse_csv
from app.services.profiling import canonical_fields, profile_dataset

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
profiles: dict[str, DatasetProfile] = {}


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
        profile = profile_dataset(headers, rows)
        dataset_id = str(uuid4())
        profile.dataset_id = dataset_id
        profiles[dataset_id] = profile
        return profile
    except CsvValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/datasets/{dataset_id}/schema", response_model=SchemaAcceptanceResponse)
def accept_schema(dataset_id: str, request: SchemaAcceptanceRequest) -> SchemaAcceptanceResponse:
    profile = profiles.get(dataset_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="The temporary dataset profile was not found. Upload the CSV again.")
    sources = {column.source_name for column in profile.columns}
    if set(request.mappings) != sources:
        raise HTTPException(status_code=422, detail="Mappings must include every source column exactly once.")
    accepted = request.mappings
    if not set(accepted.values()) <= canonical_fields():
        raise HTTPException(status_code=422, detail="A mapping contains an unsupported canonical field.")
    mapped_fields = [field for field in accepted.values() if field != "unknown"]
    if len(mapped_fields) != len(set(mapped_fields)):
        raise HTTPException(status_code=422, detail="Each canonical field may be assigned only once. Resolve mapping collisions first.")
    return SchemaAcceptanceResponse(dataset_id=dataset_id, mappings=accepted, capabilities=determine_capabilities(accepted, profile.row_count))


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
