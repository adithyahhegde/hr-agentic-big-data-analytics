from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.models import DatasetProfile, SchemaAcceptanceRequest, SchemaAcceptanceResponse, TaskCandidateResponse, TaskDetectionResponse, WorkloadRoutingRequest, WorkloadRoutingResponse
from app.services.analytics import analyze_csv
from app.services.big_data_engine import read_csv
from app.services.capabilities import determine_capabilities
from app.services.csv_ingestion import CsvValidationError, parse_csv
from app.services.dataset_store import store
from app.services.insight_agent import synthesize
from app.services.ml_engine import run_anomaly_detection, run_clustering, run_ml
from app.services.profiling import canonical_fields, profile_dataset
from app.services.task_detection import detect_tasks
from app.services.workload_router import RoutingPolicy, WorkloadProfile, route_workload

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
profiles: dict[str, DatasetProfile] = {}
accepted_mappings: dict[str, dict[str, str]] = {}
ml_runs: dict[tuple[str, str], dict[str, object]] = {}

@app.get("/api/health")
def health() -> dict[str, object]:
    return {"status": "ok", "service": settings.app_name, "local_llm_enabled": settings.allow_local_llm}

@app.get("/api/schema/fields")
def schema_fields() -> dict[str, list[str]]:
    return {"fields": sorted(canonical_fields())}

@app.post("/api/datasets/profile", response_model=DatasetProfile)
async def upload_and_profile_dataset(file: UploadFile = File(...)) -> DatasetProfile:
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Only .csv files are supported in this MVP.")
    payload = await file.read(settings.max_upload_bytes + 1)
    try:
        headers, rows = parse_csv(payload, max_bytes=settings.max_upload_bytes, max_rows=settings.max_profile_rows, max_columns=settings.max_columns)
        dataset_id = str(uuid4())
        stored = store.save_upload(dataset_id, file.filename or "dataset.csv", BytesIO(payload), settings.max_upload_bytes)
        profile = profile_dataset(headers, rows)
        profile.dataset_id = dataset_id
        profile.dataset_fingerprint = stored.sha256
        profiles[dataset_id] = profile
        return profile
    except (CsvValidationError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

@app.post("/api/workloads/route", response_model=WorkloadRoutingResponse)
def route_workload_api(request: WorkloadRoutingRequest) -> WorkloadRoutingResponse:
    policy = RoutingPolicy()
    workload = WorkloadProfile(row_count=request.row_count, column_count=request.column_count, estimated_bytes=request.estimated_bytes, file_count=request.file_count, requires_distributed=request.requires_distributed)
    engine = route_workload(workload, policy)
    return WorkloadRoutingResponse(engine=engine.value, row_count=request.row_count, column_count=request.column_count, estimated_bytes=request.estimated_bytes, file_count=request.file_count, requires_distributed=request.requires_distributed, policy={"max_local_rows": policy.max_local_rows, "max_local_bytes": policy.max_local_bytes, "max_local_columns": policy.max_local_columns, "max_local_files": policy.max_local_files})

@app.post("/api/datasets/execute")
def execute_dataset(file: UploadFile = File(...)) -> dict[str, object]:
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Only .csv files are supported for execution.")
    dataset_id = str(uuid4())
    try:
        dataset = store.save_upload(dataset_id, file.filename or "dataset.csv", file.file, settings.max_execution_upload_bytes)
        workload = WorkloadProfile(row_count=dataset.row_count, column_count=dataset.column_count, estimated_bytes=dataset.size_bytes)
        engine = route_workload(workload)
        frame = read_csv(dataset.path, workload)
        del frame
        return {"dataset_id": dataset.dataset_id, "status": "EXECUTED", "engine": engine.value, "row_count": dataset.row_count, "column_count": dataset.column_count, "size_bytes": dataset.size_bytes, "dataset_fingerprint": dataset.sha256}
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail="Dataset execution failed safely. Check the server logs for operational details.") from error

@app.post("/api/datasets/{dataset_id}/schema", response_model=SchemaAcceptanceResponse)
def accept_schema(dataset_id: str, request: SchemaAcceptanceRequest) -> SchemaAcceptanceResponse:
    profile = profiles.get(dataset_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="The temporary dataset profile was not found. Upload the CSV again.")
    sources = {column.source_name for column in profile.columns}
    if set(request.mappings) != sources:
        raise HTTPException(status_code=422, detail="Mappings must include every source column exactly once.")
    if not set(request.mappings.values()) <= canonical_fields():
        raise HTTPException(status_code=422, detail="A mapping contains an unsupported canonical field.")
    mapped_fields = [field for field in request.mappings.values() if field != "unknown"]
    if len(mapped_fields) != len(set(mapped_fields)):
        raise HTTPException(status_code=422, detail="Each canonical field may be assigned only once. Resolve mapping collisions first.")
    accepted_mappings[dataset_id] = request.mappings
    ml_runs.clear()
    return SchemaAcceptanceResponse(dataset_id=dataset_id, mappings=request.mappings, capabilities=determine_capabilities(request.mappings, profile.row_count))

