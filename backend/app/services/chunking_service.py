def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0.")
    if overlap < 0:
        raise ValueError("overlap must be greater than or equal to 0.")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size.")

    source_text = text or ""
    if not source_text.strip():
        return []

    chunks: list[str] = []
    text_length = len(source_text)
    start = 0

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = source_text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start = end - overlap

    return chunks
