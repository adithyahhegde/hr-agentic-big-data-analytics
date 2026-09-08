# Durable Agent Orchestration

The product now includes a SQLite-backed workflow state machine in `app/services/agent_orchestration.py` for bounded planner-to-synthesis execution.

## State contract

A workflow advances only through:

`PLANNING -> EXECUTION -> SYNTHESIS -> COMPLETED`

A terminal `FAILED` state is available when the retry budget is exhausted. Invalid transitions are rejected.

## Restart recovery

Workflow state, plan, evidence, result, retry count, and sanitized error type are persisted in SQLite. Re-opening `AgentWorkflowStore` against the same database recovers an unfinished `RUNNING` workflow at its last persisted step rather than restarting from scratch.

## Retry safety

Retries are bounded by `max_retries` (clamped to 0–5). A failed retry keeps the workflow at its current step. Once the retry budget is exhausted the workflow becomes terminal `FAILED` and cannot be retried.

Exception messages are never persisted. Only a bounded exception type is retained, preventing arbitrary dataset values, local paths, or dependency diagnostics from entering the durable workflow record.

## Scope and limitation

This state machine is deliberately orchestration infrastructure, not an autonomous executor. The current product still requires explicit analytical services and human-controlled consequential actions. It does not grant the agent arbitrary tools, access to raw HR records, or permission to perform external actions. Human confirmation remains required before any future consequential action integration.
