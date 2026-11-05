from app.services.chunking_service import is_heading, chunk_text


def test_invoice_values_are_not_headings():
    assert is_heading("AMOUNT DUE") is False
    assert is_heading("$58.97") is False
    assert is_heading("PAYMENT DUE DATE") is False
    assert is_heading("01/29/2024") is False


def test_invoice_labels_and_values_stay_together():
    text = (
        "ACCOUNT SUMMARY\n"
        "AMOUNT DUE\n"
        "$58.97\n"
        "PAYMENT DUE DATE\n"
        "01/29/2024\n"
    )

    chunks = chunk_text(text)

    assert any(
        "AMOUNT DUE\n$58.97" in chunk
        for chunk in chunks
    )

    assert any(
        "PAYMENT DUE DATE\n01/29/2024" in chunk
        for chunk in chunks
    )

def test_many_short_lines_do_not_create_excessive_chunks():
    text = "\n".join(
        f"Invoice line {index}: value {index}"
        for index in range(100)
    )

    chunks = chunk_text(
        text,
        chunk_size=1000,
        overlap_paragraphs=1,
    )

    assert len(chunks) <= 5
    assert all(len(chunk) <= 1000 for chunk in chunks)
    assert "Invoice line 0: value 0" in chunks[0]
    assert "Invoice line 99: value 99" in chunks[-1]