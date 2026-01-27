import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


class ChunkIndex:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.indices = {}   # {source: faiss_index}
        self.metadata = {}  # {source: list_of_chunks}

    def add_chunks(self, source, chunks):
        if not chunks:
            return

        embeddings = self.model.encode(chunks)
        embeddings = np.array(embeddings)

        # Ensure 2D
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)

        embeddings = embeddings.astype("float32")
        faiss.normalize_L2(embeddings)

        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)

        self.indices[source] = index
        self.metadata[source] = chunks

    def search(self, query, source, k=6):
        if source not in self.indices:
            return []

        q_emb = self.model.encode([query])
        q_emb = np.array(q_emb).astype("float32")
        faiss.normalize_L2(q_emb)

        index = self.indices[source]

        k = min(k, index.ntotal)  # prevent overflow
        scores, idxs = index.search(q_emb, k)

        return [
            {
                "source": source,
                "content": self.metadata[source][i]
            }
            for i in idxs[0]
        ]
