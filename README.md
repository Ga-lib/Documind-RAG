# DocuMind RAG

A production-style Retrieval-Augmented Generation (RAG) system for document question-answering — upload PDFs, ask questions, get grounded answers with source citations. Built end-to-end with a REST API, a web UI, Docker deployment, and automated tests.

**Zero-cost stack**: local embeddings (Sentence-Transformers) + free-tier LLM (Groq) + embedded vector database (ChromaDB) — no paid API keys required to run this project.

---
<img width="1919" height="920" alt="image" src="https://github.com/user-attachments/assets/770c14ce-d51f-4579-9727-02ee6603f08b" />

## Features

- 📄 **PDF upload & indexing** — automatic text extraction, chunking, and embedding
- 🔍 **Semantic search** — top-k similarity and MMR (diversity-aware) retrieval strategies
- 🚫 **Anti-hallucination guardrails** — the LLM is instructed to answer only from retrieved context, and explicitly says so when documents don't contain an answer
- 📌 **Source citations** — every answer references the specific document chunk it came from
- 🔁 **Duplicate detection** — prevents re-indexing the same document
- 💬 **Web UI** — drag-and-drop upload, chat-style Q&A, per-document filtering
- 🐳 **Dockerized** — one-command startup with `docker compose up`
- ✅ **Automated tests** — pytest coverage for chunking and PDF loading
- 📊 **Structured JSON logging** — request/error/timing visibility throughout the pipeline
- ⚙️ **Fully configurable** — chunk size, retrieval strategy, model choice, etc. via `config.yaml` + `.env`

---

## Architecture

```
                    ┌─────────────┐
                    │   Browser   │
                    │  (Web UI)   │
                    └──────┬──────┘
                           │ HTTP
                    ┌──────▼──────┐
                    │   FastAPI   │
                    │  (API layer)│
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Services   │  ← orchestration, no HTTP knowledge
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
  ┌─────▼─────┐     ┌─────▼─────┐      ┌─────▼─────┐
  │  Loader   │────▶│  Chunker  │─────▶│  Embedder │
  │  (pypdf)  │     │(recursive)│      │(Sentence- │
  └───────────┘     └───────────┘      │Transform.)│
                                        └─────┬─────┘
                                              │
                                        ┌─────▼─────┐
                                        │  ChromaDB │
                                        │ (persist.)│
                                        └─────┬─────┘
                                              │
                                        ┌─────▼─────┐
                                        │ Retriever │  top-k / MMR
                                        └─────┬─────┘
                                              │
                                        ┌─────▼─────┐
                                        │ Generator │  Groq (Llama 3.3 70B)
                                        └─────┬─────┘
                                              │
                                     Answer + Citations
```

Each pipeline stage (loading, chunking, embedding, storage, retrieval, generation) is isolated behind its own module, so any component can be swapped independently — e.g. ChromaDB → Pinecone, or Groq → OpenAI — without touching the rest of the system.

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| API | FastAPI | Async, auto-validated, auto-documented (Swagger) |
| Embeddings | Sentence-Transformers (`all-MiniLM-L6-v2`) | Free, local, fast on CPU, strong quality-per-compute |
| Vector DB | ChromaDB | Embedded, persistent, zero infra to deploy |
| LLM | Groq (Llama 3.3 70B) | Free tier, no credit card, extremely fast inference |
| Chunking | LangChain `RecursiveCharacterTextSplitter` | Preserves semantic boundaries over naive fixed-size cuts |
| Config | Pydantic Settings + YAML | Secrets (`.env`) separated from tunable parameters (`config.yaml`) |
| Deployment | Docker + Docker Compose | One-command, reproducible startup |
| Testing | pytest | Automated coverage of chunking and PDF-loading logic |

---

## Getting Started

### Option A: Docker (recommended)

**Prerequisites**: Docker Desktop, a free [Groq API key](https://console.groq.com/keys)

```bash
git clone <your-repo-url>
cd documind-rag
cp .env.example .env   # then add your GROQ_API_KEY
docker compose up -d
```

Visit `http://localhost:8000` for the web UI, or `http://localhost:8000/docs` for the API docs.

### Option B: Local development

**Prerequisites**: Python 3.12, a free [Groq API key](https://console.groq.com/keys)

```bash
git clone <your-repo-url>
cd documind-rag
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env            # then add your GROQ_API_KEY
uvicorn app.main:app --reload
```

Visit `http://localhost:8000`.

---

## API Usage

### Upload a document
```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@document.pdf"
```

### Ask a question
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What does this document cover?"}'
```

**Response:**
```json
{
  "question": "What does this document cover?",
  "answer": "...",
  "sources": [
    {
      "source_number": 1,
      "filename": "document.pdf",
      "chunk_index": 2,
      "text_snippet": "...",
      "distance": 0.47
    }
  ]
}
```

### List documents
```bash
curl http://localhost:8000/documents
```

### Delete a document
```bash
curl -X DELETE http://localhost:8000/documents/document.pdf
```

Full interactive API docs available at `/docs` once the server is running.

---

## Project Structure

```
app/
├── api/routes/        # HTTP endpoints
├── models/schemas.py  # Pydantic request/response models
├── services/           # Orchestration layer (API-agnostic business logic)
├── rag/
│   ├── loader/         # PDF → text
│   ├── chunking/       # Text → chunks (fixed & recursive strategies)
│   ├── embeddings/     # Chunks → vectors
│   ├── retriever/      # Query → relevant chunks (top-k / MMR)
│   └── generator/       # Chunks + question → grounded answer
├── vectorstore/        # ChromaDB wrapper
├── config/              # Settings loader (.env + config.yaml)
├── utils/               # Logging, exceptions, hashing
└── static/               # Web frontend (HTML/CSS/JS)
tests/                    # pytest unit tests
scripts/                  # Manual testing / CLI utilities
```

---

## Configuration

Non-secret settings live in `app/config/config.yaml` (chunk size, retrieval strategy, model names). Secrets live in `.env` (API keys). See `.env.example` for required variables.

---

## Running Tests

```bash
pip install -r requirements-dev.txt
pytest
```

---

## Design Decisions

- **Chunking**: recursive splitting (paragraph → sentence → word boundaries) is the default over fixed-size chunking, since it keeps chunks semantically coherent rather than cutting mid-sentence.
- **Retrieval**: configurable between plain top-k similarity (fast) and MMR (diversity-aware, avoids near-duplicate context) — controlled via `config.yaml`.
- **Prompting**: the system prompt explicitly instructs the LLM to answer only from retrieved context and to say so when it can't — this is the primary defense against hallucination.
- **Free-tier design**: every component (embeddings, vector DB, LLM) runs at zero cost, making the project fully reproducible without a paid API key.

---

## Future Improvements

- Streaming responses (token-by-token) instead of waiting for the full answer
- Conversation history / multi-turn context
- Content-hash-based duplicate detection (currently filename-based)
- Additional test coverage for the retriever and API layers with mocked external calls
- Support for additional document types beyond PDF

---

## License

MIT — see [LICENSE](LICENSE).
