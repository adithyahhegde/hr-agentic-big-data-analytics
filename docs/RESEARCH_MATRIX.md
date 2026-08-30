# Research & Product Comparison Matrix

## Status
Evidence-checked for implementation scoping on 2026-08-30. This matrix is not exhaustive and does not establish novelty. The primary-source checks of Data Interpreter, Microsoft Data Formulator 0.7, Oracle Data Science Agent, and SAS workforce analytics confirm that the broad product combination is already occupied; its remaining rows identify investigation targets, not verified differentiation.

## Comparison

| Work/system | Year | Data / domain | Agentic planning | Schema/data understanding | Objective/analysis discovery | ML/model workflow | Big-data / scalable layer | Explainability / recommendations | Main overlap | Remaining gap for this project |
|---|---:|---|---|---|---|---|---|---|---|---|
| Data Interpreter (Hong et al.) | 2025 publication | General data science | Yes; hierarchical graph planning + iterative verification | General data-science context | Broad data-science problem solving | Yes; end-to-end ML/open-ended tasks | Not the core contribution | General task outputs | Autonomous data-science agent | HR-specific semantic schema + HR feasibility/goal discovery + governed HR decision support + explicit scalable HR execution are not its stated focus |
| Microsoft Data Formulator | 2026 current release | Enterprise/tabular data | Yes; recommendation/insight agents and agent mode | Yes; semantic concepts, multi-table/data connectors | Yes; can recommend exploration ideas from goals/data | Analytics/visualization rather than a general HR ML engine | Yes; large-data support, DuckDB, databases, data lake/connectors | Visualization reports, lineage and insights | Very strong overlap on heterogeneous data + agentic exploration + goal recommendation | HR-specific analytical feasibility, ML governance, HR schema ontology, and decision-support workflow |
| Oracle Data Science Agent | 2026 | Database-resident enterprise data | Guided agentic ML workflow | Database object/context selection and data preparation | Can discover/explore and answer analytical questions | Profiling, feature preparation, training, evaluation, inference | In-database execution | Guided conversational results | Very close to autonomous data-science workflow | Not HR-specific; no demonstrated HR semantic schema/ontology or HR-specific decision governance; architecture is tied to Oracle ecosystem |
| Oracle Schema Discovery Agent | 2026 | Enterprise database schemas | Agentic schema discovery | Explicit schema/catalog understanding | Enables downstream agentic querying | Not an HR ML workflow | Enterprise database context | Focuses on grounding/correctness | Strong overlap with our schema interpretation problem | HR-specific semantic ontology + analytical feasibility + measurable downstream impact |
| SAS Agentic AI for Workforce Analytics | 2026 | HR/workforce | Yes; governed multi-step agentic flow | Checks required inputs | Workflow is predefined around workforce/attrition use case | Deterministic ML + rules + LLM workflow | Enterprise SAS platform | Traceable/governed recommendations | Agentic HR analytics + recommendations | More general HR objective discovery from heterogeneous schemas and an independent open/local architecture remain potential differentiators |
| SAP People Intelligence / agentic workforce analytics | 2025-26 | Enterprise people/workforce data | Agent reasons over people data and recommends actions | Enterprise people-data context | Trend/problem discovery within people analytics | Analytics-focused | Enterprise data cloud / HCM ecosystem | Explanations and tailored actions | Strong commercial overlap with agentic workforce intelligence | Arbitrary user-supplied HR datasets, schema uncertainty, and reproducible research evaluation remain areas to investigate |
| IEEE: Towards Intelligent HR Management: Agentic AI Approach with Embedded Analytics | 2025 | Recruitment / HR | Multi-agent workflow | OCR + LLM mapping of resume/JD information | Recruitment task-specific | Matching, testing and analytics | Not central | Decision hub + human approval | Agentic HR + analytics + decision support | Different HR problem; not a general-purpose HR analytical workflow discovery engine |
| Agentic AI in HRM: Autonomous Decision Systems and Organizational Governance | 2026 | HRM conceptual framework | Agentic autonomy | Conceptual | Broad HR functions | Conceptual | Not implementation-specific | Governance-focused | Agentic HR decision-making | Provides governance framing rather than the proposed executable heterogeneous-data analytics pipeline |
| Agentic AI Framework for Autonomous Workforce Analytics and Decision Support in Enterprise HRIS Systems | 2026 | Workforce analytics / HRIS | Yes; multi-agent reasoning, planning and execution | Enterprise HRIS context | Broad workforce functions | Attrition, performance, planning, compliance etc. | Real-time enterprise pipelines are part of the framework | Decision support, human oversight and governance | Extremely close at conceptual level | Must inspect the full paper to determine whether it actually implements semantic schema interpretation + objective feasibility discovery + reproducible scalable execution |
| Agentic AI Powered Talent Analytics systematic review | 2026 | Talent/workforce analytics | Reviews autonomous agents across talent lifecycle | Multi-source HR/talent data | Discusses discovery/planning across talent analytics | Predictive people analytics | Multi-source enterprise feeds discussed | Human-AI collaboration and governance | Confirms the broader research area is active and crowded | Requires a narrower technical/evaluation contribution |
| AutoML HR promotion prediction | 2026 | HR promotion | Automated model pipeline | Dataset-specific | Fixed promotion objective | AutoML + interpretable models | Not central | Interpretability/fairness | HR + AutoML | Does not establish general objective discovery or autonomous multi-analysis planning |
| TableLlama | 2024 | General tables | No general agentic planner | Semantic column type annotation | Task-specific table understanding | Table tasks | Not central | Table QA | Semantic table understanding | Potentially relevant technique for column semantics; not HR-specific and not an end-to-end HR analytics agent |
| DataSpace benchmark | 2026 | Heterogeneous workspaces: CSV, JSON, SQLite, Markdown, PDF, video | Yes; agents answer complex data tasks | Header-invariant column alignment and heterogeneous artifact grounding | Task is supplied rather than discovered | Verifiable tabular outputs | 15.01 GB benchmark workspace | Deterministic evaluation and provenance-oriented verification | Shows heterogeneous data-agent reliability is a major open problem | Domain-specific HR objective discovery, schema semantics and workflow validation |
| DSAgentBench | 2026 | General real-computer data science | Yes; long-horizon multi-tool workflows | Data wrangling and intermediate grounding | Tasks supplied by benchmark | Full data-science lifecycle | Real computer environments rather than a specific distributed engine | Deterministic evaluation of analytical correctness, visuals and model performance | Shows end-to-end autonomous data science remains unreliable | HR-specific workflow constraints, schema uncertainty, objective feasibility and scalable execution |

