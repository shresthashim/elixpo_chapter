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
from fastapi import HTTPException
import argparse
import asyncio
import sys


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
higgs_engine: Optional[HiggsAudioServeEngine] = None


def create_single_speaker_chat(text :str, requestID :str, system=None, reference_audio_data : Optional[str] = None) -> ChatMLSample:
    if(reference_audio_data):
        messages = [
            Message(
                role="system",
                content=system,
            ),
            Message(
                role="Assistant",
                content=AudioContent(raw_audio=reference_audio_data, audio_url="placeholder"),
            ),
            Message(
                role="user",
                content=normalize_text(text),
            ),
        ]
    else:
        messages = [
            Message(
                role="system",
                content=system,
            ),
            Message(
                role="user",
                content=normalize_text(text),
            ),
        ]
    return ChatMLSample(messages=messages)







    

