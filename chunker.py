from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


def chunk_pages(
    pages: list[tuple[int, str]], source: str = "sample.pdf"
) -> list[Document]:
    """
    Splits per-page text into overlapping chunks, tagging each chunk
    with its source page number for traceability.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        length_function=len,
    )

    all_chunks = []
    for page_num, page_text in pages:
        page_chunks = splitter.split_text(page_text)
        for chunk in page_chunks:
            all_chunks.append(
                Document(
                    page_content=chunk, metadata={"source": source, "page": page_num}
                )
            )
    return all_chunks


if __name__ == "__main__":
    from extract import extract_text

    pages = extract_text("data/Sample.pdf")
    chunks = chunk_pages(pages)

    print(f"Total chunks: {len(chunks)}")
    print(f"Sample chunk 0: {chunks[0].page_content[:150]}")
    print(f"Sample chunk 0 metadata: {chunks[0].metadata}")
