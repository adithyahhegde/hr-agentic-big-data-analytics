# Research & Product Comparison Matrix

## Status
Working literature/product review. This matrix is evidence for refining the research gap; it is not a claim of exhaustive novelty.

| Work/system | Year | Data / domain | Agentic planning | Schema/data understanding | Objective/analysis discovery | ML/model workflow | Big-data / scalable layer | Explainability / recommendations | Main overlap | Remaining gap for this project |
|---|---:|---|---|---|---|---|---|---|---|---|
| Data Interpreter (Hong et al.) | 2025 publication | General data science | Yes; hierarchical graph planning + iterative verification | General data-science context | Broad data-science problem solving | Yes; end-to-end ML/open-ended tasks | Not the core contribution | General task outputs | Autonomous data-science agent | HR-specific semantic schema + HR feasibility/goal discovery + governed HR decision support + explicit scalable HR execution are not its stated focus |
| Microsoft Data Formulator | 2026 current release | Enterprise/tabular data | Yes; recommendation/insight agents and agent mode | Yes; semantic concepts, multi-table/data connectors | Yes; can recommend exploration ideas from goals/data | Analytics/visualization rather than a general HR ML engine | Large-data demos and data-lake/connectors | Visualization reports and insights | AI-guided data exploration and analysis | HR-specific analytical feasibility, ML governance, HR schema ontology, and decision-support workflow |
| Oracle Data Science Agent | 2026 | Database-resident enterprise data | Guided agentic ML workflow | Database object/context selection and data preparation | Can discover/explore and answer analytical questions | Profiling, feature preparation, training, evaluation, inference | In-database execution | Guided conversational results | Very close to autonomous data-science workflow | Not HR-specific; no demonstrated HR semantic schema/ontology or HR-specific decision governance; architecture is tied to Oracle ecosystem |
| SAS Agentic AI for Workforce Analytics | 2026 | HR/workforce | Yes; governed multi-step agentic flow | Checks required inputs | Workflow is predefined around workforce/attrition use case | Deterministic ML + rules + LLM workflow | Enterprise SAS platform | Traceable/governed recommendations | Agentic HR analytics + recommendations | More general HR objective discovery from heterogeneous schemas and an independent open/local architecture remain potential differentiators |
| IEEE: Towards Intelligent HR Management: Agentic AI Approach with Embedded Analytics | 2025 | Recruitment / HR | Multi-agent workflow | OCR + LLM mapping of resume/JD information | Recruitment task-specific | Matching, testing and analytics | Not central | Decision hub + human approval | Agentic HR + analytics + decision support | Different HR problem; not a general-purpose HR analytical workflow discovery engine |
| Agentic AI in HRM: Autonomous Decision Systems and Organizational Governance | 2026 | HRM conceptual framework | Agentic autonomy | Conceptual | Broad HR functions | Conceptual | Not implementation-specific | Governance-focused | Agentic HR decision-making | Provides governance framing rather than the proposed executable heterogeneous-data analytics pipeline |
| Agentic AI Framework for Autonomous Workforce Analytics and Decision Support in Enterprise HRIS Systems | 2026 | Workforce analytics / HRIS | Yes | Real-time enterprise data | Broad workforce functions | Attrition, performance, planning etc. | Real-time data pipelines | Decision support | Extremely close at conceptual level | Need to identify whether it implements semantic schema interpretation + objective feasibility discovery + reproducible scalable execution; this requires deeper paper inspection before claiming a gap |
| AutoML HR promotion prediction (2026) | 2026 | HR promotion | Automated model pipeline | Dataset-specific | Fixed promotion objective | AutoML + interpretable models | Not central | Interpretability/fairness | HR + AutoML | Does not establish general objective discovery or autonomous multi-analysis planning |
| TableLlama | 2024 | General tables | No general agentic planner | Semantic column type annotation | Task-specific table understanding | Table tasks | Not central | Table QA | Semantic table understanding | Potentially relevant technique for column semantics; not HR-specific and not an end-to-end HR analytics agent |

## Evidence links

- Data Interpreter: https://aclanthology.org/2025.findings-acl.1016/
- Microsoft Data Formulator: https://www.microsoft.com/en-us/research/blog/data-formulator-0-7-ai-powered-data-analytics-for-enterprise-data/
- Oracle Data Science Agent: https://docs.oracle.com/en/database/oracle/machine-learning/oml-notebooks/omlug/dsa.html
- SAS Agentic AI for Workforce Analytics: https://blogs.sas.com/content/subconsciousmusings/2026/05/29/agentic-ai-for-workforce-analytics/
- IEEE HR agentic recruitment paper: https://doi.org/10.1109/PuneCon67554.2025.11378532
- Agentic AI in HRM governance paper: https://doi.org/10.51768/dbr.v27i1.271202601
- Agentic workforce analytics framework: DOI 10.70917/ijcisim-2026-2756
- AutoML promotion paper: https://doi.org/10.1016/j.jjimei.2026000121
- TableLlama: https://github.com/OSU-NLP-Group/TableLlama

## Important interpretation

The review already disproves the simple novelty claim that "agentic AI + HR + analytics/decision support" is new. The strongest candidate research contribution therefore has to be narrower and testable.

Candidate direction:

> A domain-specific, schema-aware HR analytics planner that evaluates which analytical objectives are actually feasible from heterogeneous HR data, generates a reproducible execution plan, routes suitable workloads through scalable data processing, and produces evidence-linked decision support with explicit uncertainty and human approval.

This remains a **candidate** contribution, not a proven novel contribution. Before finalizing it, the team should inspect the closest 2026 workforce-agent paper in full and search specifically for objective/goal discovery, semantic schema mapping, feasibility assessment, and Spark/distributed execution.
