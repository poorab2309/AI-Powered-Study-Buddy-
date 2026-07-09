from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma


def build_vectorstore(chunks, persist_dir="chroma_db", collection_name="study_buddy"):
    """
    Embeds chunks and stores them in a named ChromaDB collection.
    Using a unique collection_name per upload avoids ever needing to
    delete the old collection (sidesteps Windows file-lock issues).

    Args:
        chunks: list of Document objects from chunker.py
        persist_dir: folder where ChromaDB saves its data
        collection_name: name for this specific collection (unique per upload)

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
        collection_name=collection_name,
    )
    return vectorstore


if __name__ == "__main__":
    from extract import extract_text
    from chunker import chunk_pages

    pages = extract_text("data/Sample.pdf")
    chunks = chunk_pages(pages)

    print(f"Embedding {len(chunks)} chunks...")
    vectorstore = build_vectorstore(chunks)
    print("Done. Vectorstore saved to chroma_db/")

    test_query = "What is this document about?"
    results = vectorstore.similarity_search(test_query, k=2)
    print(f"\nTest query: '{test_query}'")
    for i, doc in enumerate(results):
        print(f"\nResult {i+1} (page {doc.metadata['page']}): {doc.page_content[:150]}")
