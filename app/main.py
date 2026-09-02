from __future__ import annotations

from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.models import (
    DatasetExecutionResponse,
    DatasetProfile,
    SchemaAcceptanceRequest,
    SchemaAcceptanceResponse,
    WorkloadRoutingRequest,
    WorkloadRoutingResponse,
)
from app.services.big_data_engine import read_csv
from app.services.capabilities import determine_capabilities
from app.services.csv_ingestion import CsvValidationError, parse_csv
from app.services.dataset_store import store
from app.services.profiling import canonical_fields, profile_dataset
from app.services.workload_router import RoutingPolicy, WorkloadProfile, route_workload

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


@app.post("/api/workloads/route", response_model=WorkloadRoutingResponse)
def route_workload_api(request: WorkloadRoutingRequest) -> WorkloadRoutingResponse:
    """Return a deterministic execution-path decision without loading dataset data."""
    policy = RoutingPolicy()
    workload = WorkloadProfile(
        row_count=request.row_count,
        column_count=request.column_count,
        estimated_bytes=request.estimated_bytes,
        file_count=request.file_count,
        requires_distributed=request.requires_distributed,
    )
    engine = route_workload(workload, policy)
    return WorkloadRoutingResponse(
        engine=engine.value,
        row_count=request.row_count,
        column_count=request.column_count,
        estimated_bytes=request.estimated_bytes,
        file_count=request.file_count,
        requires_distributed=request.requires_distributed,
        policy={
            "max_local_rows": policy.max_local_rows,
            "max_local_bytes": policy.max_local_bytes,
            "max_local_columns": policy.max_local_columns,
            "max_local_files": policy.max_local_files,
        },
    )


@app.post("/api/datasets/execute", response_model=DatasetExecutionResponse)
def execute_dataset(file: UploadFile = File(...)) -> DatasetExecutionResponse:
    """Persist an upload to disk, route it, and execute a bounded read."""
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Only .csv files are supported for execution.")
    dataset_id = str(uuid4())
    try:
        dataset = store.save_upload(dataset_id, file.filename or "dataset.csv", file.file, settings.max_execution_upload_bytes)
        workload = WorkloadProfile(
            row_count=dataset.row_count,
            column_count=dataset.column_count,
            estimated_bytes=dataset.size_bytes,
        )
        engine = route_workload(workload)
        frame = read_csv(dataset.path, workload)
        # Reading is deliberately the first execution primitive. Later phases
        # will apply task-specific transformations without collecting Spark data.
        if engine.value == "LOCAL":
            del frame
        else:
            del frame
        return DatasetExecutionResponse(
            dataset_id=dataset.dataset_id,
            status="EXECUTED",
            engine=engine.value,
            row_count=dataset.row_count,
            column_count=dataset.column_count,
            size_bytes=dataset.size_bytes,
            dataset_fingerprint=dataset.sha256,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        # Do not expose internal paths, stack traces, or dataset contents.
        raise HTTPException(status_code=500, detail="Dataset execution failed safely. Check the server logs for operational details.") from error


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
