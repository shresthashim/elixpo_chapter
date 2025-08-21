from scriptGenerator import generate_reply
from systemInstruction import generate_higgs_system_instruction
from transcribe import transcribe_audio_from_base64
from utility import encode_audio_base64, save_temp_audio
from templates import create_speaker_chat
from synthesis import synthesize_speech
from stt import generate_stt
from loguru import logger
from typing import Optional
import asyncio
import requests
import os
from dotenv import load_dotenv
from load_models import higgs_engine


async def generate_sts(text: str, audio_base64_path: str, requestID: str, system: Optional[str] = None, clone_path: Optional[str] = None, clone_text: Optional[str] = None) -> str:
    if system is None:
        system = await generate_higgs_system_instruction(text)
    else:
        system = f"""
        "You are a voice synthesis engine. Speak the user’s text exactly and only as written. Do not add extra words, introductions, or confirmations.\n"
        "Apply the emotions as written in the user prompt.\n"
        "Generate audio following instruction.\n"
        "<|scene_desc_start|>\n"
            {system}\n
        "<|scene_desc_end|>"
        """
    pipelined_transcription = await generate_stt(text, audio_base64_path, requestID, system)
    chatTemplate = create_speaker_chat(
        text=pipelined_transcription,
        requestID=requestID,
        system=system,
        clone_audio_path=clone_path,
        clone_audio_transcript=clone_text
    )
    audio_bytes = await synthesize_speech(chatTemplate, higgs_engine=higgs_engine)
    return audio_bytes


if __name__ == "__main__":
    async def main():
        text = "Is this fact true? Tell me more about it!"
        audio = "sample.wav"
        base264_audio = encode_audio_base64(audio)
        saved_audio_path = save_temp_audio(base264_audio, "request224", "speech")
        requestID = "request123"
        system = None
        clone_path = None
        clone_text = None

        audio_bytes = await generate_sts(text, saved_audio_path, requestID, system, clone_path, clone_text)
        with open("output_sts.wav", "wb") as f:
            f.write(audio_bytes)
        print("Audio saved as output_sts.wav")
    asyncio.run(main())