import whisper
from config import TRANSCRIBE_MODEL_SIZE, AUDIO_MODEL_PATH, AUDIO_TOKENIZER_PATH
from boson_multimodal.serve.serve_engine import HiggsAudioServeEngine

higgs_engine = HiggsAudioServeEngine(AUDIO_MODEL_PATH, AUDIO_TOKENIZER_PATH)
model = whisper.load_model(TRANSCRIBE_MODEL_SIZE)