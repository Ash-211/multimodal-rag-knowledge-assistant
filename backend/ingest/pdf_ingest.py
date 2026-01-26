import fitz
import os

def ingest_pdf(pdf_path, output_dir):
    doc = fitz.open(pdf_path)
    os.makedirs(output_dir, exist_ok=True)

    text_chunks = []
    image_count = 0
    extracted_images = []

    for page_num, page in enumerate(doc):
        # Text
        text = page.get_text()
        if text.strip():
            text_chunks.append({
                "page": page_num,
                "text": text
            })

        # Images
        for img in page.get_images(full=True):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]

            img_path = os.path.join(
                output_dir,
                f"page_{page_num}_img_{image_count}.{image_ext}"
            )

            with open(img_path, "wb") as f:
                f.write(image_bytes)

            extracted_images.append(img_path)
            image_count += 1

    return text_chunks, extracted_images
