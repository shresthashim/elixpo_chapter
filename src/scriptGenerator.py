import requests
from dotenv import load_dotenv
from typing import Optional
import os
from loguru import logger

load_dotenv()

def generate_script(prompt: str, max_tokens: Optional[int] = 1024) -> str:
    logger.info(f"Generating script for prompt: {prompt} with max tokens: {max_tokens}")
    payload = {
        "model": "mistral",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a professional scriptwriter AI. "
                    "Given a prompt, you will generate a detailed script with dialogue, narration, and stage directions. "
                    "Keep the script structured, cinematic, and engaging. "
                    "Limit the output to the requested max token length. "
                    "Do not wrap the script in markdown formatting."
                )
            },
            {
                "role": "user",
                "content": f"Prompt: {prompt}\n\nWrite a script of up to {max_tokens} tokens."
            }
        ],
        "temperature": 0.8,
        "stream": False,
        "private": True,
        "token": os.getenv("POLLI_TOKEN"),
        "referrer": "elixpoart",
        "max_tokens": max_tokens
    }

    response = requests.post("https://text.pollinations.ai/openai", json=payload)

    if response.status_code != 200:
        raise RuntimeError(f"Request failed: {response.status_code}, {response.text}")

    data = response.json()

    try:
        script = data["choices"][0]["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"Unexpected response format: {data}") from e

    return script.strip()


if __name__ == "__main__":
    # Example usage
    user_prompt = "A suspenseful sci-fi scene where astronauts discover signs of alien life on Mars."
    script = generate_script(user_prompt, max_tokens=1024)

    print("\n--- Generated Script ---\n")
    print(script)
