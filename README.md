# HR Agentic Big Data Analytics

A local-first HR analytics workbench for heterogeneous and messy workforce datasets.

## Current product

The application now provides an end-to-end user workflow:

`CSV upload → data health → canonical HR schema review → feasible-task detection → deterministic analytics → evidence-backed insights → provenance`

The product automatically profiles uploaded data, evaluates quality rules, proposes schema mappings with confidence/evidence, lets the user confirm or reject mappings, detects which analytical objectives are feasible, routes workloads between local and Spark execution policies, and computes descriptive analytics from the confirmed schema.

The interface is intentionally designed as an analytics workbench rather than a generic AI chatbot. Numerical findings are computed deterministically; the optional local LLM is not required for the core workflow.

## Run locally

Create an environment, install the project with its `dev` extra, then run:

`uvicorn app.main:app --reload`

Open `http://127.0.0.1:8000`.

For Spark/large-data execution, install the `bigdata` extra as described in `pyproject.toml`.

## Product boundary

The current release is a strong functional product foundation, not the final research-grade system. Model training/evaluation, explainability, richer scalable transformations, agentic evidence synthesis, durable persistence, and formal benchmark testing remain subsequent layers.

Uploads used by the profiling workflow are stored temporarily on local disk so the confirmed schema can be reused for analytics. Durable production persistence/lifecycle management is not yet implemented.

See `docs/MVP_SPEC.md`, `docs/API_CONTRACTS.md`, and `docs/IMPLEMENTATION.md` for the current contracts and implementation status.
