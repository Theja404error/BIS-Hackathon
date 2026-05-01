"""
Hybrid retriever: BM25 (lexical) + sentence-transformer embeddings (semantic).

Why hybrid?
- Pure dense retrieval misses exact code matches ("IS 8112" → user types it verbatim).
- Pure BM25 misses paraphrases ("cement for high rises" → "53 grade OPC").
- Reciprocal Rank Fusion combines them — typically +5-10 pts on Hit Rate.
"""

import json
import pickle
from pathlib import Path
from typing import List, Dict, Tuple

import numpy as np
import faiss
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

DATA_DIR = Path(__file__).parent.parent / "data"
CHUNKS_PATH = DATA_DIR / "chunks.json"
INDEX_DIR = DATA_DIR / "index"

EMBED_MODEL = "BAAI/bge-small-en-v1.5"  # fast, strong on retrieval


def _tokenize(text: str) -> List[str]:
    return text.lower().split()


class HybridRetriever:
    def __init__(self):
        self.chunks: List[Dict] = []
        self.bm25: BM25Okapi = None
        self.embed_model: SentenceTransformer = None
        self.faiss_index = None

    # ---------- BUILD ----------
    def build(self):
        with open(CHUNKS_PATH) as f:
            self.chunks = json.load(f)

        print(f"Building indices over {len(self.chunks)} chunks...")

        # BM25 over text + IS code (so the code is searchable too)
        corpus = [_tokenize(c["is_code"] + " " + c["text"]) for c in self.chunks]
        self.bm25 = BM25Okapi(corpus)

        # Dense embeddings
        self.embed_model = SentenceTransformer(EMBED_MODEL)
        texts = [c["is_code"] + ". " + c["text"] for c in self.chunks]
        embs = self.embed_model.encode(
            texts, batch_size=32, show_progress_bar=True, normalize_embeddings=True
        )
        embs = np.asarray(embs, dtype="float32")

        self.faiss_index = faiss.IndexFlatIP(embs.shape[1])
        self.faiss_index.add(embs)

        INDEX_DIR.mkdir(exist_ok=True)
        faiss.write_index(self.faiss_index, str(INDEX_DIR / "faiss.index"))
        with open(INDEX_DIR / "bm25.pkl", "wb") as f:
            pickle.dump(self.bm25, f)
        with open(INDEX_DIR / "chunks.json", "w") as f:
            json.dump(self.chunks, f)
        print("✅ Indices saved")

    # ---------- LOAD ----------
    def load(self):
        with open(INDEX_DIR / "chunks.json") as f:
            self.chunks = json.load(f)
        with open(INDEX_DIR / "bm25.pkl", "rb") as f:
            self.bm25 = pickle.load(f)
        self.faiss_index = faiss.read_index(str(INDEX_DIR / "faiss.index"))
        self.embed_model = SentenceTransformer(EMBED_MODEL)

    # ---------- QUERY ----------
    def search(self, query: str, top_k: int = 10) -> List[Tuple[Dict, float]]:
        # BM25 scores
        bm25_scores = self.bm25.get_scores(_tokenize(query))
        bm25_top = np.argsort(bm25_scores)[::-1][:top_k]

        # Dense scores
        q_emb = self.embed_model.encode(
            [query], normalize_embeddings=True
        ).astype("float32")
        dense_scores, dense_top = self.faiss_index.search(q_emb, top_k)
        dense_top = dense_top[0]

        # Reciprocal Rank Fusion
        k = 60  # standard RRF constant
        fused: Dict[int, float] = {}
        for rank, idx in enumerate(bm25_top):
            fused[int(idx)] = fused.get(int(idx), 0) + 1.0 / (k + rank)
        for rank, idx in enumerate(dense_top):
            if idx == -1:
                continue
            fused[int(idx)] = fused.get(int(idx), 0) + 1.0 / (k + rank)

        ranked = sorted(fused.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [(self.chunks[idx], score) for idx, score in ranked]


if __name__ == "__main__":
    r = HybridRetriever()
    r.build()
    r.load()
    results = r.search("ordinary portland cement 53 grade", top_k=5)
    for chunk, score in results:
        print(f"[{score:.3f}] {chunk['is_code']} — {chunk['text'][:120]}...")
