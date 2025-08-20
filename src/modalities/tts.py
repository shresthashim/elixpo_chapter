from templates import create_speaker_chat
from synthesis import synthesize_speech
from scriptGenerator import generate_reply
from systemInstruction import generate_higgs_system_instruction


def generate_tts(text: str,  requestID: str, system: str = None, clone_path: str = None, clone_text: str = None, type: str = "direct", multiSpeaker: bool = False) -> bytes:
    if type == "direct":
        if system is None:
            system = generate_higgs_system_instruction(text, multiSpeaker=multiSpeaker)
        prepareChatTemplate =  create_speaker_chat(
            text = text,
            requestID = requestID,
            system = system,
            clone_audio_path = clone_path,
            clone_audio_transcript = clone_text
        )
        audio_bytes = synthesize_speech(prepareChatTemplate)
        return audio_bytes
    

if __name__ == "__main__":
    # Example usage
    text = "A tense courtroom drama where the verdict is about to be announced."
    requestID = "request123"
    system = "You are a voice synthesis engine. Speak the user’s text exactly and only as written. Do not add extra words, introductions, or confirmations."
    clone_path = None  # Path to cloned audio if available
    clone_text = None  # Transcript of cloned audio if available
    multiSpeaker = True  # Set to True for multi-speaker mode

    audio_bytes = generate_tts(text, requestID, system, clone_path, clone_text, type="direct", multiSpeaker=multiSpeaker)
    with open("output.wav", "wb") as f:
        f.write(audio_bytes)
    print("Audio saved as output.wav")
