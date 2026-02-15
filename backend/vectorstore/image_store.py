import clip
import torch
import faiss
import numpy as np
from PIL import Image
import os
import pickle
class ImageVectorStore:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, self.preprocess = clip.load("ViT-B/32", device=self.device)
        self.index = faiss.IndexFlatL2(512)  # 512 is the dimension of the embeddings from the model
        self.metadata = []

    def add_images(self, image_paths, metadatas):
        images = [
            self.preprocess(Image.open(p)).unsqueeze(0)
            for p in image_paths
        ]
        images = torch.cat(images).to(self.device)

        with torch.no_grad():
            emb = self.model.encode_image(images)

        self.index.add(emb.cpu().numpy().astype("float32"))

        for path, meta in zip(image_paths, metadatas):
            enriched_meta = meta.copy()
            enriched_meta["image_path"] = path
            self.metadata.append(enriched_meta)

    def search(self, query_text, k=5):
        if self.index.ntotal == 0:
            return []
        k = min(k, self.index.ntotal)
        text_tokens = clip.tokenize([query_text]).to(self.device)
        with torch.no_grad():
            q_emb = self.model.encode_text(text_tokens)
        
        _, idxs = self.index.search(q_emb.cpu().numpy().astype("float32"), k)
        return [self.metadata[i] for i in idxs[0] if 0 <= i < len(self.metadata)]
    
    def save_local(self, folder_path):
        os.makedirs(folder_path, exist_ok=True)

        faiss.write_index(self.index, os.path.join(folder_path, "index.faiss"))

        with open(os.path.join(folder_path, "metadata.pkl"), "wb") as f:
            pickle.dump(self.metadata, f)
    
    def load_local(self, folder_path):
        self.index = faiss.read_index(os.path.join(folder_path, "index.faiss"))
            
        with open(os.path.join(folder_path, "metadata.pkl"), "rb") as f:
            self.metadata = pickle.load(f)