@app.get("/api/datasets/{dataset_id}/tasks", response_model=TaskDetectionResponse)
def detect_dataset_tasks(dataset_id: str) -> TaskDetectionResponse:
    profile = profiles.get(dataset_id)
    mappings = accepted_mappings.get(dataset_id)
    if profile is None or mappings is None:
        raise HTTPException(status_code=409, detail="Confirm the dataset schema before detecting analytical tasks.")
    tasks = detect_tasks(mappings, profile.row_count)
    return TaskDetectionResponse(dataset_id=dataset_id, row_count=profile.row_count, tasks=[TaskCandidateResponse(objective=t.objective, status=t.status, target_field=t.target_field, feature_fields=list(t.feature_fields), reasons=list(t.reasons)) for t in tasks])

@app.get("/api/datasets/{dataset_id}/analytics")
def dataset_analytics(dataset_id: str) -> dict[str, object]:
    profile = profiles.get(dataset_id)
    mappings = accepted_mappings.get(dataset_id)
    dataset = store.get(dataset_id)
    if profile is None or mappings is None or dataset is None:
        raise HTTPException(status_code=409, detail="Confirm the dataset schema before running analytics.")
    try:
        workload = WorkloadProfile(row_count=dataset.row_count, column_count=dataset.column_count, estimated_bytes=dataset.size_bytes)
        engine = route_workload(workload)
        return {"dataset_id": dataset_id, "engine": engine.value, "dataset_fingerprint": dataset.sha256, "schema_version": profile.schema_version, **analyze_csv(dataset.path, mappings)}
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

@app.post("/api/datasets/{dataset_id}/ml/{objective}")
def run_dataset_ml(dataset_id: str, objective: str) -> dict[str, object]:
    profile = profiles.get(dataset_id)
    mappings = accepted_mappings.get(dataset_id)
    dataset = store.get(dataset_id)
    if profile is None or mappings is None or dataset is None:
        raise HTTPException(status_code=409, detail="Confirm the dataset schema before running ML.")
    task = next((task for task in detect_tasks(mappings, profile.row_count) if task.objective == objective), None)
    if task is None:
        raise HTTPException(status_code=404, detail="Unknown analytical objective.")
    if task.status != "FEASIBLE" or not task.target_field:
        raise HTTPException(status_code=409, detail="This analytical task is currently blocked by the confirmed schema or dataset size.")
    key = (dataset_id, objective)
    if key in ml_runs:
        return ml_runs[key]
    try:
        result = run_ml(dataset.path, mappings, objective, task.target_field, list(task.feature_fields))
        result.update({"dataset_id": dataset_id, "dataset_fingerprint": dataset.sha256, "schema_version": profile.schema_version})
        ml_runs[key] = result
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

@app.post("/api/datasets/{dataset_id}/ml/{objective}/unsupervised")
def run_dataset_unsupervised(dataset_id: str, objective: str) -> dict[str, object]:
    profile = profiles.get(dataset_id)
    mappings = accepted_mappings.get(dataset_id)
    dataset = store.get(dataset_id)
    if profile is None or mappings is None or dataset is None:
        raise HTTPException(status_code=409, detail="Confirm the dataset schema before running ML.")
    task = next((task for task in detect_tasks(mappings, profile.row_count) if task.objective == objective), None)
    if task is None or objective not in {"employee_clustering", "anomaly_detection"}:
        raise HTTPException(status_code: 404, detail="Unknown unsupervised analytical objective.")
    if task.status != "FEASIBLE":
        raise HTTPException(status_code=409, detail="This analytical task is currently blocked by the confirmed schema or dataset size.")
    key = (dataset_id, objective)
    if key in ml_runs:
        return ml_runs[key]
    try:
        result = (run_clustering if objective == "employee_clustering" else run_anomaly_detection)(dataset.path, mappings, list(task.feature_fields))
        result.update({"dataset_id": dataset_id, "dataset_fingerprint": dataset.sha256, "schema_version": profile.schema_version})
        ml_runs[key] = result
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

@app.get("/api/datasets/{dataset_id}/insights")
def dataset_insights(dataset_id: str) -> dict[str, object]:
    profile = profiles.get(dataset_id)
    mappings = accepted_mappings.get(dataset_id)
    dataset = store.get(dataset_id)
    if profile is None or mappings is None or dataset is None:
        raise HTTPException(status_code=409, detail="Confirm the dataset schema before synthesizing insights.")
    try:
        workload = WorkloadProfile(row_count=dataset.row_count, column_count=dataset.column_count, estimated_bytes=dataset.size_bytes)
        analytics = {"dataset_id": dataset_id, "engine": route_workload(workload).value, "dataset_fingerprint": dataset.sha256, "schema_version": profile.schema_version, **analyze_csv(dataset.path, mappings)}
        runs = [result for (stored_dataset, _), result in ml_runs.items() if stored_dataset == dataset_id]
        return synthesize(analytics, runs) | {"dataset_id": dataset_id, "dataset_fingerprint": dataset.sha256, "schema_version": profile.schema_version}
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
