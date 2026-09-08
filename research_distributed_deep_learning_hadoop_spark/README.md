# Distributed Deep Learning Frameworks Using Hadoop and Spark

## Research topic
**Distributed Deep Learning Frameworks Using Hadoop and Spark**

This repository folder contains the reproducible analysis and research artifacts for the MBA research paper on distributed deep learning using Hadoop and Apache Spark.

## Research objective
Evaluate the performance and scalability of distributed deep-learning workloads using Hadoop/Spark infrastructure, using only experimentally observed results and clearly documented configurations.

## Evidence rules
- No fabricated or illustrative experimental results will be presented as findings.
- Every reported number must come from an experiment, an authoritative source, or a clearly labeled derived calculation.
- Dataset versions, software versions, hardware/runtime configuration, seeds, and experiment parameters will be recorded.
- Results will be reproducible from the code and configuration committed to this branch.
- The paper will distinguish framework capabilities, experimental observations, interpretation, and limitations.

## Planned evaluation
The study will establish a controlled baseline and distributed configurations, then evaluate:
- training/runtime performance;
- scalability as worker resources change;
- speedup/efficiency relative to the baseline;
- resource utilization where reliably measurable;
- model-quality metrics to verify that performance gains do not hide unacceptable quality changes.

The exact framework comparison and dataset will be finalized after feasibility testing. Hadoop MapReduce is treated as a batch-oriented distributed processing framework, while Spark will be evaluated for distributed/iterative processing where the implementation supports a fair comparison.

## Reproducibility
Planned artifacts:
- environment specification;
- dataset acquisition/preparation scripts;
- experiment configuration files;
- training/evaluation code;
- raw run logs/metrics;
- analysis scripts;
- generated tables and figures;
- final research-paper evidence map.

## Research status
Stage 1 — **Project initialized; feasibility and literature validation next.**
