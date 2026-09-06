# ESG Integration in Project Management — Reproducibility

**Paper:** ESG Integration in Project Management: Incorporating Environmental, Social and Governance Criteria into Project Success Metrics

This folder contains the reproducible analysis used for the MBA Project Management paper.

## Evidence base

Primary empirical dataset: **Sustainable roadway construction data from Greenroads certified projects**, Zokaei Ashtiani & Muench (2022), Mendeley Data, DOI: `10.17632/ds243x9mbs.1`.

The dataset contains 33 completed/certified roadway projects and twelve quantitative sustainability performance benchmarks. The associated peer-reviewed article is:

Zokaei Ashtiani, M., & Muench, S. T. (2022). *Using construction data and whole life cycle assessment to establish sustainable roadway performance benchmarks*. Journal of Cleaner Production, 380, 135031. DOI: `10.1016/j.jclepro.2022.135031`.

## Important evidence boundary

The paper does **not** fabricate unavailable project observations. The analysis script uses only values that are explicitly reported by the published source and performs transparent calculations from those values. The raw Mendeley workbook remains the authoritative source for the underlying project-level observations.

The two benchmark values used numerically in the paper are:
- Water use: 32,000 gallons per $1 million (2020 USD) of project bid price.
- Vegetated area: 28% of total area.

The remaining ten metrics are used for dimension-coverage analysis because the source establishes their existence as quantitative benchmarks, but their exact median values are not reproduced in the paper unless directly verified from the source.

## Reproduce

```bash
python analysis.py
```

Outputs are written to `results/` and include the tables and figures used by the paper.
