from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.models import DatasetProfile, SchemaAcceptanceRequest, SchemaAcceptanceResponse, TaskCandidateResponse, TaskDetectionResponse, WorkloadRoutingRequest, WorkloadRoutingResponse
from app.services.analytics import analyze_csv
from app.services.automl_engine import run_automl
from app.services.big_data_engine import read_csv
from app.services.capabilities import determine_capabilities
from app.services.csv_ingestion import CsvValidationError, parse_csv
from app.services.dataset_registry import registry
from app.services.dataset_store import store
from app.services.heterogeneous_ml import run_heterogeneous_ml
from app.services.insight_agent import synthesize
from app.services.ml_engine import run_anomaly_detection, run_clustering
from app.services.planning_agent import plan_analyses
from app.services.profiling import canonical_fields, profile_dataset
from app.services.report_export import build_report, to_html
from app.services.run_history import history
from app.services.spark_anomaly import run_distributed_anomaly
from app.services.spark_analytics import analyze_spark
from app.services.spark_ml_engine import run_spark_clustering, run_spark_ml
from app.services.task_detection import detect_tasks
from app.services.workload_router import RoutingPolicy, WorkloadProfile, route_workload

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
profiles: dict[str, DatasetProfile] = {}
accepted_mappings: dict[str, dict[str, str]] = {}
ml_runs: dict[tuple[str, str], dict[str, object]] = {}


def _state(dataset_id: str) -> tuple[DatasetProfile | None, dict[str, str] | None]:
    profile = profiles.get(dataset_id)
    if profile is None:
        payload = registry.get_profile(dataset_id)
        if payload:
            profile = DatasetProfile.model_validate(payload)
            profiles[dataset_id] = profile
    mappings = accepted_mappings.get(dataset_id)
    if mappings is None:
        mappings = registry.get_mappings(dataset_id)
        if mappings is not None:
            accepted_mappings[dataset_id] = mappings
    return profile, mappings


def _require_state(dataset_id: str) -> tuple[DatasetProfile, dict[str, str], object]:
    profile, mappings = _state(dataset_id)
    dataset = store.get(dataset_id)
    if profile is None or mappings is None or dataset is None:
        raise HTTPException(status_code=409, detail="Confirm the dataset schema before running analysis.")
    return profile, mappings, dataset


@app.get("/api/schema/fields")
def schema_fields() -> dict[str, list[str]]:
    return {"fields": sorted(canonical_fields())}


@app.post("/api/datasets/profile")
def create_profile(file: UploadFile = File(...)) -> DatasetProfile:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")
    content = file.file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="The uploaded file exceeds the configured profile-size limit.")
    dataset_id = str(uuid4())
    path = store.save(dataset_id, file.filename, content)
    try:
        dataset = parse_csv(path, dataset_id, file.filename, max_columns=settings.max_columns)
        registry.register(dataset)
        profile = profile_dataset(path, dataset, max_rows=settings.max_profile_rows)
        profiles[dataset_id] = profile
        registry.save_profile(dataset_id, profile)
        return profile
    except CsvValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/datasets/{dataset_id}/schema", response_model=SchemaAcceptanceResponse)
def accept_schema(dataset_id: str, request: SchemaAcceptanceRequest) -> SchemaAcceptanceResponse:
    profile, _ = _state(dataset_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="The dataset profile was not found. Upload the CSV again.")
    sources = {column.source_name for column in profile.columns}
    if set(request.mappings) != sources:
        raise HTTPException(status_code=422, detail="Mappings must include every source column exactly once.")
    if not set(request.mappings.values()) <= canonical_fields():
        raise HTTPException(status_code=422, detail="A mapping contains an unsupported canonical field.")
    mapped_fields = [field for field in request.mappings.values() if field != "unknown"]
    if len(mapped_fields) != len(set(mapped_fields)):
        raise HTTPException(status_code=422, detail="Each canonical field may be assigned only once. Resolve mapping collisions first.")
    accepted_mappings[dataset_id] = request.mappings
    registry.save_mappings(dataset_id, request.mappings)
    for key in [key for key in ml_runs if key[0] == dataset_id]:
        del ml_runs[key]
    return SchemaAcceptanceResponse(dataset_id=dataset_id, mappings=request.mappings, capabilities=determine_capabilities(request.mappings, profile.row_count))


@app.get("/api/datasets/{dataset_id}/tasks", response_model=TaskDetectionResponse)
def detect_dataset_tasks(dataset_id: str) -> TaskDetectionResponse:
    profile, mappings = _state(dataset_id)
    if profile is None or mappings is None:
        raise HTTPException(status_code=409, detail="Confirm the dataset schema before detecting analytical tasks.")
    tasks = detect_tasks(mappings, profile.row_count)
    return TaskDetectionResponse(dataset_id=dataset_id, row_count=profile.row_count, tasks=[TaskCandidateResponse(objective=t.objective, status=t.status, target_field=t.target_field, feature_fields=list(t.feature_fields), reasons=list(t.reasons)) for t in tasks])


@app.get("/api/datasets/{dataset_id}/plan")
def plan_dataset_analyses(dataset_id: str) -> dict[str, object]:
    profile, mappings = _state(dataset_id)
    if profile is None or mappings is None:
        raise HTTPException(status_code=409, detail="Confirm the dataset schema before asking the planning agent.")
    tasks = detect_tasks(mappings, profile.row_count)
    return plan_analyses(tasks, settings)


