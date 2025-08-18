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
    system=None,
    reference_audio_data_path: Optional[str] = None,
    reference_audio_text: Optional[str] = None
) -> ChatMLSample:
    logger.info(f"Creating chat template for request {requestID} with text: {text}")
    if not system: 
        systemPromptWrapper: str = """
(
"Generate audio following instruction.\n\n"
<|scene_desc_start|>\n
"You are the storyteller — a strong, bold, masculine voice with natural warmth and emotion. \n
Speak at a steady, moderate pace: never robotic, never rushed. \n
Add natural breathing, subtle pauses, and the occasional thoughtful ‘hmm’ or sigh — the way a real person would. \n
Guide the listener through emotions: let suspense hang in the air with slower pacing; brighten the tone and quicken slightly with excitement; soften and lower your voice in moments of calm or intimacy. \n
Think like a performer, not a narrator. Adjust your delivery dynamically: raise your voice to energize, whisper as if sharing a secret, or let silence build tension. \n
Every sentence should feel intentional — as if you’re painting the scene with sound, keeping the listener hooked. \n
Remember: this isn’t text-to-speech. This is performance — breathing life, drama, and emotion into every word." \n
<|scene_desc_end|>
)
"""


    else:
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

    messages = []
    # Add system prompt
    messages.append(
        Message(
            role="system",
            content=systemPromptWrapper,
        )
    )

    if reference_audio_data_path:
        with open(reference_audio_data_path, "rb") as f:
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
    
    return ChatMLSample(messages=messages)


if __name__ == "__main__":
    template = create_speaker_chat(
        "An old woman with a very happy emotional voice, celebrating about her success in life",
        "request-123",
        "Recorded in a very noisy street"
    )
    print(template)