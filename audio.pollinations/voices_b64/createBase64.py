import base64
from loguru import logger
from pydub import AudioSegment
import io


def encode_audio_base64(audio_path: str) -> str:
    def is_base64(s: str) -> bool:
        try:
            if s.startswith("data:audio"):
                s = s.split(",")[1]
            base64.b64decode(s, validate=True)
            return True
        except Exception:
            return False

    def is_wav_bytes(data: bytes) -> bool:
        return data[:4] == b'RIFF' and data[8:12] == b'WAVE'

    # If input is base64 string
    if isinstance(audio_path, str) and (audio_path.startswith("data:audio") or is_base64(audio_path)):
        # Remove header if present
        b64_data = audio_path
        if audio_path.startswith("data:audio"):
            b64_data = audio_path.split(",")[1]
        audio_bytes = base64.b64decode(b64_data)
        if is_wav_bytes(audio_bytes):
            logger.info(f"Input base64 audio is already WAV format ({len(audio_bytes)} bytes)")
            return base64.b64encode(audio_bytes).decode("utf-8")
        else:
            # Convert to WAV using pydub
            try:
                audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
                buf = io.BytesIO()
                audio.export(buf, format="wav")
                wav_bytes = buf.getvalue()
                logger.info(f"Converted base64 audio to WAV format ({len(wav_bytes)} bytes)")
                return base64.b64encode(wav_bytes).decode("utf-8")
            except Exception as e:
                logger.error(f"Failed to convert base64 audio to WAV: {e}")
                raise ValueError("Invalid base64 audio data or unsupported format")
    else:
        # Assume it's a file path
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        if is_wav_bytes(audio_bytes):
            logger.info(f"Input file is already WAV format ({len(audio_bytes)} bytes)")
            return base64.b64encode(audio_bytes).decode("utf-8")
        else:
            try:
                audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
                buf = io.BytesIO()
                audio.export(buf, format="wav")
                wav_bytes = buf.getvalue()
                logger.info(f"Converted file audio to WAV format ({len(wav_bytes)} bytes)")
                return base64.b64encode(wav_bytes).decode("utf-8")
            except Exception as e:
                logger.error(f"Failed to convert file audio to WAV: {e}")
                raise ValueError("Invalid audio file or unsupported format")

if __name__ == "__main__":
    voices = ["alloy","echo","fable","onyx","nova","shimmer","coral","verse","ballad","ash","sage","amuch","dan"]
    for voice in voices:
        print(f"Processing voice: {voice}")
        audio = f"voices_b64/raw_wav/{voice}.wav"
        audio_b64 = encode_audio_base64(audio)
        with open(f"voices_b64/base64Data/{voice}_b64.txt", "w") as f:
            f.write(audio_b64)
    print("All voices processed and saved to base64 files.")