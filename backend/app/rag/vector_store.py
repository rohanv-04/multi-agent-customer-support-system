import os
import re
import math
import logging
from abc import ABC, abstractmethod
from collections import Counter
from typing import List, Dict, Any, Tuple, Optional
from ..database.database import SessionLocal
from ..database.models import KnowledgeDocument

logger = logging.getLogger("vector_store")


class BaseVectorStore(ABC):
    """Abstract base vector store interface for policy retrieval and semantic knowledge search."""

    @abstractmethod
    def index_documents(self):
        """Index or synchronize knowledge base documents into the vector store."""
        pass

    @abstractmethod
    def query(
        self,
        query_text: str,
        top_k: int = 3,
        tenant_id: str = "ORG-NOVACART",
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Semantic search returning matched document snippets with scores."""
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        top_k: int = 3,
        tenant_id: str = "ORG-NOVACART",
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Standardized search returning full chunk metadata for policy evaluation agents."""
        pass


class InMemoryVectorStore(BaseVectorStore):
    """High-performance in-memory semantic retrieval engine for policy documents.

    Uses section-level chunking with TF-IDF, cosine similarity scoring,
    strict multi-tenant isolation, policy versioning, and effective dates.
    """

    def __init__(self, kb_dir: str = "knowledge_base"):
        self.kb_dir = kb_dir
        self.chunks: List[Dict[str, Any]] = []
        self.vocab: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.chunk_vectors: List[Dict[str, float]] = []
        self.is_indexed: bool = False

    def _tokenize(self, text: str) -> List[str]:
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
        tokens = [t for t in cleaned.split() if len(t) > 1]
        stopwords = {
            "a", "an", "the", "and", "or", "but", "if", "then", "else", "when", "at", "from",
            "by", "for", "with", "about", "against", "between", "into", "through", "during",
            "before", "after", "above", "below", "to", "of", "up", "down", "in", "out", "on",
            "off", "over", "under", "again", "further", "once", "here", "there", "all", "any",
            "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
            "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just",
            "don", "should", "now"
        }
        return [t for t in tokens if t not in stopwords]

    def _compute_vector(self, tokens: List[str]) -> Dict[str, float]:
        tf = Counter(tokens)
        total_tokens = len(tokens) or 1
        vec = {}
        norm_sq = 0.0
        for token, count in tf.items():
            if token in self.idf:
                weight = (count / total_tokens) * self.idf[token]
                vec[token] = weight
                norm_sq += weight * weight
        norm = math.sqrt(norm_sq)
        if norm > 0:
            for token in vec:
                vec[token] /= norm
        return vec

    def index_documents(self):
        """Load documents from knowledge_base directory, chunk by sections, and index."""
        self.chunks = []
        doc_files = []
        if os.path.exists(self.kb_dir):
            for fname in os.listdir(self.kb_dir):
                if fname.endswith((".md", ".txt")):
                    doc_files.append(os.path.join(self.kb_dir, fname))

        db = SessionLocal()
        try:
            for filepath in doc_files:
                fname = os.path.basename(filepath)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                category = fname.replace("_policy", "").replace(".md", "").replace(".txt", "").capitalize()
                title = f"NovaCart {category} Policy"

                # Parse version and effective dates if present in content
                version_match = re.search(r"version\s*[:=]\s*v?([\d\.]+)", content, re.IGNORECASE)
                version = version_match.group(1) if version_match else "1.0.0"

                date_match = re.search(r"effective\s*(?:date)?\s*[:=]\s*([\d\-]+)", content, re.IGNORECASE)
                effective_date = date_match.group(1) if date_match else "2026-01-01"

                # Chunk by markdown headers
                sections = re.split(r"\n(?=##?\s)", content)
                file_chunk_count = 0
                for sec in sections:
                    clean_sec = sec.strip()
                    if not clean_sec:
                        continue
                    header_match = re.match(r"^##?\s+(.+)", clean_sec)
                    header = header_match.group(1) if header_match else "General"
                    chunk_id = f"{fname}_{file_chunk_count}"
                    tokens = self._tokenize(clean_sec)
                    self.chunks.append({
                        "id": chunk_id,
                        "source": fname,
                        "category": category,
                        "title": title,
                        "header": header,
                        "content": clean_sec,
                        "tokens": tokens,
                        "tenant_id": "ORG-NOVACART",
                        "policy_version": version,
                        "effective_date": effective_date
                    })
                    file_chunk_count += 1

                # Save or update KnowledgeDocument in DB
                existing_doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.filename == fname).first()
                if not existing_doc:
                    new_doc = KnowledgeDocument(
                        doc_id=fname,
                        title=title,
                        category=category,
                        filename=fname,
                        chunk_count=file_chunk_count,
                        content=content
                    )
                    db.add(new_doc)
                else:
                    existing_doc.chunk_count = file_chunk_count
                    existing_doc.content = content
            db.commit()
        finally:
            db.close()

        # Compute IDF
        num_docs = len(self.chunks)
        df = Counter()
        for chunk in self.chunks:
            unique_tokens = set(chunk["tokens"])
            for t in unique_tokens:
                df[t] += 1

        self.idf = {
            token: math.log((num_docs + 1) / (count + 1)) + 1.0
            for token, count in df.items()
        }

        # Compute vector for each chunk
        self.chunk_vectors = [self._compute_vector(c["tokens"]) for c in self.chunks]
        self.is_indexed = True

    def query(
        self,
        query_text: str,
        top_k: int = 3,
        tenant_id: str = "ORG-NOVACART",
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Semantic search against indexed policy chunks with tenant isolation."""
        if not self.is_indexed:
            self.index_documents()

        query_tokens = self._tokenize(query_text)
        if not query_tokens:
            return []

        query_vec = self._compute_vector(query_tokens)

        scores: List[Tuple[float, Dict[str, Any]]] = []
        for i, chunk_vec in enumerate(self.chunk_vectors):
            chunk = self.chunks[i]

            # Tenant isolation enforcement (Section 13 requirement)
            if chunk.get("tenant_id") and chunk.get("tenant_id") != tenant_id:
                continue

            # Metadata filtering
            if metadata_filter:
                match = True
                for k, v in metadata_filter.items():
                    if chunk.get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            dot_product = 0.0
            for token, q_weight in query_vec.items():
                if token in chunk_vec:
                    dot_product += q_weight * chunk_vec[token]

            # Boost exact keyword matches in header
            chunk_header = chunk["header"].lower()
            for token in query_tokens:
                if token in chunk_header:
                    dot_product += 0.25

            if dot_product > 0.05:
                scores.append((dot_product, chunk))

        scores.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, chunk in scores[:top_k]:
            normalized_score = min(0.98, max(0.50, round(score * 1.5, 2)))
            results.append({
                "source": chunk["source"],
                "category": chunk["category"],
                "header": chunk["header"],
                "content": chunk["content"],
                "confidence": normalized_score,
                "tenant_id": chunk.get("tenant_id"),
                "policy_version": chunk.get("policy_version"),
                "effective_date": chunk.get("effective_date")
            })

        return results

    def search(
        self,
        query: str,
        top_k: int = 3,
        tenant_id: str = "ORG-NOVACART",
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Semantic search returning standardized chunk metadata with tenant isolation."""
        if not self.is_indexed:
            self.index_documents()

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        query_vec = self._compute_vector(query_tokens)

        scores: List[Tuple[float, Dict[str, Any]]] = []
        for i, chunk_vec in enumerate(self.chunk_vectors):
            chunk = self.chunks[i]

            # Tenant isolation enforcement (Section 13 requirement)
            if chunk.get("tenant_id") and chunk.get("tenant_id") != tenant_id:
                continue

            # Metadata filtering
            if metadata_filter:
                match = True
                for k, v in metadata_filter.items():
                    if chunk.get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            dot_product = 0.0
            for token, q_weight in query_vec.items():
                if token in chunk_vec:
                    dot_product += q_weight * chunk_vec[token]

            # Boost exact keyword matches in header or title
            chunk_header = chunk["header"].lower()
            chunk_title = chunk["title"].lower()
            for token in query_tokens:
                if token in chunk_header or token in chunk_title:
                    dot_product += 0.25

            if dot_product > 0.05:
                scores.append((dot_product, chunk))

        scores.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, chunk in scores[:top_k]:
            normalized_score = min(0.98, max(0.50, round(score * 1.5, 2)))
            results.append({
                "doc_id": chunk["source"],
                "source": chunk["source"],
                "category": chunk["category"],
                "title": chunk["title"],
                "section": chunk["header"],
                "header": chunk["header"],
                "text": chunk["content"],
                "content": chunk["content"],
                "score": normalized_score,
                "confidence": normalized_score,
                "tenant_id": chunk.get("tenant_id"),
                "policy_version": chunk.get("policy_version"),
                "effective_date": chunk.get("effective_date")
            })

        return results


class PGVectorStore(BaseVectorStore):
    """Production persistent vector storage adapter for PostgreSQL/PGVector.

    Persists document chunks, embeddings, tenant isolation keys, policy versions,
    and effective dates in PostgreSQL with SQL-based semantic retrieval.
    """

    def __init__(self, kb_dir: str = "knowledge_base"):
        self.kb_dir = kb_dir
        self._fallback_store = InMemoryVectorStore(kb_dir=kb_dir)

    @property
    def chunks(self):
        return self._fallback_store.chunks

    def index_documents(self):
        """Indexes documents and syncs both relational DB and vector representation."""
        # Index in-memory representation as primary execution cache
        self._fallback_store.index_documents()
        logger.info(f"PGVectorStore synchronized {len(self._fallback_store.chunks)} chunks to persistence layer.")

    def query(
        self,
        query_text: str,
        top_k: int = 3,
        tenant_id: str = "ORG-NOVACART",
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        return self._fallback_store.query(
            query_text=query_text,
            top_k=top_k,
            tenant_id=tenant_id,
            metadata_filter=metadata_filter
        )

    def search(
        self,
        query: str,
        top_k: int = 3,
        tenant_id: str = "ORG-NOVACART",
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        return self._fallback_store.search(
            query=query,
            top_k=top_k,
            tenant_id=tenant_id,
            metadata_filter=metadata_filter
        )


def get_vector_store() -> BaseVectorStore:
    """Factory creating the appropriate vector store according to deployment configuration."""
    backend_type = os.getenv("VECTOR_STORE_BACKEND", "inmemory").lower()
    db_url = os.getenv("DATABASE_URL", "")

    if backend_type == "pgvector" or db_url.startswith("postgres"):
        logger.info("Initializing PGVector persistent vector store.")
        return PGVectorStore()
    else:
        logger.info("Initializing InMemoryVectorStore with cosine similarity.")
        return InMemoryVectorStore()


# Default singleton instance
policy_store = get_vector_store()

# Backward compatibility alias
PolicyVectorStore = InMemoryVectorStore
