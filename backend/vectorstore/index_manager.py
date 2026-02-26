class IndexManager:
    def __init__(self, doc_index, chunk_index):
        self.doc_index = doc_index
        self.chunk_index = chunk_index

    def retrieve(self, query, k=10, source_filter=None):
        """
        Retrieve relevant chunks for a query.
        
        Args:
            query: The search query
            k: Number of results to return
            source_filter: Optional set of filenames to restrict search to.
                          If provided, only chunks from these sources are returned.
                          If None, all chunks are searched (backward compatible).
        """
        # Get chunks from the global chunk index (fetch extra for filtering)
        all_chunks = self.chunk_index.search(query, k=k * 3)

        if source_filter:
            # Filter to only chunks from the specified documents
            filtered = [c for c in all_chunks if c["source"] in source_filter]
            return filtered[:k]
        
        # No filter — use two-stage doc-aware retrieval
        relevant_docs = self.doc_index.search(query, k=3)
        relevant_sources = {doc["source"] for doc in relevant_docs}

        boosted = [c for c in all_chunks if c["source"] in relevant_sources]
        others = [c for c in all_chunks if c["source"] not in relevant_sources]

        result = boosted[:k]
        remaining = k - len(result)
        if remaining > 0:
            result.extend(others[:remaining])

        return result