@app.get("/api/datasets/{dataset_id}/analytics")
def dataset_analytics(dataset_id: str) -> dict[str, object]:
    profile, mappings, dataset = _require_state(dataset_id)
    try:
        workload = WorkloadProfile(row_count=dataset.row_count, column_count=dataset.column_count, estimated_bytes=dataset.size_bytes)
        engine = route_workload(workload)
        analytics_result = analyze_spark(dataset.path, mappings) if engine.value == "SPARK" else analyze_csv(dataset.path, mappings)
        result = {"dataset_id": dataset_id, "engine": engine.value, "dataset_fingerprint": dataset.sha256, "schema_version": profile.schema_version, **analytics_result}
        history.record(dataset_id, dataset.sha256, "descriptive_analytics", "SUCCEEDED", result, engine.value)
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.post("/api/datasets/{dataset_id}/ml/{objective}")
def run_dataset_ml(dataset_id: str, objective: str) -> dict[str, object]:
    profile, mappings, dataset = _require_state(dataset_id)
    task = next((task for task in detect_tasks(mappings, profile.row_count) if task.objective == objective), None)
    if task is None:
        raise HTTPException(status_code=404, detail="Unknown analytical objective.")
    if task.status != "FEASIBLE" or not task.target_field:
        raise HTTPException(status_code=409, detail="This analytical task is currently blocked by the confirmed schema or dataset size.")
    key = (dataset_id, objective)
    if key in ml_runs:
        return ml_runs[key]
    try:
        workload = WorkloadProfile(row_count=dataset.row_count, column_count=dataset.column_count, estimated_bytes=dataset.size_bytes)
        engine = route_workload(workload)
        result = run_spark_ml(dataset.path, mappings, objective, task.target_field, list(task.feature_fields)) if engine.value == "SPARK" else run_heterogeneous_ml(dataset.path, mappings, objective, task.target_field, list(task.feature_fields))
        result.update({"dataset_id": dataset_id, "dataset_fingerprint": dataset.sha256, "schema_version": profile.schema_version, "engine": engine.value})
        ml_runs[key] = result
        history.record(dataset_id, dataset.sha256, objective, "SUCCEEDED", result, engine.value)
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.post("/api/datasets/{dataset_id}/ml/{objective}/automl")
def run_dataset_automl(dataset_id: str, objective: str) -> dict[str, object]:
    """Run bounded AutoML for a feasible supervised objective on the local engine."""
    profile, mappings, dataset = _require_state(dataset_id)
    if objective not in {"attrition_classification", "salary_regression"}:
        raise HTTPException(status_code=404, detail="AutoML is currently available only for supervised objectives.")
    task = next((task for task in detect_tasks(mappings, profile.row_count) if task.objective == objective), None)
    if task is None or task.status != "FEASIBLE" or not task.target_field:
        raise HTTPException(status_code=409, detail="This analytical task is currently blocked by the confirmed schema or dataset size.")
    workload = WorkloadProfile(row_count=dataset.row_count, column_count=dataset.column_count, estimated_bytes=dataset.size_bytes)
    engine = route_workload(workload)
    if engine.value != "LOCAL":
        raise HTTPException(status_code=409, detail="This dataset is routed to Spark. Run the routed model comparison instead of local AutoML.")
    key = (dataset_id, f"automl:{objective}")
    if key in ml_runs:
        return ml_runs[key]
    try:
        result = run_automl(dataset.path, mappings, objective, task.target_field, list(task.feature_fields), time_budget=settings.automl_time_budget_seconds)
        result.update({"dataset_id": dataset_id, "dataset_fingerprint": dataset.sha256, "schema_version": profile.schema_version, "engine": "LOCAL", "execution_mode": "BOUNDED_AUTOML"})
        ml_runs[key] = result
        history.record(dataset_id, dataset.sha256, f"automl:{objective}", "SUCCEEDED", result, "LOCAL")
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.post("/api/datasets/{dataset_id}/ml/{objective}/unsupervised")
def run_dataset_unsupervised(dataset_id: str, objective: str) -> dict[str, object]:
    profile, mappings, dataset = _require_state(dataset_id)
    task = next((task for task in detect_tasks(mappings, profile.row_count) if task.objective == objective), None)
    if task is None or objective not in {"employee_clustering", "anomaly_detection"}:
        raise HTTPException(status_code=404, detail="Unknown unsupervised analytical objective.")
    if task.status != "FEASIBLE":
        raise HTTPException(status_code=409, detail="This analytical task is currently blocked by the confirmed schema or dataset size.")
    key = (dataset_id, objective)
    if key in ml_runs:
        return ml_runs[key]
    try:
        workload = WorkloadProfile(row_count=dataset.row_count, column_count=dataset.column_count, estimated_bytes=dataset.size_bytes)
        engine = route_workload(workload)
        if engine.value == "SPARK":
            result = run_spark_clustering(dataset.path, mappings, list(task.feature_fields)) if objective == "employee_clustering" else run_distributed_anomaly(dataset.path, mappings, list(task.feature_fields))
        else:
            result = run_clustering(dataset.path, mappings, list(task.feature_fields)) if objective == "employee_clustering" else run_anomaly_detection(dataset.path, mappings, list(task.feature_fields))
        result.update({"dataset_id": dataset_id, "dataset_fingerprint": dataset.sha256, "schema_version": profile.schema_version, "engine": engine.value})
        ml_runs[key] = result
        history.record(dataset_id, dataset.sha256, objective, "SUCCEEDED", result, engine.value)
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/api/datasets/{dataset_id}/runs")
def dataset_runs(dataset_id: str, limit: int = 50) -> dict[str, object]:
    return {"dataset_id": dataset_id, "runs": history.list(dataset_id, limit)}
