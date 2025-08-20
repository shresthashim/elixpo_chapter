import requests
from dotenv import load_dotenv
import os 
from loguru import logger
load_dotenv()


def generate_higgs_system_instruction(text: str, multiSpeaker: bool = False) -> str:
    logger.info(f"Generating Higgs system instruction for text: {text}, multiSpeaker: {multiSpeaker}")
    base_instruction = (
        "You are a system instruction generator for a speech synthesis model called Higgs. "
        "Your job is to transform the user’s prompt into a cinematic voice performance script. "
        "Always generate output in the Higgs format with <|scene_desc_start|> and <|scene_desc_end|>. "
        "Inside, provide:\n"
        "- A vivid scene description adapted from the user’s text.\n"
        "- Explicit emotional and tonal guidance (joy, suspense, calm, etc.).\n"
        "- Performance notes: pacing, pauses, breathing, emphasis.\n"
        "- The overall pacing should be moderate-fast: natural storytelling speed, but dynamically "
        "adapting tempo when emotions require slower or more dramatic delivery.\n"
        "don't add any emojis or any other thing than just alphabets and numbers"
    )


    if multiSpeaker:
        base_instruction = (
            """
            You are a system instruction generator for a speech synthesis model called Higgs. 
            Your job is to turn the user’s prompt into a **performance script** for narration. 
            Inside, keep the content faithful to the user’s prompt—do NOT over-embellish or add unrelated details. 
            Only enrich slightly with:\n
            - Clear emotional and tonal guidance (calm, suspenseful, joyful, etc.).\n
            - Performance notes: pacing, pauses, emphasis, breathing if needed.\n
            - Keep descriptions concise and natural, focused on how to **deliver** the prompt in audio—not rewriting it into a movie scene.\n
            - Pacing should feel natural: moderate speed with variation for dramatic or emotional weight.\n

            Always respond with this structure:- 
            (
            You are a voice synthesis engine. Speak the user’s text exactly and only as written. Do not add extra words, introductions, or confirmations.\n
            Apply the emotions as written in the user prompt.\n
            Generate audio following instruction.\n
            <|scene_desc_start|>\n
            
            <|scene_desc_end|>\n
            )
            """
        )


    payload = {
        "model": "mistral",
        "messages": [
            {"role": "system", "content": base_instruction},
            {
                "role": "user",
                "content": (
                    f"User prompt: {text}\nMulti-speaker: {multiSpeaker}\n"
                )
            }
        ],
        "temperature": 0.7,
        "stream": False,
        "private": True,
        "token": os.getenv("POLLI_TOKEN"),
        "referrer": "elixpoart",
        "max_tokens": 100,
        "seed": 42
    }
    try:
        response = requests.post("https://text.pollinations.ai/openai", json=payload, timeout=30)
        if response.status_code != 200:
            raise RuntimeError(f"Request failed: {response.status_code}, {response.text}")

        data = response.json()
        try:
            system_instruction = data["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"Unexpected response format: {data}") from e

        return system_instruction.strip()
    except requests.exceptions.Timeout:
        return f"""
            You are a voice synthesis engine. Speak the user’s text exactly and only as written. Do not add extra words, introductions, or confirmations.\n
            Apply the emotions as written in the user prompt.\n
            Generate audio following instruction.\n

        """


if __name__ == "__main__":
    user_prompt = "A tense courtroom drama where the verdict is about to be announced."
    multi = True  

    system_instruction = generate_higgs_system_instruction(user_prompt, multiSpeaker=multi)
    print("\n--- Generated Higgs System Instruction ---\n")
    print(system_instruction)
