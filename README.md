# HR Agentic Big Data Analytics

A local-first HR analytics workbench for heterogeneous and messy workforce datasets.

## Current product

The application now provides an end-to-end analytical workflow:

`CSV upload → data health → canonical HR schema review → feasible-task detection → descriptive analytics → model comparison → explainability evidence → insights/provenance`

The product automatically profiles uploaded data, evaluates quality rules, proposes schema mappings with confidence/evidence, lets the user confirm or reject mappings, detects feasible analytical objectives, routes workloads between local and Spark execution policies, computes descriptive analytics, and can compare multiple supervised ML candidates for feasible attrition-classification and salary-regression tasks.

ML execution is deliberately bounded and deterministic: only confirmed targets are used; identifier-like and constant predictors are excluded; a reproducible held-out split is used; task-appropriate metrics are reported; and feature-importance/permutation evidence is returned with the selected model. The system does not make automated employment decisions.

The interface is intentionally designed as an analytics workbench rather than a generic AI chatbot. Numerical findings and model metrics are computed locally; the optional local LLM is not required for the core workflow.

## Run locally

Create an environment and install the project with the desired extras, then run:

`uvicorn app.main:app --reload`

Open `http://127.0.0.1:8000`.

For supervised ML, install the `ml` extra. For Spark/large-data execution, install the `bigdata` extra. These extras keep the base application lightweight.

## Product boundary

This is an expanding research-grade product foundation, not yet the final evaluated research system. The remaining major layers are agentic evidence synthesis/recommendations, broader feature preparation, native Spark ML, clustering/anomaly execution, SHAP-based explanations, durable persistence, reporting/export, and formal benchmark/robustness testing.

Uploads used by the profiling workflow are stored temporarily on local disk so the confirmed schema and subsequent analysis can reuse the same dataset. Durable production persistence/lifecycle management is not yet implemented.

No new ML test results are claimed until the dedicated end-to-end testing and benchmark pass.

See `docs/MVP_SPEC.md`, `docs/API_CONTRACTS.md`, and `docs/IMPLEMENTATION.md` for current contracts, implementation status, and known boundaries.