## Current assessment

The broad claims are already occupied:

- agentic data analysis exists;
- autonomous data-science workflows exist;
- HR/workforce agentic analytics exists;
- enterprise schema discovery exists;
- heterogeneous data-agent benchmarking exists;
- commercial workforce-intelligence products increasingly connect analytics to recommendations and action.

Recent evidence makes this especially important. Microsoft Data Formulator now supports agentic exploration, recommendations, semantic field analysis, large-data workflows and live/connected data. citeturn1search0turn1search1 A 2026 systematic review explicitly describes agentic AI across talent analytics and workforce planning. citeturn0search1 SAP and other enterprise vendors are also positioning agentic workforce intelligence as part of Autonomous HCM. citeturn0search2turn2search16

Therefore the project must not claim novelty merely from combining an LLM, an agent, Spark, ML and SHAP.

## Candidate research gap

The strongest current hypothesis is a narrower pipeline:

> Given a previously unseen, heterogeneous HR dataset, determine which analytical objectives are actually supported by the available fields and data quality; semantically map uncertain fields into a canonical HR schema with confidence/evidence; generate a constrained analytical plan; execute it using validated analytical tools; and return provenance-linked results and recommendations with explicit uncertainty and human approval points.

This is a **research hypothesis, not a verified novelty claim**.

## Important new warning

The objective-discovery idea is **not automatically novel either**. Data Formulator already supports recommendation/agent modes that can suggest exploration ideas, and Gartner's August 2026 research explicitly frames agentic analytics as moving toward continuous discovery rather than purely hypothesis-driven analysis. citeturn1search0turn0search7

The potential contribution therefore needs to be more specific than "the agent finds useful analyses." The research question should test whether an **HR-domain semantic feasibility layer** can improve the reliability of autonomous analytical planning on heterogeneous HR data compared with a generic data agent.

## What must be tested next

1. Inspect the full 2026 workforce-analytics framework paper and determine its concrete architecture, datasets, experiments and schema assumptions.
2. Search specifically for automatic analytical-objective discovery from arbitrary HR datasets.
3. Search for HR-specific semantic schema mapping / ontology induction used to drive analytics rather than retrieval.
4. Search for feasibility checking before model selection in agentic analytics.
5. Search for systems combining these with Spark/distributed execution.
6. Define measurable baselines: generic data agent, rule-based schema mapper, LLM-only schema mapper, and our proposed HR semantic feasibility layer.
7. Only after those comparisons should the PRD's research contribution be frozen.

## Evidence links

- Microsoft Data Formulator: https://github.com/microsoft/data-formulator
- DataSpace: https://arxiv.org/abs/2608.03451
- DSAgentBench: https://arxiv.org/abs/2608.10366
- Agentic AI Powered Talent Analytics systematic review: https://xlescience.org/index.php/IJASIS/article/view/538
- Oracle Schema Discovery Agent: https://blogs.oracle.com/cloud-infrastructure/schema-discovery-agent-for-nl2sql-ai
- Agentic workforce analytics framework: https://www.researchgate.net/publication/410602799_Agentic_AI_Framework_for_Autonomous_Workforce_Analytics_and_Decision_Support_in_Enterprise_HRIS_Systems

## Last reviewed

2026-08-30
