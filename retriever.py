import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

CURRENT_COLLECTION_FILE = "current_collection.txt"

def get_current_collection_name(default="study_buddy"):
    if os.path.exists(CURRENT_COLLECTION_FILE):
        with open(CURRENT_COLLECTION_FILE, "r") as f:
            return f.read().strip()
    return default

def load_vectorstore(persist_dir="chroma_db"):
    embedding_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    collection_name = get_current_collection_name()
    vectorstore = Chroma(
        persist_directory=persist_dir,
        embedding_function=embedding_model,
        collection_name=collection_name
    )
    return vectorstore

def retrieve_chunks(query: str, k: int = 4, persist_dir="chroma_db"):
    vectorstore = load_vectorstore(persist_dir)
    results = vectorstore.similarity_search(query, k=k)
    return results

def get_chunks_by_page(page_num: int, persist_dir="chroma_db"):
    """
    Fetches all chunks from a specific page directly (metadata filter,
    no similarity search needed). Used for weak-area quiz targeting.
    """
    vectorstore = load_vectorstore(persist_dir)
    result = vectorstore._collection.get(where={"page": page_num})
    return result.get("documents", [])

if __name__ == "__main__":
    test_query = "What is this book about?"
    results = retrieve_chunks(test_query)
    print(f"Query: '{test_query}'")
    print(f"Retrieved {len(results)} chunks:\n")
    for i, doc in enumerate(results):
        print(f"--- Chunk {i+1} (page {doc.metadata['page']}) ---")
        print(doc.page_content[:200])
        print()