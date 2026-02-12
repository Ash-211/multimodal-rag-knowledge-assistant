from ingest.image_ingest import ingest_image
from PIL import Image

img_path = ingest_image(
    "../data/raw/devops.png",
    "../data/processed/images"
)

img = Image.open(img_path)
img.verify()

print(" Standalone image ingestion works")

