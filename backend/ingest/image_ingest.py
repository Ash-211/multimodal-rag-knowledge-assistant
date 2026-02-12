from PIL import Image
import os
import shutil

def ingest_image(image_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    img = Image.open(image_path).convert("RGB")

    filename = os.path.basename(image_path)
    save_path = os.path.join(output_dir, filename)

    shutil.copy(image_path, save_path)

    return save_path
