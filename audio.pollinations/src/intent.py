from loguru import logger 
import requests
from typing import Optional
from dotenv import load_dotenv
import os 
import asyncio

load_dotenv()

async def getIntentType(text: str, system: Optional[str] = None, max_tokens: Optional[int] = 10) -> str:
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
                    "1.1 If the user is asking to speak or convert text-to-speech directly without any changes"
                    "(e.g., 'transcribe this audio', 'what is this audio saying?', 'please speak this audio for me', 'say as it is'), respond with DIRECT. "
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

    test_text = "Speak it out as it is -- 'This is an awesome solar event happening this year school students will be taken for a field trip!!'"
    test_system = "Transcription system"
    result = asyncio.run(getIntentType(test_text, test_system))
    print(f"Result: {result}")