import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import os
import pickle

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

    def save_local(self, folder_path):
        os.makedirs(folder_path, exist_ok=True)

        faiss.write_index(self.index, os.path.join(folder_path, "index.faiss"))

        with open(os.path.join(folder_path, "metadata.pkl"), "wb") as f:
            pickle.dump(self.metadata, f)
    
    def load_local(self, folder_path):
        self.index = faiss.read_index(os.path.join(folder_path, "index.faiss"))
            
        with open(os.path.join(folder_path, "metadata.pkl"), "rb") as f:
            self.metadata = pickle.load(f)
