# Integrations

None is currently functional. No credentials were supplied. LLM mode is a deterministic source excerpt compiler and is labelled DEMO. No outbound network request is made by document drafting. Copilot/Glean are not treated as generic model endpoints.

PostgreSQL/pgvector, Redis and MinIO are defined in compose.yaml; no Docker executable was available, and worker, embeddings, uploads and object-storage clients are not implemented. OAuth catalogues in the full product spec are requirements, not configured services. No government portal is scraped; no messaging, meetings or external delivery success is fabricated.

To extend: implement a provider interface with explicit capability/auth/scope/health metadata, server-only secrets, department classification policy, outbound consent, idempotency and audit. Add contract and integration tests using a real configured test tenant before changing status to functional. Revoke credentials through the provider and invalidate stored references when disconnecting.
