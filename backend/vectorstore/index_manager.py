class IndexManager:
    def __init__(self, doc_index, chunk_index):
        self.doc_index = doc_index
        self.chunk_index = chunk_index

    def retrieve(self, query):

        # Search global chunk index directly
        all_chunks = self.chunk_index.search(query, k=10)
        return all_chunks
