import fitz
from docx import Document as DocxDocument

PSEUDO_PAGE_SIZE = (
    3000  # chars per "page" for DOCX/TXT, which have no real page concept
)


def extract_pdf_text(pdf_path):
    doc = fitz.open(pdf_path)
    pages = []
    for index, page in enumerate(doc):
        page_text = page.get_text().strip()
        if page_text:
            pages.append((index + 1, page_text))
    doc.close()
    return pages


def extract_docx_text(docx_path):
    doc = DocxDocument(docx_path)
    full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return _chunk_into_pseudo_pages(full_text)


def extract_txt_text(txt_path):
    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
        full_text = f.read()
    return _chunk_into_pseudo_pages(full_text)


def _chunk_into_pseudo_pages(full_text: str):
    """
    DOCX and TXT files don't have real page boundaries like PDFs.
    We simulate pages by splitting every PSEUDO_PAGE_SIZE characters,
    so the rest of the pipeline (which expects page numbers) keeps working.
    """
    pages = []
    for i in range(0, len(full_text), PSEUDO_PAGE_SIZE):
        chunk = full_text[i : i + PSEUDO_PAGE_SIZE].strip()
        if chunk:
            pages.append((len(pages) + 1, chunk))
    return pages


def extract_text(file_path):
    """
    Dispatches to the right extractor based on file extension.
    Returns list of (page_number, text) tuples in all cases.
    """
    lower = file_path.lower()
    if lower.endswith(".pdf"):
        return extract_pdf_text(file_path)
    elif lower.endswith(".docx"):
        return extract_docx_text(file_path)
    elif lower.endswith(".txt"):
        return extract_txt_text(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_path}")


if __name__ == "__main__":
    pdf_path = "data/Sample.pdf"
    pages = extract_text(pdf_path)
    print(f"Total pages with text: {len(pages)}")
    print(f"Page {pages[0][0]}: {pages[0][1][:200]}")
