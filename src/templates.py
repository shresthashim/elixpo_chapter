from typing import Optional
import os
from boson_multimodal.data_types import ChatMLSample, Message, AudioContent
from boson_multimodal.serve.serve_engine import HiggsAudioServeEngine
from loguru import logger
from utility import normalize_text
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
higgs_engine: Optional[HiggsAudioServeEngine] = None

def create_speaker_chat(
    text: str,
    requestID: str,
    system: Optional[str] = None,
    reference_audio_path: Optional[str] = None,
    reference_audio_text: Optional[str] = None
) -> ChatMLSample:
    logger.info(f"Creating chat template for request {requestID} with text: {text}")
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

    messages = []
    messages.append(
        Message(
            role="system",
            content=systemPromptWrapper,
        )
    )

    if reference_audio_path:
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
                content=[AudioContent(audio_url=reference_audio_path)],
            )
        )

    messages.append(
        Message(
            role="user",
            content=normalize_text(text),
        )
    )

    logger.info(f"Created chat template with {len(messages)} messages for request {requestID}")
    
    return ChatMLSample(messages=messages), requestID


if __name__ == "__main__":
    template, request_id = create_speaker_chat(
        "An old woman with a very happy emotional voice, celebrating about her success in life",
        "request-123",
        "Recorded in a very noisy street"
    )
    print(template)
    os.makedirs(f"/temp/higgs/{request_id}/", exist_ok=True)
    with open(f"/temp/higgs/{request_id}/chatTemplate.txt", "w", encoding="utf-8") as f:
        f.write(str(template))