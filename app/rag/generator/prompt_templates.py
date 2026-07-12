"""
Prompt templates for the generation step.

The system prompt is the primary defense against hallucination: it forces
the LLM to answer strictly from retrieved context and to explicitly admit
when the context doesn't contain the answer, rather than guessing.
"""

from app.vectorstore.chroma_store import StoredChunk

SYSTEM_PROMPT = """You are a precise document question-answering assistant.

Rules you must follow strictly:
1. Answer ONLY using the information in the "Context" section below.
2. Do NOT use any outside knowledge, even if you are confident it is correct.
3. If the context does not contain enough information to answer the question, \
respond exactly with: "The documents do not contain enough information to \
answer this question." Do not guess or fill gaps with assumptions.
4. When you do answer, mention which source number(s) (e.g. "Source 1") \
support each claim you make.
5. Be concise. Do not repeat the context verbatim; synthesize it into a \
direct answer.
"""


def build_context_block(chunks: list[StoredChunk]) -> str:
    """
    Format retrieved chunks into a numbered context block the LLM can
    cite back to (e.g. "Source 1", "Source 2"), which is what allows us
    to return source citations to the end user afterward.
    """
    if not chunks:
        return "No relevant context was found."

    parts = []
    for i, chunk in enumerate(chunks, start=1):
        source_name = chunk.metadata.get("source_filename", "unknown")
        parts.append(f"[Source {i}: {source_name}]\n{chunk.text}")
    return "\n\n".join(parts)


def build_user_prompt(question: str, chunks: list[StoredChunk]) -> str:
    """Build the full user-turn prompt: context block + the actual question."""
    context_block = build_context_block(chunks)
    return f"""Context:
{context_block}

Question: {question}

Answer the question using only the context above, following the system rules."""