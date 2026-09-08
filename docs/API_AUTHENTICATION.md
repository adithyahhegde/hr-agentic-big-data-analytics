# API authentication

The service supports API-key authentication for deployments that expose the API beyond a trusted local process. When per-user credentials are configured, the authenticated credential also establishes the request identity used for durable dataset ownership checks.

## Configuration

### Single-user / legacy mode

Set `HR_ANALYTICS_API_KEY` to a non-empty secret. When it is set, every `/api/*` endpoint except `/api/health` requires the HTTP header `X-API-Key` with the exact configured value. The authenticated identity is `local`.

### Multi-user mode

Set `HR_ANALYTICS_API_KEYS` using the form:

```text
alice=secret-for-alice;bob=secret-for-bob
```

Each entry maps one validated user identifier to one API credential. When `HR_ANALYTICS_API_KEYS` is non-empty, it takes precedence over `HR_ANALYTICS_API_KEY`; a valid credential determines the request identity and client-supplied user headers are not trusted.

When neither credential setting is configured, authentication remains disabled to preserve local-development MVP behavior. In that mode the durable registry uses the default `local` identity and must not be treated as a production multi-tenant deployment.

## Security properties

- API keys are compared with constant-time comparison.
- Missing and incorrect credentials receive the same `401 Authentication required` response.
- `/api/health` remains public for liveness/readiness probes.
- Authentication failures are rejected before dataset processing.
- Authenticated identity is stored only in request-scoped context and reset after the request completes.
- Dataset manifests, profiles, and confirmed mappings are filtered by authenticated owner.
- A client cannot select another owner by sending a user-id header.
- API credentials are never returned by the application.

## Scope and limitation

This provides lightweight application-level identity and dataset isolation, but it is **not** a full production IAM system. It does not provide password login, token rotation, external identity-provider integration, granular roles/permissions, organization administration, or secret storage. Use a proper identity provider and secret-management system for production deployments. Human confirmation still requires an explicit approval action; authentication establishes identity but does not itself grant consequential-action approval.
