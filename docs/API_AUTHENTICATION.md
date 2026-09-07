# API authentication

The service supports an optional API-key boundary for deployments that expose the API beyond a trusted local process.

## Configuration

Set `HR_ANALYTICS_API_KEY` to a non-empty secret. When it is set, every `/api/*` endpoint except `/api/health` requires the HTTP header `X-API-Key` with the exact configured value.

When `HR_ANALYTICS_API_KEY` is unset, authentication is disabled to preserve the local-development MVP behavior.

## Security properties

- API keys are compared with a constant-time comparison.
- Missing and incorrect credentials receive the same `401 Authentication required` response.
- `/api/health` remains public for liveness/readiness probes.
- Authentication failures are rejected before dataset processing.
- The API key is never returned by the application.

## Scope and limitation

This is an application-wide shared-secret boundary, **not** multi-user identity, tenant isolation, role-based authorization, or per-user dataset ownership. Those remain separate production-hardening work. Do not treat the shared API key as sufficient for a multi-tenant HR deployment.
