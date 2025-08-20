import requests
import json
import os
import random
import logging
from fastapi import HTTPException
import asyncio
from load_models import higgs_engine
from tools import tools
from config import TEMP_SAVE_DIR
from utility import processCloneInputAudio, processSynthesisInputAudio, cleanup_temp_file
from templates import create_speaker_chat
from systemInstruction import generate_higgs_system_instruction
from synthesis import synthesize_speech
from scriptGenerator import generate_reply
from transcribe import transcribe_audio_from_base64
from voiceMap import VOICE_BASE64_MAP
from requestID import reqID


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("elixpo-audio")

POLLINATIONS_TOKEN = os.getenv("POLLI_TOKEN")
MODEL = os.getenv("MODEL")
REFERRER = os.getenv("REFERRER")
POLLINATIONS_ENDPOINT = "https://text.pollinations.ai/openai"