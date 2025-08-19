import whisper
import base64
import tempfile
import os

def transcribe_audio(b64_file: str, model_size: str = "small") -> str:

    with open(b64_file, "r") as f:
        b64_audio = f.read().strip()


    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
        tmp_file.write(base64.b64decode(b64_audio))
        audio_path = tmp_file.name  

    try:

        model = whisper.load_model(model_size)
        result = model.transcribe(audio_path)

        return result["text"]

    finally:

        if os.path.exists(audio_path):
            os.remove(audio_path)


if __name__ == "__main__":
    text = transcribe_audio("audio_base64.txt", model_size="small")
    print("\n--- Transcription ---\n")
    print(text)
