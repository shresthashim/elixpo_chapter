tools = [
    {
        "type": "function",
        "function": {
            "name": "create_speaker_chat",
            "description": "Creates the chat template suited to HIGGS for a speaker with specific instructions and messages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The main text or prompt that the speaker should say."
                    },
                    "requestID": {
                        "type": "string",
                        "description": "A unique identifier for the request."
                    },
                    "system": {
                        "type": "string",
                        "description": "system prompt or scene description for the speaker.",
                    },
                    "clone_audio_path": {
                        "type": "string",
                        "description": "Optional, path to the file containing base64 string of the voice to be cloned",
                    },
                    "clone_audio_transcript": {
                        "type": "string",
                        "description": "Optional text transcript to the reference audio.",
                    }
                },
                "required": ["text", "requestID"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "synthesize_speech",
            "description": "Synthesizes speech audio from a chat template using the HIGGS audio engine.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chatTemplate_path": {
                        "type": "string",
                        "description": "The file path to the chat template generated for the speaker."
                    },
                    "seed": {
                        "type": "integer",
                        "description": "Optional random seed for deterministic synthesis."
                    }
                },
                "required": ["chatTemplate_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_higgs_system_instruction",
            "description": "Generates a cinematic system instruction for the Higgs speech synthesis model, expanding a user prompt into a vivid scene description with emotional and performance guidance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The user prompt or main text to be transformed into a Higgs system instruction."
                    },
                    "multiSpeaker": {
                        "type": "boolean",
                        "description": "Whether the scene involves multiple speakers with distinct styles and interactions."
                    },
                    "voiceCloning": {
                        "type": "boolean",
                        "description": "Whether to adapt the instruction for voice cloning.",
                    }
                },
                "required": ["text", "multiSpeaker", "voiceCloning"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_reply",
            "description": "Generates a detailed script with dialogue, narration, and stage directions based on a prompt used for conversational reply.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt or idea for the reply."
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum number of tokens for the generated script.",
                    }
                },
                "required": ["prompt"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "transcribe_audio_from_base64",
            "description": "Transcribes speech from a base64-encoded audio file using OpenAI Whisper.",
            "parameters": {
                "type": "object",
                "properties": {
                    "synthesis_audio_path": {
                        "type": "string",
                        "description": "Path to the file containing the base64-encoded audio data."
                    },
                    "reqID": {
                        "type": "string",
                        "description": "Unique identifier for the transcription request."
                    },
                    "model_size": {
                        "type": "string",
                        "description": "Optional Whisper model size to use (e.g., tiny, base, small, medium, large).",
                        "default": "small"
                    }
                },
                "required": ["b64_audio_path", "reqID"]
            }
        }
    },
    
]