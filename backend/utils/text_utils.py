def chunk_by_slide(text):
    # Split by newline and group logically
    lines = text.split("\n")
    chunks = []
    current_chunk = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # If line looks like a heading, start new chunk
        if line.endswith("Structure") or line.endswith("Generation"):
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = line + "\n"
        else:
            current_chunk += line + " "

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks
