#!/usr/bin/env python3
"""
Higgs V2 Audio Model - OpenAI Compatible API Server
Stateless voice cloning with exact OpenAI format compatibility
"""

import os
import io
import json
import time
import base64
import asyncio
import tempfile
import traceback
from typing import Optional, List, Dict, Any, Union
from urllib.parse import unquote

import numpy as np
import torch
import torchaudio
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, validator
import aiohttp
from loguru import logger

# Import Higgs components
from boson_multimodal.serve.serve_engine import HiggsAudioServeEngine, HiggsAudioResponse
from boson_multimodal.data_types import ChatMLSample, Message, AudioContent


MODEL_PATH = os.environ.get("MODEL_PATH", "bosonai/higgs-audio-v2-generation-3B-base")
AUDIO_TOKENIZER_PATH = os.environ.get("AUDIO_TOKENIZER_PATH", "bosonai/higgs-audio-v2-tokenizer")
SAMPLE_RATE = 24000

MAX_FILE_SIZE_MB = 5
MAX_CONCURRENT_REQUESTS = 50

DEFAULT_SYSTEM_PROMPT = (
    "Generate audio following instruction.\n\n"
    "<|scene_desc_start|>\n"
    "Audio is recorded from a quiet room.\n"
    "<|scene_desc_end|>"
)

DEFAULT_STOP_STRINGS = ["<|end_of_text|>", "<|eot_id|>"]


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Global engine instance
higgs_engine: Optional[HiggsAudioServeEngine] = None

# ==================== Pydantic Models ====================
class APIMessage(BaseModel):
    """Chat message for API (renamed to avoid conflicts)"""
    role: str = Field(..., description="Role: user, assistant, system")
    content: str = Field(..., description="Message content")

class OpenAIRequest(BaseModel):
    """OpenAI-compatible request format"""
    model: str = Field(default="higgs", description="Model name")
    modalities: List[str] = Field(default=["text", "audio"], description="Supported modalities")
    audio: Optional[str] = Field(None, description="Base64 encoded audio or URL for voice cloning")
    messages: List[APIMessage] = Field(..., description="Chat messages")
    seed: Optional[int] = Field(None, description="Random seed")

# ==================== Utility Functions ====================
def normalize_text(text: str) -> str:
    """Normalize text for TTS processing"""
    # Chinese punctuation conversion
    chinese_to_english = {
        "\uff0c": ", ",  # ，
        "\u3002": ".",   # 。
        "\uff1a": ":",   # ：
        "\uff1b": ";",   # ；
        "\uff1f": "?",   # ？
        "\uff01": "!",   # ！
        "\uff08": "(",   # （
        "\uff09": ")",   # ）
        "\u3010": "[",   # 【
        "\u3011": "]",   # 】
        "\u300a": "<",   # 《
        "\u300b": ">",   # 》
        "\u201c": '"',   # "
        "\u201d": '"',   # "
        "\u2018": "'",   # '
        "\u2019": "'",   # '
        "\u3001": ",",   # 、
        "\u2014": "-",   # —
        "\u2026": "...", # …
        "\u00b7": "."    # ·
    }
    
    for zh, en in chinese_to_english.items():
        text = text.replace(zh, en)
    
    # Clean up parentheses and special chars
    text = text.replace("(", " ").replace(")", " ")
    text = text.replace("\u00b0F", " degrees Fahrenheit")  # °F
    text = text.replace("\u00b0C", " degrees Celsius")     # °C
    
    # Handle special tags for effects
    tag_replacements = [
        ("[laugh]", "<SE>[Laughter]</SE>"),
        ("[music start]", "<SE_s>[Music]</SE_s>"),
        ("[music end]", "<SE_e>[Music]</SE_e>"),
        ("[applause]", "<SE>[Applause]</SE>"),
        ("[cough]", "<SE>[Cough]</SE>"),
    ]
    
    for tag, replacement in tag_replacements:
        text = text.replace(tag, replacement)
    
    # Clean whitespace
    lines = text.split("\n")
    text = "\n".join([" ".join(line.split()) for line in lines if line.strip()])
    text = text.strip()
    
    # Add period if missing
    if text and not any(text.endswith(c) for c in [".", "!", "?", ",", ";", '"', "'", "</SE_e>", "</SE>"]):
        text += "."
    
    return text

