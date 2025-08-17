from typing import Optional
from config import DEFAULT_SYSTEM_PROMPT, DEFAULT_STOP_STRINGS, SAMPLE_RATE
import io
import torch
import torchaudio
import os
from boson_multimodal.data_types import ChatMLSample, Message, AudioContent
from boson_multimodal.serve.serve_engine import HiggsAudioServeEngine
from loguru import logger
from utility import normalize_text, encode_audio_base64, save_temp_audio, cleanup_temp_file, set_random_seed
import traceback
from fastapi import  HTTPException

higgs_engine: Optional[HiggsAudioServeEngine] = None

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