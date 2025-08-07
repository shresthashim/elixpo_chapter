from cli.SparkTTS import SparkTTS
import torch
import soundfile as sf


model = SparkTTS(
    "pretrained_models/Spark-TTS-0.5B",
    torch.device("cuda:0")  
)

chat_history = [
    {"role": "system", "content": "You are Spark‑TTS. Reply with an audio file."},
    {"role": "user", "content": "Hello! Could you say: 'Good morning, how can I assist you today?' in a friendly female voice?"}
]


user_msg = chat_history[-1]["content"]


prompt_audio = "path/to/sample.wav"
prompt_text = "Sample reference text matching the audio"


wav = model.inference(
    text=user_msg,
    prompt_speech_path=prompt_audio,
    prompt_text=prompt_text,
    gender="female",
    pitch="moderate",
    speed="moderate"
)


output_path = "output_conversational.wav"
sf.write(output_path, wav, samplerate=16000)

print(f"User asked: {user_msg}")
print(f"Audio response saved to: {output_path}")
