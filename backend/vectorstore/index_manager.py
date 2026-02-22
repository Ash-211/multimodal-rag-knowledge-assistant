class IndexManager:
    def __init__(self, doc_index, chunk_index):
        self.doc_index = doc_index
        self.chunk_index = chunk_index

    def retrieve(self, query, k=10):
        """
        Two-stage retrieval:
        1. Find the most relevant DOCUMENTS via doc_index
        2. Search all chunks, but boost chunks from relevant documents
        """
        # Stage 1: Find relevant documents
        relevant_docs = self.doc_index.search(query, k=3)
        relevant_sources = {doc["source"] for doc in relevant_docs}

        # Stage 2: Get chunks from the global chunk index
        all_chunks = self.chunk_index.search(query, k=k * 2)  # fetch extra

        # Separate into relevant-doc chunks and other chunks
        boosted = [c for c in all_chunks if c["source"] in relevant_sources]
        others = [c for c in all_chunks if c["source"] not in relevant_sources]

        # Prioritize chunks from relevant documents, fill remaining with others
        result = boosted[:k]
        remaining = k - len(result)
        if remaining > 0:
            result.extend(others[:remaining])

        return result
