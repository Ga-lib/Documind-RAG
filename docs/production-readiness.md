# DocuMind production-readiness plan

## Current baseline

DocuMind currently provides PDF text extraction, chunking, local FastEmbed embeddings, ChromaDB retrieval, Groq generation, and a browser interface. It is a useful single-instance prototype, not yet a multi-customer SaaS.

## Completed in the production-foundation change

- Deployment environment variables now override YAML defaults for model selection, embedding, retrieval, chunking, upload, storage, and logging settings.
- Question payloads are limited to 4,000 characters and source filenames to 255 characters.
- Added tests for configuration precedence and request bounds.

## Required before accepting business customers

1. **Identity and tenant isolation:** Supabase Auth; every document, chunk, conversation, and operation must be scoped to an authenticated tenant/user. The current single shared API key is not customer authentication.
2. **Persistent data:** Move document metadata and source files to Supabase/Postgres and Supabase Storage. Replace local Chroma persistence with a managed Postgres vector store (pgvector) or another shared vector database. The current Render filesystem is ephemeral.
3. **Authorization:** Enforce tenant ownership in every read, upload, delete, and retrieval query. Add database Row Level Security policies and server-side authorization checks.
4. **Abuse and cost controls:** Add per-user rate limits, upload quotas, token/LLM budgets, request timeouts, and concurrency limits using shared infrastructure rather than process-local counters.
5. **Document safety:** Add malware scanning, robust PDF parsing limits, encrypted storage, retention/deletion workflows, and clear handling for scanned PDFs/OCR.
6. **RAG quality:** Add a repeatable evaluation dataset measuring retrieval recall, answer faithfulness, citation correctness, and abstention on unsupported questions.
7. **Operations:** Add readiness checks, structured request IDs, error monitoring, backups, restore tests, alerting, and deployment rollback procedures.
8. **Business operations:** Add plans/billing, usage dashboards, customer support workflows, terms/privacy disclosures, and audit logs before charging customers.

## Infrastructure prerequisites

- A Supabase project with Auth, Postgres/pgvector, and Storage enabled.
- Supabase project URL and publishable/anon key for the client.
- Supabase service-role key configured only as a protected Render secret; never commit it or expose it in browser code.
- A persistent production deployment and a backup/restore policy.

## Rollout sequence

- Phase 1: Configuration and request-boundary hardening (this change).
- Phase 2: Supabase Auth, tenant-aware schema, RLS, and private file storage.
- Phase 3: Managed vector retrieval, migrations, re-indexing, and persistence verification.
- Phase 4: Rate limits, quotas, monitoring, backups, and security testing.
- Phase 5: RAG evaluation, billing, and controlled customer beta.

Do not describe the service as production-ready until tenant isolation, persistence, security, recovery, and RAG evaluation have passed explicit tests.