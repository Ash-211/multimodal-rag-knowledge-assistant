from vectorstore.document_index import DocumentIndex
from vectorstore.chunk_index import ChunkIndex
from vectorstore.image_store import ImageVectorStore
from vectorstore.index_manager import IndexManager

from rag.generator import generate_answer, decompose_query
from rag.reranker import rerank

from ingest.pdf_ingest import ingest_pdf
from utils.text_utils import chunk_by_slide

import os
import glob




doc_index = DocumentIndex()
chunk_index = ChunkIndex()
image_store = ImageVectorStore()

index_manager = IndexManager(doc_index, chunk_index)


DATA_DIR = "../data"
INDICES_DIR = os.path.join(DATA_DIR, "indices")

CHUNK_INDEX_PATH = os.path.join(INDICES_DIR, "chunks")
DOC_INDEX_PATH = os.path.join(INDICES_DIR, "docs")
IMAGE_INDEX_PATH = os.path.join(INDICES_DIR, "images")

if os.path.exists(CHUNK_INDEX_PATH) and os.path.exists(DOC_INDEX_PATH) and os.path.exists(IMAGE_INDEX_PATH):
    print("Loading indices from disk (skipping ingestion)...")

    chunk_index.load_local(CHUNK_INDEX_PATH)
    doc_index.load_local(DOC_INDEX_PATH)
    image_store.load_local(IMAGE_INDEX_PATH)

    index_manager = IndexManager(doc_index, chunk_index)
else:
    print("Indices not found. Starting fresh ingesetion...")

    pdf_list = [
        "../data/raw/os.pdf",
        "../data/raw/DEVOPS.pdf",
        "../data/raw/DBMS_Notes.pdf"
    ]
    
    text_chunks, _ = ingest_pdf(pdf_list, "../data/processed/images")

    from collections import defaultdict
    chunks_by_source = defaultdict(list)

    for chunk in text_chunks:
        chunks_by_source[chunk["source"]].append(chunk["text"])

    for source, chunks in chunks_by_source.items():
        slide_chunks = []
        full_text = ""
        for text in chunks:
            text = text.strip()
            if len(text) > 50:
                full_text += text + "\n"
                slide_chunks.append(text)
            
        if(slide_chunks):
            doc_index.add_document(full_text, source)
            chunk_index.add_chunks(source, slide_chunks)

    image_paths = glob.glob("../data/processed/images/*.png")
    image_metadata = []

    for p in image_paths:
        try:
            parts = p.split("_page_")
            page_num = int(parts[1].split("_img_")[0]) if len(parts) > 1 else 0
        except:
            page_num = 0
        image_metadata.append({"image_path": p, "page": page_num})
    
    image_store.add_images(image_paths[:20], image_metadata[:20])

    print("Saving indices to disk...")
    chunk_index.save_local(CHUNK_INDEX_PATH)
    doc_index.save_local(DOC_INDEX_PATH)
    image_store.save_local(IMAGE_INDEX_PATH)

print("System ready!")








query = input("Enter your question: ")

# Optional: decompose
# Optional: decompose
# Skip decomposition for speed
subqueries = [query]

all_chunks = []

for sq in subqueries:
    retrieved_chunks = index_manager.retrieve(sq)
    all_chunks.extend(retrieved_chunks)

# Deduplicate
# Deduplicate
unique = []
seen = set()

for r in all_chunks:
    content_text = r["content"]  # this should be string
    if content_text not in seen:
        unique.append(r)
        seen.add(content_text)

print(f"\nFound {len(unique)} unique chunks.")
for i, r in enumerate(unique[:3]):
    print(f"Chunk {i}: {r['content'][:100]}...")

text_results = rerank(query, unique, top_k=6)
print(f"Reranked to {len(text_results)} chunks.")

# Image retrieval stays global (can improve later)
image_results = image_store.search(query, k=6)

try:
    answer = generate_answer(query, text_results, image_results)
    print("\n=== FINAL ANSWER ===\n")
    print(answer)
except Exception as e:
    print(f"\nGeneration failed: {e}")
    # Don't fail the script, just report error

