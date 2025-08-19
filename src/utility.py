import numpy as np
import base64
import asyncio
import tempfile
import aiohttp
from loguru import logger
from config import MAX_FILE_SIZE_MB
from fastapi import HTTPException
import os
import torch
from pydub import AudioSegment
import io
from typing import Optional
import wave


def normalize_text(text: str) -> str:
    chinese_to_english = {
        "\uff0c": ", ",
        "\u3002": ".",
        "\uff1a": ":",
        "\uff1b": ";",
        "\uff1f": "?",
        "\uff01": "!",
        "\uff08": "(",
        "\uff09": ")",
        "\u3010": "[",
        "\u3011": "]",
        "\u300a": "<",
        "\u300b": ">",
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u3001": ",",
        "\u2014": "-",
        "\u2026": "...",
        "\u00b7": "."
    }
    for zh, en in chinese_to_english.items():
        text = text.replace(zh, en)
    text = text.replace("(", " ").replace(")", " ")
    text = text.replace("\u00b0F", " degrees Fahrenheit")
    text = text.replace("\u00b0C", " degrees Celsius")
    tag_replacements = [
        ("[laugh]", "<SE>[Laughter]</SE>"),
        ("[music start]", "<SE_s>[Music]</SE_s>"),
        ("[music end]", "<SE_e>[Music]</SE_e>"),
        ("[applause]", "<SE>[Applause]</SE>"),
        ("[cough]", "<SE>[Cough]</SE>"),
    ]
    for tag, replacement in tag_replacements:
        text = text.replace(tag, replacement)
    lines = text.split("\n")
    text = "\n".join([" ".join(line.split()) for line in lines if line.strip()])
    text = text.strip()
    if text and not any(text.endswith(c) for c in [".", "!", "?", ",", ";", '"', "'", "</SE_e>", "</SE>"]):
        text += "."
    return text


def is_wav_bytes(data: bytes) -> bool:
    """Check RIFF/WAVE header."""
    return (
        len(data) > 12 and
        data[0:4] == b"RIFF" and
        data[8:12] == b"WAVE"
    )


def validate_wav_pcm(audio_bytes: bytes) -> bool:
    """Check if WAV file is PCM (uncompressed)."""
    try:
        with wave.open(io.BytesIO(audio_bytes), 'rb') as wf:
            return wf.getcomptype() == 'NONE'  
    except wave.Error:
        return False


def ensure_wav(audio_bytes: bytes) -> bytes:
    if is_wav_bytes(audio_bytes) and validate_wav_pcm(audio_bytes):
        return audio_bytes  

    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        wav_io = io.BytesIO()
        audio.export(wav_io, format="wav")
        return wav_io.getvalue()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to convert audio to WAV: {str(e)}")


async def download_audio(url: str) -> bytes:
    """Download audio from URL and return as validated WAV bytes."""
    max_retries = 3
    timeout_config = aiohttp.ClientTimeout(total=45, connect=10, sock_read=30)
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'audio/*,*/*;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }

    for attempt in range(max_retries):
        try:
            logger.info(f"Downloading audio from {url} (attempt {attempt + 1}/{max_retries})")
            async with aiohttp.ClientSession(timeout=timeout_config, headers=headers) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        if response.status in [404, 403, 410]:
                            raise HTTPException(status_code=400, detail=f"Audio URL returned {response.status}: {url}")
                        continue

                    content_length = response.headers.get('Content-Length')
                    if content_length:
                        size_mb = int(content_length) / (1024 * 1024)
                        if size_mb > MAX_FILE_SIZE_MB:
                            raise HTTPException(status_code=413, detail=f"Audio file too large: {size_mb:.1f}MB")

                    data = await response.read()
                    if not data:
                        raise HTTPException(status_code=400, detail="Downloaded audio is empty")

                    logger.info(f"Downloaded {len(data)} bytes, validating as WAV")
                    return ensure_wav(data)  # <-- Ensure WAV here

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning(f"Error downloading {url} (attempt {attempt+1}): {e}")
            if attempt == max_retries - 1:
                raise HTTPException(status_code=400, detail=f"Failed to download audio: {str(e)}")
        await asyncio.sleep(1.0 * (attempt + 1))

    raise HTTPException(status_code=500, detail="Unexpected error in download_audio")


def validate_and_decode_base64_audio(audio_data: str) -> bytes:
    """Decode base64 audio and ensure WAV format."""
    try:
        if audio_data.startswith("data:"):
            if ";base64," in audio_data:
                audio_data = audio_data.split(";base64,")[1]
            else:
                raise ValueError("Invalid data URL format")

        decoded_data = base64.b64decode(audio_data, validate=True)
        size_mb = len(decoded_data) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            raise HTTPException(status_code=413, detail=f"Base64 audio too large: {size_mb:.1f}MB")

        if not decoded_data:
            raise HTTPException(status_code=400, detail="Base64 audio data is empty")

        wav_data = ensure_wav(decoded_data)
        logger.info(f"Decoded {len(wav_data)} bytes of WAV audio")
        return wav_data

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid audio data: {str(e)}")


def save_temp_audio(audio_data: bytes, req_id: str, useCase: str = "clone") -> str:
    if not audio_data:
        raise ValueError("Empty audio data")

    tmp_dir = f"/tmp/higgs/{req_id}"
    os.makedirs(tmp_dir, exist_ok=True)
    file_path = os.path.join(tmp_dir, f"voice_{req_id}.wav" if useCase == "clone" else f"speech_{req_id}.wav")

    with open(file_path, "wb") as f:
        f.write(audio_data)
    logger.debug(f"Saved {len(audio_data)} bytes WAV to {file_path}")
    return file_path


def encode_audio_base64(audio_path: str) -> str:
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    wav_bytes = ensure_wav(audio_bytes)
    if not wav_bytes:
        raise ValueError("Invalid WAV audio data")
    else:
        logger.debug(f"Encoded {len(wav_bytes)} bytes of WAV audio to base64")
    return base64.b64encode(wav_bytes).decode("utf-8")


def cleanup_temp_file(filepath: str):
    try:
        if filepath and os.path.exists(filepath):
            os.unlink(filepath)
            logger.debug(f"Cleaned up temp file: {filepath}")
    except Exception as e:
        logger.warning(f"Failed to cleanup {filepath}: {e}")


def set_random_seed(seed: Optional[int] = None):
    if seed is not None:
        torch.manual_seed(seed)
        np.random.seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)


if __name__ == "__main__":
    audio = "audio.wav"
    audio_b64 = encode_audio_base64(audio)
    decoded_audio = validate_and_decode_base64_audio(audio_b64)
    is_valid = validate_wav_pcm(decoded_audio)
    print(f"Is valid PCM WAV: {is_valid}")