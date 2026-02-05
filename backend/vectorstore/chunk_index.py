import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import pickle
import os

class ChunkIndex:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        # Global index for ALL chunks
        self.index = None
        self.chunks = []  # List of dicts: {"source": str, "text": str}

    def add_chunks(self, source, chunks):
        """
        chunks: list of strings (the text segments)
        source: filename or identifier
        """
        if not chunks:
            return

        # 1. Store metadata
        for text in chunks:
            self.chunks.append({
                "source": source,
                "text": text
            })

        # 2. Embed
        embeddings = self.model.encode(chunks)
        embeddings = np.array(embeddings)

        # Ensure 2D
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)

        embeddings = embeddings.astype("float32")
        faiss.normalize_L2(embeddings)

        # 3. Add to FAISS index
        if self.index is None:
            self.index = faiss.IndexFlatIP(embeddings.shape[1])

        self.index.add(embeddings)

    def search(self, query, k=6):
        if self.index is None or self.index.ntotal == 0:
            return []

        q_emb = self.model.encode([query])
        q_emb = np.array(q_emb).astype("float32")
        faiss.normalize_L2(q_emb)

        k = min(k, self.index.ntotal)
        scores, idxs = self.index.search(q_emb, k)

        results = []
        for i in idxs[0]:
            if i < len(self.chunks):
                item = self.chunks[i]
                results.append({
                    "source": item["source"],
                    "content": item["text"]
                })
        
        return results
    
    def save_local(self, folder_path):
        os.makedirs(folder_path, exist_ok=True)

        faiss.write_index(self.index, os.path.join(folder_path, "index.faiss"))

        with open(os.path.join(folder_path, "chunks.pkl"), "wb") as f:
            pickle.dump(self.chunks, f)
    
    def load_local(self, folder_path):
        self.index = faiss.read_index(os.path.join(folder_path, "index.faiss"))
            
        with open(os.path.join(folder_path, "chunks.pkl"), "rb") as f:
            self.chunks = pickle.load(f)
