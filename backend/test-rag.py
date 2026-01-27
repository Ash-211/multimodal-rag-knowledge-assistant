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



pdf_list = [
    "../data/raw/os.pdf",
    "../data/raw/DEVOPS.pdf",
    "../data/raw/DBMS_Notes.pdf"
]

for pdf_path in pdf_list:
    print(f"Processing PDF: {pdf_path}")

    text_chunks, _ = ingest_pdf(
        pdf_path,
        "../data/processed/images"
    )

    source_name = os.path.basename(pdf_path)

    # ---- Build full document text (for doc-level index)
    full_text = ""
    slide_chunks = []

    for chunk in text_chunks:
        slide_text = chunk["text"].strip()
        if len(slide_text) > 50:
            full_text += slide_text + "\n"
            slide_chunks.append(slide_text)

    # Add to document-level index
    doc_index.add_document(full_text, source_name)

    # Add slide-level chunks to chunk index
    chunk_index.add_chunks(source_name, slide_chunks)



image_paths = glob.glob("../data/processed/images/*.png")

image_store.add_images(
    image_paths[:20],
    [{"image_path": p} for p in image_paths[:20]]
)




query = input("Enter your question: ")

# Optional: decompose
subqueries = decompose_query(query)



all_chunks = []

for sq in subqueries:
    retrieved_chunks = index_manager.retrieve(sq)
    all_chunks.extend(retrieved_chunks)

# Deduplicate
unique = []
seen = set()

for r in all_chunks:
    content_text = r["content"]  # this should be string
    if content_text not in seen:
        unique.append(r)
        seen.add(content_text)



text_results = rerank(query, unique, top_k=6)

# Image retrieval stays global (can improve later)
image_results = image_store.search(query, k=6)


answer = generate_answer(query, text_results, image_results)

print("\n=== FINAL ANSWER ===\n")
print(answer)
