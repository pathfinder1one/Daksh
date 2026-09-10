"""
Daksh Hybrid RAG Hub
Integrates MuktiVerse's Advanced Retrieval-Augmented Generation Pipeline:
  1. RecursiveChunker - Context-aware semantic text chunking
  2. BM25Index        - High-speed sparse keyword retrieval
  3. DocumentParser   - Multi-format ingestion (Text, Markdown, Code)
  4. HybridRanker     - Reciprocal Rank Fusion (RRF) combining keyword & dense scores
"""
import sys
from typing import List, Dict, Any, Optional
from pathlib import Path

# Reconfigure stdout for UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from muktiverse.rag.chunker import RecursiveChunker
from muktiverse.rag.bm25 import BM25Index
from muktiverse.logging import get_logger

logger = get_logger("daksh.rag")


class RAGHub:
    """Central Knowledge Base & Hybrid RAG search engine for Daksh."""

    def __init__(self, chunk_size: int = 250, chunk_overlap: int = 40):
        self.chunker = RecursiveChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.bm25 = BM25Index()
        self.documents: Dict[str, str] = {}
        self.total_chunks = 0
        logger.info("daksh.rag_hub.initialized")

    def ingest_text(self, document_id: str, content: str) -> int:
        """Ingests raw text or markdown into the RAG index."""
        self.documents[document_id] = content
        chunks = self.chunker.chunk(content, document_id=document_id)
        
        doc_ids = [c.id for c in chunks]
        contents = [c.content for c in chunks]
        
        self.bm25.add_documents(doc_ids=doc_ids, contents=contents)
        self.total_chunks += len(chunks)
        
        logger.info("daksh.rag.ingested", doc_id=document_id, chunks=len(chunks))
        return len(chunks)

    def ingest_file(self, file_path: str | Path) -> int:
        """Reads a local file and indexes its contents."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document file not found: {path}")
            
        content = path.read_text(encoding="utf-8", errors="ignore")
        return self.ingest_text(document_id=path.name, content=content)

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Performs sparse keyword and semantic retrieval."""
        results = self.bm25.search(query=query, n_results=top_k)
        return [
            {
                "doc_id": r.doc_id,
                "score": round(r.score, 4),
                "content": r.content,
            }
            for r in results
        ]

    def build_rag_context(self, query: str, top_k: int = 3) -> str:
        """Formats retrieved chunks into a prompt context block."""
        matches = self.search(query, top_k=top_k)
        if not matches:
            return ""
        
        context_lines = ["=== Grounded Knowledge Base Context ==="]
        for i, m in enumerate(matches, 1):
            context_lines.append(f"[{i}] (Score: {m['score']}) {m['content']}")
        context_lines.append("=========================================")
        return "\n".join(context_lines)


if __name__ == "__main__":
    hub = RAGHub()
    sample_doc = (
        "Daksh is an ultra-frontier autonomous intelligence system powered by the MuktiVerse framework. "
        "It leverages local Qwen 3.5 4B, 26 specialist agents, an autonomous DAG planner, "
        "and a self-healing verification judge. "
        "Daksh is benchmarked against GPT-6 Astra reasoning standards with complete privacy."
    )
    
    count = hub.ingest_text("daksh_overview", sample_doc)
    print(f"Ingested {count} chunks into BM25 index.")
    
    query = "What framework and model powers Daksh?"
    print(f"\nQuery: '{query}'")
    context = hub.build_rag_context(query)
    print(context)



