from scriptGenerator import generate_reply
from systemInstruction import generate_higgs_system_instruction
from transcribe import transcribe_audio_from_base64
from utility import encode_audio_base64, save_temp_audio
from loguru import logger
from typing import Optional
import asyncio
import requests
import os
from dotenv import load_dotenv

load_dotenv()


async def generate_stt(text: str, audio_base64_path: str, requestID: str, system: Optional[str] = None, type: Optional[str] = "DIRECT") -> str:
    transcription = await transcribe_audio_from_base64(audio_base64_path, requestID)
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
    intention = getIntentType(text, system)
    if intention == "DIRECT":
        return transcription.strip()
    if intention == "REPLY":
        get_reply = await generate_reply(f"This is the prompt {text} and this is the transcript {transcription}")
        return get_reply
    else:
        return transcription.strip()

def getIntentType(text: str, system: Optional[str] = None, max_tokens: Optional[int] = 10) -> str:
    logger.info(f"Classifying intent for prompt: {text} with max tokens: {max_tokens}")
    payload = {
        "model": "mistral",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an intent classification AI. "
                    "Your task is to analyze the user's text and output ONLY one word: "
                    "either REPLY or DIRECT. "
                    "Rules: "
                    "1. If the user is asking to transcribe, interpret, or convert speech/audio to text "
                    "(e.g., 'transcribe this audio', 'what is this audio saying?'), respond with DIRECT. "
                    "2. If the user is asking a question, making a statement, or starting a conversation, or asking to do a specific sense respond with REPLY. "
                    "3. Do not output anything except REPLY or DIRECT. "
                    "4. If unsure or an error occurs, default to DIRECT."
                )
            },
            {
                "role": "user",
                "content": f"This is the text prompt  and {text} this is the system instruction {system}"
            }
        ],
        "temperature": 0,
        "stream": False,
        "private": True,
        "token": os.getenv("POLLI_TOKEN"),
        "referrer": "elixpoart",
        "max_tokens": max_tokens
    }

    try:
        response = requests.post("https://text.pollinations.ai/openai", json=payload, timeout=30)
        if response.status_code != 200:
            raise RuntimeError(f"Request failed: {response.status_code}, {response.text}")

        data = response.json()
        try:
            reply: str  = data["choices"][0]["message"]["content"]
            if "---" in reply and "**Sponsor**" in reply:
                sponsor_start = reply.find("---")
                if sponsor_start != -1:
                    sponsor_section = reply[sponsor_start:]
                    if "**Sponsor**" in sponsor_section:
                        reply = reply[:sponsor_start].strip()
            if reply not in ["REPLY", "DIRECT"]:
                reply = "DIRECT"  
        except Exception as e:
            raise RuntimeError(f"Unexpected response format: {data}") from e
        
        print(f"Intent classified as: {reply}")
        return reply
    except requests.exceptions.Timeout:
        logger.warning("Timeout occurred in getIntentType, returning default DIRECT.")
        return "DIRECT"


if __name__ == "__main__":
    async def main():
        audio = "sample.wav"
        base64_audio = encode_audio_base64(audio)
        saved_path = save_temp_audio(base64_audio, "223Req", "speech")
        content = await generate_stt(
            text="is this a true fact?",
            audio_base64_path=saved_path,
            requestID="223Req",
            system=None,
        )
        print(f"Transcription result: {content}")
    asyncio.run(main())

        