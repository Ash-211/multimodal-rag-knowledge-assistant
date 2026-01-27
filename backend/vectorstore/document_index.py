import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

class DocumentIndex:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.index = faiss.IndexFlatIP(384)
        self.metadata = []

    def add_document(self, full_text, source):
        embedding = self.model.encode([full_text])
        embedding = np.array(embedding).astype("float32")
        faiss.normalize_L2(embedding)

        self.index.add(embedding)

        self.metadata.append({
            "source": source,
            "full_text": full_text
        })

    def search(self, query, k=2):
        q_emb = self.model.encode([query])
        q_emb = np.array(q_emb).astype("float32")
        faiss.normalize_L2(q_emb)

        scores, idxs = self.index.search(q_emb, k)

        return [self.metadata[i] for i in idxs[0]]
