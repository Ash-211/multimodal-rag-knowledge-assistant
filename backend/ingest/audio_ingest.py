import whisper

_model = None

def _get_model():
    global _model
    if _model is None:
        _model = whisper.load_model("base")
    return _model

def ingest_audio(audio_path):
    result = _get_model().transcribe(audio_path)
    return result["text"]