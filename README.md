# DocuMind RAG

A Retrieval-Augmented Generation (RAG) application for PDF question-answering. Upload documents, retrieve relevant passages, and generate answers with source citations.

**Stack:** FastAPI, Sentence-Transformers, ChromaDB, Groq, Pydantic Settings, Docker.

## Features

- PDF text extraction and configurable recursive/fixed chunking
- Local embeddings using `all-MiniLM-L6-v2`
- ChromaDB persistent vector storage
- Similarity and Maximal Marginal Relevance (MMR) retrieval
- Groq-powered answers with retrieved source citations
- Content-hash duplicate detection and bounded PDF uploads
- Optional API-key protection in development; required in production
- Browser UI, Docker support, and pytest tests

## Architecture

```text
Browser / API client
       |
     FastAPI ---- API-key dependency
       |
  Application services
       |
 PDF loader -> Chunker -> Embedder -> ChromaDB
                                  |
Question -> Retriever -> Context -> Groq -> Answer + citations
```

## Requirements

- Python 3.12
- Groq API key: https://console.groq.com/keys
- Docker (optional)

## Local setup

```bash
git clone https://github.com/Ga-lib/Documind-RAG.git
cd Documind-RAG
python -m venv .venv
# Windows PowerShell:
.venv\\Scripts\\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env
```

Add your Groq key to `.env`:

```dotenv
GROQ_API_KEY=your_groq_api_key_here
```

Start the API:

```bash
uvicorn app.main:app --reload
```

Open http://localhost:8000 for the UI and http://localhost:8000/docs for Swagger.

In development, the API key is optional. To protect a local instance, set `DOCUMIND_API_KEY` to a random secret of at least 24 characters. The UI will request it on first protected request and retain it only for the browser session.

## Production configuration

Set `ENVIRONMENT=production` (or set `app.environment: "production"` in `app/config/config.yaml`) and configure these environment variables in your deployment platform:

```dotenv
GROQ_API_KEY=your_groq_api_key
ENVIRONMENT=production
DOCUMIND_API_KEY=your_long_random_secret_at_least_24_chars
```

The application refuses to start in production without `DOCUMIND_API_KEY`. Protected endpoints require the `X-API-Key` header. Generate a secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

This is a single shared API key, not multi-user authentication. Do not use it as a substitute for user accounts, per-user document isolation, rate limiting, or a managed identity system when serving multiple customers.

## Docker

```bash
docker compose up --build -d
```

The Compose service reads `.env` and persists the `data/` directory. Ensure your deployment platform mounts persistent storage at `/app/data`; otherwise the ChromaDB index can be lost when the container is replaced.

## API

When API-key protection is enabled, include `X-API-Key` on protected requests.

Upload a PDF:

```bash
curl -X POST http://localhost:8000/upload \\
  -H "X-API-Key: $DOCUMIND_API_KEY" \\
  -F "file=@document.pdf"
```

Ask a question:

```bash
curl -X POST http://localhost:8000/ask \\
  -H "X-API-Key: $DOCUMIND_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"question":"What does this document discuss?"}'
```

List documents:

```bash
curl http://localhost:8000/documents -H "X-API-Key: $DOCUMIND_API_KEY" -H "X-API-Key: $DOCUMIND_API_KEY"
```

Delete a document:

```bash
curl -X DELETE "http://localhost:8000/documents/document.pdf" \\
  -H "X-API-Key: $DOCUMIND_API_KEY"
```

Health check is intentionally unauthenticated at `/health`. Interactive API documentation is available at `/docs`.

## Configuration

Non-secret settings are in `app/config/config.yaml`. Secrets belong in environment variables or `.env`; never commit `.env`.

Important settings include:

- `chunking.strategy`, `chunk_size`, and `chunk_overlap`
- `embeddings.model_name` and `batch_size`
- `retrieval.search_type`, `top_k`, and `mmr_diversity`
- `llm.model`, `temperature`, `max_tokens`, and `timeout_seconds`
- `upload.max_file_size_mb`

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Known limitations

- PDF image OCR is not implemented; scanned PDFs without a text layer are rejected.
- Authentication is a single shared API key; no user accounts or per-user data partitioning.
- No rate limiting or request quotas are included.
- ChromaDB is suitable for a small single-instance deployment; multi-replica deployments need a shared vector database.
- RAG answer quality still needs a representative evaluation dataset and measured retrieval/generation metrics.

## License

MIT.
