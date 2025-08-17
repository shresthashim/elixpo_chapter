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
    reference_audio_data: Optional[str] = None,
    reference_audio_text: Optional[str] = None
) -> ChatMLSample:
    logger.info(f"Creating chat template for request {requestID} with text: {text}")
    if not system: 
        systemPromptWrapper: str = """
(
"Generate audio following instruction.\n\n"
<|scene_desc_start|>\n
"SPEAKER: MODERATE, BOLD, MASCULINE, PACED VOICE WITH EMOTIONS"\n
"Speak at a moderate pace — not too slow, not rushed. \n
Include natural breathing, small pauses, and even ‘hmm’s when it fits, so it feels real. \n
Build suspense dynamically — speed up or slow down when the moment calls for it. If there’s tension, let the listener feel it; if it’s joyful, let that energy shine through. \n
Make the listener feel the exact emotion: thrill, joy, calm, or suspense. Vary your tone, pacing, and delivery to match the moment. \n
Don’t be flat — sometimes raise your voice with excitement, sometimes soften it, as if sharing a secret. Adjust loudness and tempo to taste, just like a storyteller keeping the audience hooked. \n
Remember, this isn’t just reading text — it’s performing it with emotion, pacing, and flair that pulls the listener into the moment.\n"
<|scene_desc_end|>
)
        """

    else:
        systemPromptWrapper: str = f"""
(
Generate audio following instruction.\n
"Speak at a moderate pace — not too slow, not rushed. \n
Include natural breathing, small pauses, and even ‘hmm’s when it fits, so it feels real. \n
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

    if reference_audio_data:
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