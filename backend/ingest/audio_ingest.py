import whisper

model = whisper.load_model("base")

def ingest_audio(audio_path):
    result = model.transcribe(audio_path)
    return result["text"]