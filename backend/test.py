from ingest.audio_ingest import ingest_audio
from ingest.pdf_ingest import ingest_pdf

print(ingest_pdf("../data/raw/os.pdf", "../data/processed/images"))
print(ingest_audio("../data/raw/Recording.mp3"))