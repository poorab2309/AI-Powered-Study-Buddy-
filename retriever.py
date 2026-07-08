from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma


def load_vectorstore(persist_dir="chroma_db"):
    """
    Loads the existing ChromaDB vectorstore from disk.
    Must use the SAME embedding model as embedder.py, or
    similarity search will produce garbage (mismatched vector spaces).
    """
    embedding_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    vectorstore = Chroma(
        persist_directory=persist_dir,
        embedding_function=embedding_model,
        collection_name="study_buddy",
    )
    return vectorstore


def retrieve_chunks(query: str, k: int = 4, persist_dir="chroma_db"):
    """
    Given a user question, returns the top-k most relevant chunks.
    """
    vectorstore = load_vectorstore(persist_dir)
    results = vectorstore.similarity_search(query, k=k)
    return results


if __name__ == "__main__":
    test_query = "What is this book about?"
    results = retrieve_chunks(test_query)

    print(f"Query: '{test_query}'")
    print(f"Retrieved {len(results)} chunks:\n")
    for i, doc in enumerate(results):
        print(f"--- Chunk {i+1} (page {doc.metadata['page']}) ---")
        print(doc.page_content[:200])
        print()
