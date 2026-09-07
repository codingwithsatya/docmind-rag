def is_heading(paragraph: str) -> bool:
    text = paragraph.strip()

    if not text:
        return False

    if len(text) > 80:
        return False

    known_headings = {
        "risk",
        "sector strength & weakness",
        "gap downs",
        "gap up",
        "opening volume",
        "the squeeze",
    }

    if text.lower() in known_headings:
        return True

    if (
        len(text.split()) <= 8
        and not text.endswith((".", ",", ";", ":"))
        and not text.startswith("-")
    ):
        return True

    return False


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap_paragraphs: int = 1,
):
    paragraphs = [
        paragraph.strip()
        for paragraph in text.split("\n")
        if paragraph.strip()
    ]

    chunks = []
    current_paragraphs = []

    for paragraph in paragraphs:
        if is_heading(paragraph) and current_paragraphs:
            chunks.append("\n".join(current_paragraphs))
            current_paragraphs = [paragraph]
            continue

        candidate_paragraphs = current_paragraphs + [paragraph]
        candidate_text = "\n".join(candidate_paragraphs)

        if len(candidate_text) <= chunk_size:
            current_paragraphs.append(paragraph)
            continue

        if current_paragraphs:
            chunks.append("\n".join(current_paragraphs))

        overlap = current_paragraphs[-overlap_paragraphs:]
        current_paragraphs = overlap + [paragraph]

    if current_paragraphs:
        chunks.append("\n".join(current_paragraphs))

    return chunks


def chunk_pages(
    pages: list[dict],
    chunk_size: int = 1000,
    overlap_paragraphs: int = 1,
):
    results = []
    chunk_index = 0

    for page in pages:
        page_number = page["page_number"]
        text = page["text"]

        page_chunks = chunk_text(
            text=text,
            chunk_size=chunk_size,
            overlap_paragraphs=overlap_paragraphs,
        )

        for chunk in page_chunks:
            results.append(
                {
                    "chunk_index": chunk_index,
                    "page_number": page_number,
                    "content": chunk,
                }
            )

            chunk_index += 1

    return results
