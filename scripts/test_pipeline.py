"""
Manual end-to-end test script for the RAG pipeline, using the service layer.
Run with: python scripts/test_pipeline.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.qa_service import QAService
from app.services.document_service import DocumentService


def main():
    doc_service = DocumentService()
    qa_service = QAService()

    print("=== Indexed documents ===")
    print(doc_service.list_documents())
    print()

    question = "What machine learning projects has this person worked on?"
    answer, citations = qa_service.ask(question)

    print("=== ANSWER ===")
    print(answer)
    print()
    print(f"=== SOURCES ({len(citations)}) ===")
    for c in citations:
        print(f"Source {c.source_number}: {c.filename} (chunk {c.chunk_index}, distance={c.distance:.4f})")


if __name__ == "__main__":
    main()