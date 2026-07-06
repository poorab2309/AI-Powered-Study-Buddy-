import fitz


def extract_text(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text


if __name__ == "__main__":
    pdf_path = "data/Sample.pdf"
    text = extract_text(pdf_path)
    print(text[:500])  # print first 500 characters to test