async def download_audio(url: str) -> bytes:
    """Download audio from URL with robust error handling and retries"""
    max_retries = 3
    timeout_config = aiohttp.ClientTimeout(
        total=45,      # Total timeout
        connect=10,    # Connection timeout
        sock_read=30   # Socket read timeout
    )
    
    # Custom headers to mimic a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'audio/*,*/*;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Downloading audio from {url} (attempt {attempt + 1}/{max_retries})")
            
            # Create a new session for each attempt
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
                    # Check response status
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status} from {url}")
                        if response.status in [404, 403, 410]:
                            # Don't retry for client errors
                            raise HTTPException(
                                status_code=400, 
                                detail=f"Audio URL returned {response.status}: {url}"
                            )
                        continue  # Retry for server errors
                    
                    # Check content type
                    content_type = response.headers.get('Content-Type', '').lower()
                    if content_type and not any(audio_type in content_type for audio_type in 
                                              ['audio', 'wav', 'mp3', 'flac', 'ogg', 'application/octet-stream']):
                        logger.warning(f"Unexpected content type: {content_type}")
                    
                    # Check content length
                    content_length = response.headers.get('Content-Length')
                    if content_length:
                        size_mb = int(content_length) / (1024 * 1024)
                        if size_mb > MAX_FILE_SIZE_MB:
                            raise HTTPException(
                                status_code=413, 
                                detail=f"Audio file too large: {size_mb:.1f}MB (max {MAX_FILE_SIZE_MB}MB)"
                            )
                        logger.info(f"Downloading {size_mb:.1f}MB audio file")
                    
                    # Download in chunks
                    data = b""
                    chunk_size = 8192
                    async for chunk in response.content.iter_chunked(chunk_size):
                        data += chunk
                        # Check size during download
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
            # Re-raise HTTP exceptions immediately
            raise
        except Exception as e:
            logger.error(f"Unexpected error downloading {url}: {e}")
            if attempt == max_retries - 1:
                raise HTTPException(status_code=400, detail=f"Failed to download audio: {str(e)}")
        
        # Wait before retry
        if attempt < max_retries - 1:
            await asyncio.sleep(1.0 * (attempt + 1))  # Progressive backoff
    
    raise HTTPException(status_code=500, detail="Unexpected error in download_audio")

def validate_and_decode_base64_audio(audio_data: str) -> bytes:
    """Validate and decode base64 audio data"""
    try:
        # Remove data URL prefix if present
        if audio_data.startswith('data:'):
            # Format: data:audio/wav;base64,<data>
            if ';base64,' in audio_data:
                audio_data = audio_data.split(';base64,')[1]
            else:
                raise ValueError("Invalid data URL format")
        
        # Decode base64
        decoded_data = base64.b64decode(audio_data, validate=True)
        
        # Check size
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
    """Encode audio file to base64"""
    with open(audio_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def save_temp_audio(audio_data: bytes, suffix: str = ".wav") -> str:
    """Save audio data to temporary file with validation"""
    if not audio_data:
        raise ValueError("Empty audio data")
    
    # Basic audio file validation (check for common headers)
    is_valid_audio = False
    if audio_data[:4] == b'RIFF' and audio_data[8:12] == b'WAVE':
        is_valid_audio = True  # WAV file
    elif audio_data[:3] == b'ID3' or audio_data[:2] == b'\xff\xfb':
        is_valid_audio = True  # MP3 file
    elif audio_data[:4] == b'OggS':
        is_valid_audio = True  # OGG file
    elif audio_data[:4] == b'fLaC':
        is_valid_audio = True  # FLAC file
    else:
        logger.warning("Unknown audio format, proceeding anyway")
        is_valid_audio = True  # Allow unknown formats
    
    if not is_valid_audio:
        raise HTTPException(status_code=400, detail="Invalid audio file format")
    
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(audio_data)
        logger.debug(f"Saved {len(audio_data)} bytes to {f.name}")
        return f.name

def cleanup_temp_file(filepath: str):
    """Clean up temporary file"""
    try:
        if filepath and os.path.exists(filepath):
            os.unlink(filepath)
            logger.debug(f"Cleaned up temp file: {filepath}")
    except Exception as e:
        logger.warning(f"Failed to cleanup {filepath}: {e}")

def set_random_seed(seed: Optional[int] = None):
    """Set random seeds for reproducible generation"""
    if seed is not None:
        torch.manual_seed(seed)
        np.random.seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)

