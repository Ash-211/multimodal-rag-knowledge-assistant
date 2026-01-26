from vectorstore.text_store import TextVectorStore
from vectorstore.image_store import ImageVectorStore
import glob
image_paths = glob.glob("../data/processed/images/*.png")
# TEXT
text_store = TextVectorStore()
text_store.add_texts(
    ["Git is a version control system", "Docker uses containers"],
    [{"src": "pdf"}, {"src": "pdf"}]
)

print(text_store.search("What is git?"))

# IMAGE
image_store = ImageVectorStore()
image_store.add_images(
    image_paths,
    [{"page": i} for i in range(len(image_paths))]
)
print(image_store.search("types of operating systems"))
