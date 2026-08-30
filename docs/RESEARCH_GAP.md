# Research Gap & Novelty Review

## Status
**Evidence-checked, no novelty claim.** A 2026-08-30 refresh against primary sources—[Data Interpreter](https://aclanthology.org/2025.findings-acl.1016/), [Microsoft Data Formulator 0.7](https://www.microsoft.com/en-us/research/blog/data-formulator-0-7-ai-powered-data-analytics-for-enterprise-data/), [Oracle Data Science Agent](https://docs.oracle.com/en/database/oracle/machine-learning/data-science-agent/tasks.html), and [SAS workforce analytics](https://blogs.sas.com/content/subconsciousmusings/2026/05/29/agentic-ai-for-workforce-analytics/)—confirms material overlap. The project therefore makes no “first” or broad-combination novelty claim.

The initial literature/product review confirms that the broad combination of agentic AI, HR analytics, ML and decision support already exists. The project therefore needs a narrower, testable contribution.

## What the review already establishes

1. **Autonomous data-science agents already exist.** Data Interpreter presents an LLM agent for end-to-end data-science workflows using hierarchical planning and iterative verification. It is published in Findings of ACL 2025.
   Source: https://aclanthology.org/2025.findings-acl.1016/

2. **AI-guided general data analytics already exists.** Microsoft Data Formulator 0.7 provides agent-guided enterprise data exploration, data connectors, recommendation/insight agents, multi-table workflows and large-data support.
   Source: https://www.microsoft.com/en-us/research/blog/data-formulator-0-7-ai-powered-data-analytics-for-enterprise-data/

3. **Agentic machine-learning workflows already exist.** Oracle Data Science Agent supports discovery, preparation, model training, evaluation and scoring in an in-database workflow.
   Source: https://docs.oracle.com/en/database/oracle/machine-learning/oml-notebooks/omlug/dsa.html

4. **Agentic HR workforce analytics already exists.** SAS has published an Agentic AI for Workforce Analytics implementation combining structured ML, rules, LLM agents and HR recommendations.
   Source: https://blogs.sas.com/content/subconsciousmusings/2026/05/29/agentic-ai-for-workforce-analytics/

5. **Agentic HR decision-support research already exists.** A 2025 IEEE PuneCon paper describes a multi-agent HR recruitment system with document processing, semantic extraction, matching, assessment and analytics/decision support.
   DOI: https://doi.org/10.1109/PuneCon67554.2025.11378532

6. **Broader autonomous HR decision systems have also been published in 2026**, including governance frameworks and workforce-analytics architectures. The closest identified item is a July 2026 paper titled *Agentic AI Framework for Autonomous Workforce Analytics and Decision Support in Enterprise HRIS Systems*. Its full implementation details must be inspected before making any gap claim.

7. **HR-specific AutoML is not novel.** A 2026 study evaluates hybrid AutoML for employee promotion prediction.
   DOI: https://doi.org/10.1016/j.jjimei.2026000121

8. **Semantic table/column understanding is an established research area.** TableLlama includes column type annotation and other table-understanding tasks.
   Source: https://github.com/OSU-NLP-Group/TableLlama

## Therefore, what is NOT our novelty

Do not claim novelty for any of the following alone:

- HR attrition prediction
- HR promotion/performance prediction
- AutoML for HR
- SHAP/explainable HR ML
- LLM-based HR analytics
- agentic HR
- workforce analytics agents
- autonomous data-science agents
- HR decision-support dashboards

## Candidate research direction

The strongest current hypothesis is:

> **A domain-specific, schema-aware HR analytics planner that evaluates which analytical objectives are actually feasible from heterogeneous HR data, generates a reproducible execution plan, routes suitable workloads through scalable data processing, and produces evidence-linked decision support with explicit uncertainty and human approval.**

The distinctive elements to investigate are:

1. **Semantic HR schema interpretation** — inconsistent column names and structures are mapped into a canonical HR ontology with confidence and evidence rather than silently guessed.
2. **Objective feasibility discovery** — the system determines which HR analytical questions are supported by the available variables, labels, time coverage and data quality instead of assuming a fixed task such as attrition.
3. **Analytical workflow planning** — the agent creates a reproducible plan linking objective → data requirements → transformations → analytical method → evaluation → explanation.
4. **Scalable execution routing** — large/complex workloads are routed through Spark while small workloads may use lighter local processing; the choice and performance are measurable.
5. **Evidence-linked decision support** — recommendations are generated from structured analytical evidence and accompanied by uncertainty/limitations and human approval rather than presented as autonomous employment decisions.

## Research questions to test

- Can an HR-specific schema layer correctly map inconsistent HR column names and types better than simple string normalization/synonym matching?
- Can the system correctly determine whether a proposed HR objective is feasible from the available data?
- Can an agent generate a valid and reproducible analytical plan across multiple HR datasets?
- Does scalable execution provide measurable benefits as dataset size/complexity increases?
- Can the system produce recommendations that remain traceable to model/statistical evidence?

## Required next investigation

Before locking the contribution:

1. Obtain and inspect the full 2026 *Agentic AI Framework for Autonomous Workforce Analytics and Decision Support in Enterprise HRIS Systems* paper.
2. Search specifically for **objective/goal discovery from arbitrary HR schemas**.
3. Search specifically for **HR semantic schema mapping / canonical HR ontology + agentic analytics**.
4. Search specifically for **agentic HR analytics + Spark/distributed execution**.
5. Search for existing products that accept arbitrary HR data and automatically determine feasible analytical objectives.
6. Update the comparison matrix with evidence from the closest systems.
7. Only then freeze the research contribution.

## Novelty rule

Do not write “first”, “never built”, “no one has done this”, or equivalent claims unless supported by a defensible literature/product review. If an identical or substantially similar system is found, refine the contribution rather than hiding the overlap.

## Research-safe implementation statement

The implementation may evaluate whether confidence-aware schema interpretation, feasibility gates, constrained plans, and provenance improve reliability on defined heterogeneous HR test datasets. Until a labelled protocol and comparative results exist, this is an evaluation hypothesis, not a research contribution claim.
