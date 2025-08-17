
import os
import io
import json
import time
import traceback
from typing import Optional
from urllib.parse import unquote
import numpy as np
import torch
import sys
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from boson_multimodal.serve.serve_engine import HiggsAudioServeEngine
from config import MODEL_PATH, AUDIO_TOKENIZER_PATH, MAX_FILE_SIZE_MB
from pydanticModels import APIMessage, OpenAIRequest
from utility import normalize_text, download_audio, validate_and_decode_base64_audio
from ttsService import synthesize_speech


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")



app = FastAPI(
    title="Higgs V2 Audio API",
    description="OpenAI-compatible TTS API with voice cloning",
    version="2.0.2"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    try:
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

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


if __name__ == "__main__":
    
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