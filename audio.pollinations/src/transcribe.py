import whisper

def transcribe_audio(file_path: str, model_size: str = "large") -> str:
    """
    Transcribe speech from an audio file using OpenAI Whisper.

    Args:
        file_path (str): Path to the audio file.
        model_size (str): Whisper model size (tiny, base, small, medium, large).

    Returns:
        str: Transcribed text.
    """
    model = whisper.load_model(model_size)  # runs on GPU automatically if available
    result = model.transcribe(file_path)
    return result["text"]

if __name__ == "__main__":
    text = transcribe_audio("example.mp3", model_size="large")
    print("\n--- Transcription ---\n")
    print(text)
