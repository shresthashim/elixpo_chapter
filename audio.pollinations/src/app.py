
import os
import io
import json
import time
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
from loguru import logger
from boson_multimodal.serve.serve_engine import HiggsAudioServeEngine, HiggsAudioResponse
from boson_multimodal.data_types import ChatMLSample, Message, AudioContent

from config import MODEL_PATH, AUDIO_TOKENIZER_PATH, SAMPLE_RATE, MAX_FILE_SIZE_MB, DEFAULT_SYSTEM_PROMPT, DEFAULT_STOP_STRINGS
from pydanticModels import APIMessage, OpenAIRequest
from utility import normalize_text, download_audio, validate_and_decode_base64_audio, encode_audio_base64, save_temp_audio, cleanup_temp_file, set_random_seed

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
higgs_engine: Optional[HiggsAudioServeEngine] = None




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