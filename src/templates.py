from typing import Optional
import os
from boson_multimodal.data_types import ChatMLSample, Message, AudioContent
from boson_multimodal.serve.serve_engine import HiggsAudioServeEngine
from loguru import logger
from utility import normalize_text
import sys


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
higgs_engine: Optional[HiggsAudioServeEngine] = None


def create_speaker_chat(
    text: str,
    requestID: str,
    system=None,
    reference_audio_data: Optional[str] = None,
    reference_audio_text: Optional[str] = None
) -> ChatMLSample:
    if not system: 
        systemPromptWrapper: str = """
        "<|scene_desc_start|>\n"
        "If no instructions are provided follow these -- "
        "Sound totally human: it’s okay to say things like ‘um’, ‘hmm’, or take a short breath before a big detail. Feel free to *slightly* stutter, casually reword something, or chuckle if the moment’s funny — that’s what makes it real. "
        "Add light humor where it fits — just subtle, natural stuff. If something sounds ridiculous or cool, say it like you mean it. Imagine you’re on a podcast and your goal is to keep listeners smiling and hooked. "
        "Speed up naturally — you’re excited to tell this story — but still clear. Use pauses for effect, like after a big stat, or before a surprising twist. Don’t rush, but don’t drag either. "
        "Smile through your voice. Be curious, expressive, slightly sassy if it works. Bring real charm, like you’re sharing this over coffee with a friend. "
        "No robotic reading. No filler. No fake facts. Just bring the script to life with humor, breath, warmth, and energy. "
        "The whole thing should feel like a fun, punchy, real-person monologue that lasts 3 to 4 minutes, tops. Leave listeners grinning, curious, or saying ‘whoa’."
        "Remember, you’re not just reading a script — you’re performing it with personality and flair!"
        "<|scene_desc_end|>"
        """
    else:
        systemPromptWrapper: str = f"""
        "Create natural-sounding audio, with breathing, pauses and hums which will set a clear mood of the user " \
        "adapt to the provided instruction, if given dynamically"
        
        "<|scene_desc_start|>\n"
        "{system}\n"
        "<|scene_desc_end|>"
        """

    userPromptWrapper: str = f"""
    <|generation_instruction_start|>
    {text}
    <|generation_instruction_start|>
    """

    messages = [
        Message(
            role="system",
            content=systemPromptWrapper,
        )
    ]

    if reference_audio_data:
        messages.append(
            Message(
                role="Assistant",
                content=AudioContent(raw_audio=reference_audio_data, audio_url="placeholder"),
            )
        )
        if reference_audio_text:
            messages.append(
                Message(
                    role="user",
                    content=normalize_text(reference_audio_text),
                )
            )

    messages.append(
        Message(
            role="user",
            content=normalize_text(userPromptWrapper),
        )
    )
    
    logger.info(f"Creating chat template with {len(messages)} messages for request {requestID}")
    return ChatMLSample(messages=messages)