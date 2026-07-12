"""
Manual end-to-end test script for the RAG pipeline.
Run with: python scripts/test_pipeline.py
"""

import sys
from pathlib import Path

# Add the project root (one level up from scripts/) to Python's import path,
# so "from app..." imports work regardless of which directory this script
# is run from.
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag.retriever.retriever import Retriever
from app.rag.generator.generator import Generator


def main():
    retriever = Retriever()
    generator = Generator()

    question = "What machine learning projects has this person worked on?"
    chunks = retriever.retrieve(question, top_k=3)
    result = generator.generate(question, chunks)

    print()
    print("=== ANSWER ===")
    print(result.answer)
    print()
    print(f"=== SOURCES ({len(result.sources)}) ===")
    for i, source in enumerate(result.sources, start=1):
        filename = source.metadata.get("source_filename")
        chunk_index = source.metadata.get("chunk_index")
        print(f"Source {i}: {filename} (chunk {chunk_index})")


if __name__ == "__main__":
    main()