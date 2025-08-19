import requests
from dotenv import load_dotenv
import os 
from loguru import logger
load_dotenv()


def generate_higgs_system_instruction(text: str, multiSpeaker: bool = False, voiceCloning: bool = False) -> str:
    logger.info(f"Generating Higgs system instruction for text: {text}, multiSpeaker: {multiSpeaker}, voiceCloning: {voiceCloning}")
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
    )

    if voiceCloning:
        base_instruction += (
            "- IMPORTANT: Voice cloning is enabled. A reference voice has already been provided to the Higgs model. "
            "You must adapt all emotional delivery, pacing, and tonal variations to stay consistent with this provided voice. "
            "Do NOT invent arbitrary new speaker identities; instead, guide how the cloned voice should shift tone, "
            "emotion, and rhythm to match the scene.\n"
        )

    if multiSpeaker:
        base_instruction = (
            "You are a system instruction generator for a speech synthesis model called Higgs. "
            "Your job is to turn the user’s prompt into a **performance script** for narration. "
            "Always respond in the Higgs format with <|scene_desc_start|> and <|scene_desc_end|>. "
            "Inside, keep the content faithful to the user’s prompt—do NOT over-embellish or add unrelated details. "
            "Only enrich slightly with:\n"
            "- Clear emotional and tonal guidance (calm, suspenseful, joyful, etc.).\n"
            "- Performance notes: pacing, pauses, emphasis, breathing if needed.\n"
            "- Keep descriptions concise and natural, focused on how to **deliver** the prompt in audio—not rewriting it into a movie scene.\n"
            "- Pacing should feel natural: moderate speed with variation for dramatic or emotional weight.\n"
        )


    payload = {
        "model": "mistral",
        "messages": [
            {"role": "system", "content": base_instruction},
            {
                "role": "user",
                "content": (
                    f"User prompt: {text}\nMulti-speaker: {multiSpeaker}\nVoice Cloning: {voiceCloning}\n"
                    "Generate the Higgs system instruction in the following format:\n\n"
                    "(\n"
                    "\"Generate audio following instruction.\\n\\n\"\n"
                    "<|scene_desc_start|>\\n\n"
                    "[Expanded scene description + emotions + voice/speaker guidance]\\n\n"
                    "<|scene_desc_end|>\n"
                    ")\n"
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
            You are a lively and natural voice artist, adapt to the prompts 
            and generate the emotions and the feelings of the scene so that 
            it sounds like a perfect performance.

        """


if __name__ == "__main__":
    # Example usage
    user_prompt = "A tense courtroom drama where the verdict is about to be announced."
    multi = True  
    cloning = True  # test with cloning

    system_instruction = generate_higgs_system_instruction(user_prompt, multiSpeaker=multi, voiceCloning=cloning)
    print("\n--- Generated Higgs System Instruction ---\n")
    print(system_instruction)
