# Durable Agent Orchestration

The product includes a SQLite-backed workflow state machine in `app/services/agent_orchestration.py` for bounded planner-to-synthesis execution.

## State contract

Normal analytical workflows advance through:

`PLANNING -> EXECUTION -> SYNTHESIS -> COMPLETED`

If synthesis emits a consequential action request, the workflow instead enters:

`PLANNING -> EXECUTION -> SYNTHESIS -> CONFIRMATION -> COMPLETED`

The `CONFIRMATION` state is persisted as `WAITING_CONFIRMATION`. No consequential action is executed by `request_confirmation`; it only records a bounded action description and pauses the workflow. A human must explicitly approve it through `confirm(..., approved=True)` before completion is permitted. A denial produces terminal `FAILED` with the sanitized error type `HumanConfirmationDenied`.

A terminal `FAILED` state is available when the retry budget is exhausted or confirmation is denied. Invalid transitions are rejected.

## Restart recovery

Workflow state, plan, evidence, result, retry count, confirmation payload, and sanitized error type are persisted in SQLite. Re-opening `AgentWorkflowStore` against the same database preserves a workflow waiting for human confirmation; it is not silently resumed or auto-approved.

## Retry safety

Retries are bounded by `max_retries` (clamped to 0–5). A failed retry keeps the workflow at its current step. Once the retry budget is exhausted the workflow becomes terminal `FAILED` and cannot be retried.

Exception messages are never persisted. Only a bounded exception type is retained, preventing arbitrary dataset values, local paths, or dependency diagnostics from entering the durable workflow record. Confirmation action text is also bounded to 500 characters and each action may reference at most 20 evidence IDs.

## Scope and limitation

This gate is an approval boundary, not an identity, authorization, or audit system. The current product still does not grant the agent arbitrary tools, access to raw HR records, or permission to perform external actions. If consequential integrations are added later, they must invoke this gate and independently authenticate/authorize the approving human before execution.
