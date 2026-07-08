from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

def build_vectorstore(chunks, persist_dir="chroma_db"):
    """
    Embeds chunks using HuggingFace all-MiniLM-L6-v2 and stores them
    in a persistent ChromaDB collection on disk.

    Args:
        chunks: list of Document objects from chunker.py
        persist_dir: folder where ChromaDB saves its data

    Returns:
        Chroma vectorstore object (also usable immediately for retrieval)
    """
    embedding_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        persist_directory=persist_dir,
        collection_name="study_buddy"
    )
    return vectorstore

if __name__ == "__main__":
    from extract import extract_text
    from chunker import chunk_pages

    pages = extract_text("data/Sample.pdf")
    chunks = chunk_pages(pages)

    print(f"Embedding {len(chunks)} chunks... this may take a minute on first run (downloading model).")
    vectorstore = build_vectorstore(chunks)
    print("Done. Vectorstore saved to chroma_db/")

    # quick sanity check: does semantic search actually work?
    test_query = "What is this document about?"
    results = vectorstore.similarity_search(test_query, k=2)
    print(f"\nTest query: '{test_query}'")
    for i, doc in enumerate(results):
        print(f"\nResult {i+1} (page {doc.metadata['page']}): {doc.page_content[:150]}")