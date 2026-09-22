import os
import re
import math
from collections import Counter
from typing import List, Dict, Any, Tuple
from ..database.database import SessionLocal
from ..database.models import KnowledgeDocument

class PolicyVectorStore:
    """A high-performance semantic retrieval engine for NovaCart policy documents.

    Uses section-level chunking with TF-IDF and Cosine similarity scoring.
    Maintains grounded text snippets and confidence scores.
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
                        "tokens": tokens
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

    def query(self, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Semantic search against indexed policy chunks."""
        if not self.is_indexed:
            self.index_documents()

        query_tokens = self._tokenize(query_text)
        if not query_tokens:
            return []

        query_vec = self._compute_vector(query_tokens)

        scores: List[Tuple[float, Dict[str, Any]]] = []
        for i, chunk_vec in enumerate(self.chunk_vectors):
            dot_product = 0.0
            for token, q_weight in query_vec.items():
                if token in chunk_vec:
                    dot_product += q_weight * chunk_vec[token]

            # Boost exact keyword matches in header
            chunk_header = self.chunks[i]["header"].lower()
            for token in query_tokens:
                if token in chunk_header:
                    dot_product += 0.25

            if dot_product > 0.05:
                scores.append((dot_product, self.chunks[i]))

        scores.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, chunk in scores[:top_k]:
            normalized_score = min(0.98, max(0.50, round(score * 1.5, 2)))
            results.append({
                "source": chunk["source"],
                "category": chunk["category"],
                "header": chunk["header"],
                "content": chunk["content"],
                "confidence": normalized_score
            })

        return results

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Semantic search returning standardized chunk metadata for policy interpretation."""
        if not self.is_indexed:
            self.index_documents()

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        query_vec = self._compute_vector(query_tokens)

        scores: List[Tuple[float, Dict[str, Any]]] = []
        for i, chunk_vec in enumerate(self.chunk_vectors):
            dot_product = 0.0
            for token, q_weight in query_vec.items():
                if token in chunk_vec:
                    dot_product += q_weight * chunk_vec[token]

            # Boost exact keyword matches in header or title
            chunk_header = self.chunks[i]["header"].lower()
            chunk_title = self.chunks[i]["title"].lower()
            for token in query_tokens:
                if token in chunk_header or token in chunk_title:
                    dot_product += 0.25

            if dot_product > 0.05:
                scores.append((dot_product, self.chunks[i]))

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
                "confidence": normalized_score
            })

        return results

policy_store = PolicyVectorStore()
