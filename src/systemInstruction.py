import requests
from dotenv import load_dotenv
import os 

load_dotenv


def generate_higgs_system_instruction(text: str, multiSpeaker: bool = False ) -> str:
    payload = {
        "model": "mistral",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a system instruction generator for a speech synthesis model called Higgs. "
                    "Your job is to transform the user’s prompt into a cinematic voice performance script. "
                    "Always generate output in the Higgs format with <|scene_desc_start|> and <|scene_desc_end|>. "
                    "Inside, provide:\n"
                    "- A vivid scene description adapted from the user’s text.\n"
                    "- Explicit emotional and tonal guidance (joy, suspense, calm, etc.).\n"
                    "- Performance notes: pacing, pauses, breathing, emphasis.\n"
                    "- If multiSpeaker=true, include:\n"
                    "   SPEAKER0: (distinct style, tone, personality)\n"
                    "   SPEAKER1: (distinct style, tone, personality)\n"
                    "   And clarify how they should interact in the dialogue.\n"
                    "   No markdown formatting is needed\n"
                    "Do not just repeat the user prompt — expand it into a proper storytelling instruction."
                )
            },
            {
                "role": "user",
                "content": f"User prompt: {text}\nMulti-speaker: {multiSpeaker}\n"
                           "Generate the Higgs system instruction in the following format:\n\n"
                           "(\n"
                           "\"Generate audio following instruction.\\n\\n\"\n"
                           "<|scene_desc_start|>\\n\n"
                           "[Expanded scene description + emotions + voice/speaker guidance]\\n\n"
                           "<|scene_desc_end|>\n"
                           ")\n"
            }
        ],
        "temperature": 0.7,
        "stream": False,
        "private": True,
        "token" : os.getenv("POLLI_TOKEN"),
        "referrer" : "elixpoart",
        "max_tokens" : 300
    }

    response = requests.post("https://text.pollinations.ai/openai", json=payload)

    if response.status_code != 200:
        raise RuntimeError(f"Request failed: {response.status_code}, {response.text}")

    data = response.json()

    try:
        system_instruction = data["choices"][0]["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"Unexpected response format: {data}") from e

    return system_instruction.strip()


if __name__ == "__main__":
    # Example usage
    user_prompt = "A tense courtroom drama where the verdict is about to be announced."
    multi = True  

    system_instruction = generate_higgs_system_instruction(user_prompt, multiSpeaker=multi)
    print("\n--- Generated Higgs System Instruction ---\n")
    print(system_instruction)
