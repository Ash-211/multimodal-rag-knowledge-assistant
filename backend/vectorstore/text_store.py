from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

class TextVectorStore:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = faiss.IndexFlatIP(384)  # 384 is the dimension of the embeddings from the model
        self.metadata = []

    def add_texts(self, texts, metadatas=None):
        embeddings = self.model.encode(texts)
        embeddings = np.array(embeddings).astype("float32")
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)

        for text, meta in zip(texts, metadatas):
            enriched_meta = meta.copy()
            enriched_meta["content"] = text
            self.metadata.append(enriched_meta)

    def search(self, query, k=5):
        q_emb = self.model.encode([query])
        q_emb = np.array(q_emb).astype("float32")
        faiss.normalize_L2(q_emb)
        _, idxs = self.index.search(q_emb.astype("float32"), k)
        return [self.metadata[i] for i in idxs[0]]

    