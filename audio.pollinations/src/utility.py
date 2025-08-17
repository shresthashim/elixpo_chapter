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
from typing import Optional

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

async def download_audio(url: str) -> bytes:
    max_retries = 3
    timeout_config = aiohttp.ClientTimeout(
        total=45,
        connect=10,
        sock_read=30
    )
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'audio/*,*/*;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    for attempt in range(max_retries):
        try:
            logger.info(f"Downloading audio from {url} (attempt {attempt + 1}/{max_retries})")
            connector = aiohttp.TCPConnector(
                limit=10,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout_config,
                headers=headers
            ) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status} from {url}")
                        if response.status in [404, 403, 410]:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Audio URL returned {response.status}: {url}"
                            )
                        continue
                    content_type = response.headers.get('Content-Type', '').lower()
                    if content_type and not any(audio_type in content_type for audio_type in
                                              ['audio', 'wav', 'mp3', 'flac', 'ogg', 'application/octet-stream']):
                        logger.warning(f"Unexpected content type: {content_type}")
                    content_length = response.headers.get('Content-Length')
                    if content_length:
                        size_mb = int(content_length) / (1024 * 1024)
                        if size_mb > MAX_FILE_SIZE_MB:
                            raise HTTPException(
                                status_code=413,
                                detail=f"Audio file too large: {size_mb:.1f}MB (max {MAX_FILE_SIZE_MB}MB)"
                            )
                        logger.info(f"Downloading {size_mb:.1f}MB audio file")
                    data = b""
                    chunk_size = 8192
                    async for chunk in response.content.iter_chunked(chunk_size):
                        data += chunk
                        if len(data) > MAX_FILE_SIZE_MB * 1024 * 1024:
                            raise HTTPException(
                                status_code=413,
                                detail=f"Audio file too large during download (max {MAX_FILE_SIZE_MB}MB)"
                            )
                    if not data:
                        raise HTTPException(status_code=400, detail="Downloaded audio file is empty")
                    logger.info(f"Successfully downloaded {len(data)} bytes from {url}")
                    return data
        except aiohttp.ClientError as e:
            logger.warning(f"Network error downloading {url} (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to download audio after {max_retries} attempts: {str(e)}"
                )
        except asyncio.TimeoutError:
            logger.warning(f"Timeout downloading {url} (attempt {attempt + 1})")
            if attempt == max_retries - 1:
                raise HTTPException(
                    status_code=408,
                    detail=f"Timeout downloading audio after {max_retries} attempts"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error downloading {url}: {e}")
            if attempt == max_retries - 1:
                raise HTTPException(status_code=400, detail=f"Failed to download audio: {str(e)}")
        if attempt < max_retries - 1:
            await asyncio.sleep(1.0 * (attempt + 1))
    raise HTTPException(status_code=500, detail="Unexpected error in download_audio")


def save_temp_audio(audio_data: bytes, req_id: str, suffix: str = ".wav") -> str:
    if not audio_data:
        raise ValueError("Empty audio data")
    is_valid_audio = False
    if audio_data[:4] == b'RIFF' and audio_data[8:12] == b'WAVE':
        is_valid_audio = True
    elif audio_data[:3] == b'ID3' or audio_data[:2] == b'\xff\xfb':
        is_valid_audio = True
    elif audio_data[:4] == b'OggS':
        is_valid_audio = True
    elif audio_data[:4] == b'fLaC':
        is_valid_audio = True
    else:
        logger.warning("Unknown audio format, proceeding anyway")
        is_valid_audio = True
    if not is_valid_audio:
        raise HTTPException(status_code=400, detail="Invalid audio file format")
    tmp_dir = "/tmp/higgs"
    os.makedirs(tmp_dir, exist_ok=True)
    file_path = os.path.join(tmp_dir, f"{req_id}{suffix}")
    with open(file_path, "wb") as f:
        f.write(audio_data)
        logger.debug(f"Saved {len(audio_data)} bytes to {file_path}")
        return file_path


        
def validate_and_decode_base64_audio(audio_data: str) -> bytes:
    try:
        if audio_data.startswith('data:'):
            if ';base64,' in audio_data:
                audio_data = audio_data.split(';base64,')[1]
            else:
                raise ValueError("Invalid data URL format")
        decoded_data = base64.b64decode(audio_data, validate=True)
        size_mb = len(decoded_data) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            raise HTTPException(
                status_code=413,
                detail=f"Base64 audio too large: {size_mb:.1f}MB (max {MAX_FILE_SIZE_MB}MB)"
            )
        if not decoded_data:
            raise HTTPException(status_code=400, detail="Base64 audio data is empty")
        logger.info(f"Decoded {len(decoded_data)} bytes from base64 audio")
        return decoded_data
    except base64.binascii.Error:
        raise HTTPException(status_code=400, detail="Invalid base64 audio data")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid audio data format: {str(e)}")

def encode_audio_base64(audio_path: str) -> str:
    with open(audio_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

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