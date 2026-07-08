import fitz


def extract_text(pdf_path):
    """
    Extracts text from a PDF, page by page, preserving page numbers.

    Returns:
        list of (page_number, page_text) tuples, 1-indexed.
        Empty/blank pages are skipped (no point embedding nothing).
    """
    doc = fitz.open(pdf_path)
    pages = []
    for index, page in enumerate(doc):
        page_text = page.get_text().strip()
        if page_text:  # skip blank pages (e.g. scanned images with no text layer)
            pages.append(
                (index + 1, page_text)
            )  # +1 so page numbers match human reading
    doc.close()
    return pages


if __name__ == "__main__":
    pdf_path = "data/Sample.pdf"
    pages = extract_text(pdf_path)
    print(f"Total pages with text: {len(pages)}")
    print(f"Page {pages[0][0]}: {pages[0][1][:200]}")
