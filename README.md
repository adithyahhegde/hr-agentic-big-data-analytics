# HR Agentic Big Data Analytics

Agentic AI for Autonomous Big Data Analytics & Decision Making in Human Resource Management.

## Project status

Foundation release (0.1.0): local health check, safe CSV profiling, deterministic HR schema proposals, and a small web intake interface.

## Run locally

Create an environment, install the project with its `dev` extra, then run `uvicorn app.main:app --reload`. Open `http://127.0.0.1:8000`.

The service keeps uploads in request memory only. See [the MVP contract](docs/MVP_SPEC.md), [API contracts](docs/API_CONTRACTS.md), and [implementation status](docs/IMPLEMENTATION.md).
