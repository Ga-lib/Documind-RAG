# DocuMind RAG

DocuMind RAG is a PDF question-answering application. Users sign in, upload PDFs, and ask questions grounded in retrieved document passages with source citations.

## Production architecture

- **Frontend:** lightweight responsive browser UI served by FastAPI
- **API:** FastAPI with authenticated document and question-answering routes
- **Authentication:** Supabase Auth; API requests carry the signed-in user's access token
- **File storage:** private Supabase Storage bucket
- **Metadata and vectors:** Supabase Postgres with pgvector and row-level security
- **Embeddings:** FastEmbed / ONNX Runtime to keep the service's memory footprint small
- **Generation:** Groq API (configured through `GROQ_MODEL`)

Document and chunk queries are scoped to the authenticated user. The vector-search function only returns chunks belonging to that user and to documents in the `ready` state.

## Features

- Email sign-up, sign-in, and sign-out through Supabase Auth
- PDF upload with a configurable size limit (20 MB by default)
- PDF validation, text extraction, chunking, and embedding
- Private per-user document storage
- Duplicate filename and content detection per user
- Document listing and deletion using stable document UUIDs
- RAG question answering with source citations
- Optional restriction of a question to one document using its UUID
- Docker deployment and health endpoint

Scanned PDFs that contain only page images are not OCR-processed.

## Required services and configuration

Create a Supabase project and a Groq API key. Configure the Supabase database schema, pgvector RPC, private Storage bucket, RLS policies, and Auth redirect URLs for the deployed application.

Set these environment variables in the deployment environment:

| Variable | Required | Purpose |
|---|---|---|
| `GROQ_API_KEY` | Yes | Groq API access |
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_ANON_KEY` | Yes | Supabase publishable key (safe for browser use) |
| `SUPABASE_BUCKET` | No | Private Storage bucket; defaults to `documind-documents` |
| `ENVIRONMENT` | Recommended | Set to `production` |
| `GROQ_MODEL` | No | Generation model; defaults to `openai/gpt-oss-120b` |
| `MAX_FILE_SIZE_MB` | No | Upload limit; defaults to `20` |
| `TOP_K` | No | Default retrieval count; defaults to `4` |
| `LOG_LEVEL` | No | Application log level; defaults to `INFO` |
| `LOG_FORMAT` | No | `json` or `text`; defaults to `json` |
| `SUPABASE_TIMEOUT_SECONDS` | No | Supabase request timeout; defaults to `20` |

Never put a Supabase service-role key, secret key, database password, or user access token in frontend code or commit one to the repository. The browser only receives the Supabase URL and publishable key through `/config`.

## Run locally

1. Install Python 3.12 and create a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with the required values:
   ```dotenv
   GROQ_API_KEY=your_groq_api_key
   SUPABASE_URL=https://your-project-ref.supabase.co
   SUPABASE_ANON_KEY=your_supabase_publishable_key
   SUPABASE_BUCKET=documind-documents
   ENVIRONMENT=development
   ```
4. Start the application:
   ```bash
   uvicorn app.main:app --reload
   ```
5. Open http://localhost:8000.

For local authentication, add your local frontend origin to the Supabase Auth redirect URL allowlist. Use the actual local origin shown by your development server.

## API overview

Protected endpoints require:

```http
Authorization: Bearer <supabase-user-access-token>
```

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Application health check |
| `GET` | `/config` | Public frontend configuration (Supabase URL and publishable key only) |
| `POST` | `/upload` | Upload and index a PDF as multipart field `file` |
| `GET` | `/documents` | List the signed-in user's ready documents |
| `DELETE` | `/documents/{document_id}` | Delete a document by UUID |
| `POST` | `/ask` | Ask a question about the user's indexed documents |

Example question request:

```json
{
  "question": "What are the main findings?",
  "top_k": 4,
  "source_document_id": "optional-document-uuid"
}
```

The `source_document_id` field is optional. When supplied, retrieval is restricted to that document. Document IDs are returned by `GET /documents`.

Interactive API documentation is available at `/docs` when enabled by the deployment.

## Deployment

The repository includes a Dockerfile and is configured for deployment as a Render web service. Configure the environment variables above, use `/health` as the health-check path, and ensure the Supabase project has the required schema, policies, and private bucket before accepting user uploads.

The current hosted instance is:

https://documind-rag-vled.onrender.com

## Security notes and known limitations

- Keep the Supabase Storage bucket private.
- Keep RLS enabled on the document and chunk tables. Policies must enforce ownership using the authenticated user's ID.
- Do not expose privileged Supabase keys in the browser.
- Leaked-password protection is a Supabase Auth project setting and depends on the Supabase plan.
- Rate limiting, per-user quotas, billing, and an administrative console are not yet implemented.
- OCR for scanned/image-only PDFs is not implemented.
- RAG quality still needs evaluation against a representative question-and-answer dataset.
- The current Render service uses the free plan; cold starts and resource limits may affect response time.

## Tests

Install the development dependencies and run:

```bash
pip install -r requirements-dev.txt
pytest
```

## License

MIT.
