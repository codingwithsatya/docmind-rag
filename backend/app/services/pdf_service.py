import fitz


def extract_pdf_text(file_bytes: bytes):
    document = fitz.open(stream=file_bytes, filetype="pdf")

    pages = []

    for page_number, page in enumerate(document, start=1):
        text = page.get_text()

        pages.append({
            "page_number": page_number,
            "text": text,
        })

    return pages


def extract_pdf_info(file_bytes: bytes, filename: str):
    pages = extract_pdf_text(file_bytes)

    full_text = "\n".join(
        page["text"]
        for page in pages
    )

    return {
        "filename": filename,
        "pages": len(pages),
        "characters": len(full_text),
        "preview": full_text[:500],
    }
