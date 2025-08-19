import json
from typing import Optional
import os
from boson_multimodal.data_types import ChatMLSample, Message, AudioContent
from boson_multimodal.serve.serve_engine import HiggsAudioServeEngine
from loguru import logger
from utility import normalize_text
import sys
from config import TEMP_SAVE_DIR


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
higgs_engine: Optional[HiggsAudioServeEngine] = None

def create_speaker_chat(
    text: str,
    requestID: str,
    system: Optional[str] = None,
    clone_audio_path: Optional[str] = None,
    reference_audio_text: Optional[str] = None
) -> ChatMLSample:
    logger.info(f"Creating chat template for request {requestID} with text: {text}")
    messages = []
    if system:
        if "<|scene_desc_start|>" in system and "<|scene_desc_end|>" not in system:
            systemPromptWrapper: str = f"""
    (
    Generate audio following instruction.\n
    "Speak at a moderate pace — not too slow, not rushed. \n
    "Build suspense dynamically — speed up or slow down when the moment calls for it. If there’s tension, let the listener feel it; if it’s joyful, let that energy shine through. \n"
    <|scene_desc_start|>\n
    "{system}"
    <|scene_desc_end|>
    )
            """
        else:
            systemPromptWrapper: str = system

        
        messages.append(
            Message(
                role="system",
                content=systemPromptWrapper,
            )
        )


    if clone_audio_path:
        with open(clone_audio_path, "r") as f:
            reference_audio_data = f.read()
        if reference_audio_text:
            messages.append(
                Message(
                    role="user",
                    content=normalize_text(reference_audio_text),
                )
            )
        else:
            messages.append(
                Message(
                    role="user",
                    content="Please clone this voice.",
                )
            )
        
        messages.append(
            Message(
                role="assistant",  
                content=[AudioContent(raw_audio=reference_audio_data, audio_url="")],
            )
        )

    messages.append(
        Message(
            role="user",
            content=normalize_text(text),
        )
    )

    logger.info(f"Created chat template with {len(messages)} messages for request {requestID}")
    os.makedirs(f"{TEMP_SAVE_DIR}{requestID}", exist_ok=True)
    
    def serialize_message(msg: Message):
        # Handles both string and list-of-AudioContent for content
        if isinstance(msg.content, str):
            content = msg.content
        elif isinstance(msg.content, list):
            # Ensure all items are dicts (for AudioContent or future types)
            content = [c.__dict__ if hasattr(c, "__dict__") else c for c in msg.content]
        else:
            # Fallback for unexpected types
            content = str(msg.content)
        return {
            "role": msg.role,
            "content": content
        }

    serialized_messages = [serialize_message(m) for m in messages]

    chat_template_path = f"{TEMP_SAVE_DIR}{requestID}/chatTemplate.json"
    with open(chat_template_path, "w", encoding="utf-8") as f:
        json.dump(serialized_messages, f, ensure_ascii=False, indent=2)

    return chat_template_path


if __name__ == "__main__":
    template = create_speaker_chat(
        "An old woman with a very happy emotional voice, celebrating about her success in life",
        "request-123",
        "Recorded in a very noisy street"
    )
    print(template)
    print(f"Chat template saved to {template}")