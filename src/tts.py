from templates import create_speaker_chat
from synthesis import synthesize_speech
from scriptGenerator import generate_reply
from systemInstruction import generate_higgs_system_instruction
from utility import encode_audio_base64
from typing import Optional
from voiceMap import VOICE_BASE64_MAP
import asyncio
from load_models import higgs_engine

async def generate_tts(text: str,  requestID: str, system: Optional[str] = None, clone_path: Optional[str] = None, clone_text: Optional[str] = None, type: str = "direct", voice: Optional[str] = "alloy") -> bytes:
    if clone_path is None:
        if(voice):
            load_audio_path = VOICE_BASE64_MAP.get(voice)
            base64 = encode_audio_base64(load_audio_path)    
            clone_path = base64

    if type == "direct":
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
        print(f"The formatted system instruction is:- {system}")
        prepareChatTemplate =  create_speaker_chat(
            text = text,
            requestID = requestID,
            system = system,
            clone_audio_path = clone_path,
            clone_audio_transcript = clone_text
        )
        print(f"The prepared chat template is {prepareChatTemplate}")
        audio_bytes = await synthesize_speech(prepareChatTemplate, higgs_engine=higgs_engine)
        return audio_bytes
    elif type == "reply":
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
        print(f"The formatted system instruction is:- {system}")
        replyText = await generate_reply(text)
        prepareChatTemplate =  create_speaker_chat(
            text = replyText,
            requestID = requestID,
            system=system,
            clone_audio_path=clone_path,
            clone_audio_transcript=clone_text
        )
        print(f"The prepared chat template is {prepareChatTemplate}")
        audio_bytes = await synthesize_speech(prepareChatTemplate, higgs_engine=higgs_engine)
        return audio_bytes


if __name__ == "__main__":
    async def main():
        text = "Such a beautiful day to start with!! What's on your mind?"
        requestID = "request123"
        system = None
        voice = "alloy"
        clone_path = None  
        clone_text = None  
        type = "reply"
        
        audio_bytes = await generate_tts(text, requestID, system, clone_path, clone_text, type, voice)
        with open("output_reply.wav", "wb") as f:
            f.write(audio_bytes)
        print("Audio saved as output_reply.wav")
    asyncio.run(main())