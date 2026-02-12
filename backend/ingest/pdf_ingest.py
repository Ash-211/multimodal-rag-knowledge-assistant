import fitz
import os

def ingest_pdf(pdf_paths, output_dir):

    # 🔹 Allow both single path (string) and list of paths
    if isinstance(pdf_paths, str):
        pdf_paths = [pdf_paths]

    all_text_chunks = []
    all_extracted_images = []

    os.makedirs(output_dir, exist_ok=True)

    for pdf_path in pdf_paths:
        try:
            print("Processing PDF:", pdf_path)
            doc = fitz.open(pdf_path)

            image_count = 0
            source_name = os.path.basename(pdf_path)

            for page_num, page in enumerate(doc):

                # ------------------
                # Extract Text
                # ------------------
                text = page.get_text()

                if text.strip():
                    all_text_chunks.append({
                        "page": page_num,
                        "text": text,
                        "source": source_name  # important for multi-doc retrieval
                    })

                # ------------------
                # Extract Images
                # ------------------
                for img in page.get_images(full=True):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    img_path = os.path.join(
                        output_dir,
                        f"{source_name}_page_{page_num}_img_{image_count}.{image_ext}"
                    )

                    with open(img_path, "wb") as f:
                        f.write(image_bytes)

                    all_extracted_images.append(img_path)
                    image_count += 1

        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")

    return all_text_chunks, all_extracted_images
