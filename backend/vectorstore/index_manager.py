class IndexManager:
    def __init__(self, doc_index, chunk_index):
        self.doc_index = doc_index
        self.chunk_index = chunk_index

    def retrieve(self, query):

        docs = self.doc_index.search(query, k=2)

        all_chunks = []


        for doc in docs:
            source = doc["source"]
            chunks = self.chunk_index.search(query, source, k=6)
            all_chunks.extend([
                {"source": source, "content": c}
                for c in chunks
            ])

        return all_chunks