# ==================== Core TTS Functions ====================
def prepare_chatml_sample(
    text: str,
    reference_audio_path: Optional[str] = None,
    reference_text: Optional[str] = None,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
) -> ChatMLSample:
    """Prepare ChatML sample for Higgs engine"""
    messages = []
    
    try:
        # Add system prompt
        if system_prompt:
            sys_message = Message(role="system", content=system_prompt)
            messages.append(sys_message)
        
        # Add reference audio for voice cloning if available
        if reference_audio_path and os.path.exists(reference_audio_path):
            logger.info(f"Adding reference audio: {reference_audio_path}")
            
            # Add reference text as user message
            if reference_text:
                ref_user_message = Message(role="user", content=reference_text)
                messages.append(ref_user_message)
            else:
                # Use a generic message for voice cloning
                ref_user_message = Message(role="user", content="Please clone this voice.")
                messages.append(ref_user_message)
            
            # Add reference audio as assistant message
            audio_base64 = encode_audio_base64(reference_audio_path)
            audio_content = AudioContent(raw_audio=audio_base64, audio_url="")
            ref_assistant_message = Message(role="assistant", content=[audio_content])
            messages.append(ref_assistant_message)
        
        # Add main text to synthesize
        text = normalize_text(text)
        user_message = Message(role="user", content=text)
        messages.append(user_message)
        
        # Create ChatMLSample
        chatml_sample = ChatMLSample(messages=messages)
        
        logger.debug(f"Created ChatMLSample with {len(messages)} messages")
        return chatml_sample
        
    except Exception as e:
        logger.error(f"Error in prepare_chatml_sample: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Fallback: create a minimal sample
        fallback_messages = [
            Message(role="user", content=normalize_text(text))
        ]
        return ChatMLSample(messages=fallback_messages)

async def synthesize_speech(
    text: str,
    reference_audio_data: Optional[bytes] = None,
    reference_text: Optional[str] = None,
    temperature: float = 0.7,
    top_p: float = 0.95,
    top_k: int = 50,
    seed: Optional[int] = None
) -> bytes:
    """Synthesize speech using Higgs engine with optional voice cloning"""
    if higgs_engine is None:
        raise HTTPException(status_code=500, detail="TTS engine not initialized")
    
    temp_file = None
    try:
        # Set random seed if provided
        set_random_seed(seed)
        
        # Save reference audio to temp file if provided
        if reference_audio_data:
            logger.info(f"Processing reference audio ({len(reference_audio_data)} bytes)")
            temp_file = save_temp_audio(reference_audio_data)
        
        # Prepare ChatML sample
        chatml_sample = prepare_chatml_sample(
            text=text,
            reference_audio_path=temp_file,
            reference_text=reference_text
        )
        
        logger.info(f"Generating audio for text: '{text[:100]}...'")
        if temp_file:
            logger.info(f"Using voice cloning with reference audio: {temp_file}")
        
        # Generate audio with error handling
        try:
            response = higgs_engine.generate(
                chat_ml_sample=chatml_sample,
                max_new_tokens=1024,
                temperature=temperature,
                top_k=top_k if top_k > 0 else None,
                top_p=top_p,
                stop_strings=DEFAULT_STOP_STRINGS,
                ras_win_len=7,
                ras_win_max_num_repeat=2,
                force_audio_gen=True
            )
        except Exception as gen_error:
            logger.error(f"Generation error: {gen_error}")
            logger.error(f"Generation traceback: {traceback.format_exc()}")
            
            # Try with minimal parameters
            logger.info("Retrying with minimal parameters...")
            response = higgs_engine.generate(
                chat_ml_sample=chatml_sample,
                max_new_tokens=512,
                temperature=0.8,
                force_audio_gen=True
            )
        
        if response.audio is None:
            raise HTTPException(status_code=500, detail="No audio generated by model")
        
        # Convert to WAV bytes
        audio_tensor = torch.from_numpy(response.audio).unsqueeze(0)
        
        # Ensure proper sample rate
        if hasattr(response, 'sampling_rate'):
            sample_rate = response.sampling_rate
        else:
            sample_rate = SAMPLE_RATE
        
        # Save to bytes
        buffer = io.BytesIO()
        torchaudio.save(buffer, audio_tensor, sample_rate, format="WAV")
        audio_bytes = buffer.getvalue()
        
        logger.info(f"Generated audio: {len(audio_bytes)} bytes at {sample_rate}Hz")
        return audio_bytes
        
    except Exception as e:
        logger.error(f"Synthesis error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")
    finally:
        # Always cleanup temp file
        if temp_file:
            cleanup_temp_file(temp_file)

# ==================== FastAPI App ====================
app = FastAPI(
    title="Higgs V2 Audio API",
    description="OpenAI-compatible TTS API with voice cloning",
    version="2.0.2"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Startup/Shutdown ====================
@app.on_event("startup")
async def startup_event():
    """Initialize Higgs engine on startup"""
    global higgs_engine
    try:
        logger.info(f"Initializing Higgs Audio V2 on {device}...")
        higgs_engine = HiggsAudioServeEngine(
            model_name_or_path=MODEL_PATH,
            audio_tokenizer_name_or_path=AUDIO_TOKENIZER_PATH,
            device=device
        )
        logger.info("✅ Higgs Audio V2 initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Higgs: {e}")
        logger.error(f"Initialization traceback: {traceback.format_exc()}")
        # Continue anyway for testing

# ==================== API Endpoints ====================
@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model": "higgs-v2",
        "device": str(device),
        "engine_loaded": higgs_engine is not None,
        "max_audio_size_mb": MAX_FILE_SIZE_MB,
        "endpoints": {
            "get": "/{text}?model=higgs&seed=123&audio=base64_or_url",
            "post": "/openai"
        }
    }

@app.get("/{text:path}")
async def generate_speech_get(
    text: str = Path(..., description="Text to synthesize"),
    model: str = "higgs",
    seed: Optional[int] = None,
    audio: Optional[str] = None
):
    """Generate speech from text using GET (Pollinations format)"""
    try:
        # URL decode the text
        text = unquote(text)
        logger.info(f"GET TTS request: '{text[:50]}...', seed={seed}, has_audio={audio is not None}")
        
        # Handle reference audio
        reference_audio_data = None
        if audio:
            if audio.startswith(("http://", "https://")):
                # Download from URL
                logger.info(f"Downloading reference audio from URL: {audio}")
                reference_audio_data = await download_audio(audio)
            else:
                # Decode base64
                logger.info("Decoding base64 reference audio")
                reference_audio_data = validate_and_decode_base64_audio(audio)
        
        # Generate speech
        audio_data = await synthesize_speech(
            text=text,
            reference_audio_data=reference_audio_data,
            seed=seed
        )
        
        return Response(
            content=audio_data,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "inline; filename=speech.wav",
                "Content-Length": str(len(audio_data))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GET TTS error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/openai")
async def generate_speech_post(request: OpenAIRequest):
    """Generate speech using OpenAI-compatible format"""
    try:
        # Extract text from messages (use last user message)
        text = ""
        for msg in reversed(request.messages):
            if msg.role == "user":
                text = msg.content
                break
        
        if not text:
            raise HTTPException(status_code=400, detail="No user message found")
        
        logger.info(f"POST TTS request: '{text[:50]}...', seed={request.seed}, has_audio={request.audio is not None}")
        
        # Handle reference audio
        reference_audio_data = None
        if request.audio:
            if request.audio.startswith(("http://", "https://")):
                # Download from URL
                logger.info(f"Downloading reference audio from URL: {request.audio}")
                reference_audio_data = await download_audio(request.audio)
            else:
                # Decode base64
                logger.info("Decoding base64 reference audio")
                reference_audio_data = validate_and_decode_base64_audio(request.audio)
        
        # Generate speech
        audio_data = await synthesize_speech(
            text=text,
            reference_audio_data=reference_audio_data,
            seed=request.seed
        )
        
        # Always return WAV format for consistency
        return Response(
            content=audio_data,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "inline; filename=speech.wav",
                "Content-Length": str(len(audio_data))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"POST TTS error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Error Handlers ====================
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "type": "invalid_request_error",
                "code": exc.status_code
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "Internal server error",
                "type": "internal_error",
                "code": 500
            }
        }
    )

# ==================== Performance Middleware ====================
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# ==================== Main ====================
if __name__ == "__main__":
    import sys
    
    # Parse simple CLI args
    host = "127.0.0.1"
    port = 8000
    
    for arg in sys.argv[1:]:
        if arg.startswith("--host="):
            host = arg.split("=")[1]
        elif arg.startswith("--port="):
            port = int(arg.split("=")[1])
    
    logger.info(f"Starting Higgs V2 API Server")
    logger.info(f"Host: {host}:{port}")
    logger.info(f"Device: {device}")
    logger.info(f"Max audio size: {MAX_FILE_SIZE_MB}MB")
    logger.info(f"GET endpoint: http://{host}:{port}/your_text_here?model=higgs&seed=123&audio=base64_or_url")
    logger.info(f"POST endpoint: http://{host}:{port}/openai")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        loop="uvloop",
        log_level="info"
    )