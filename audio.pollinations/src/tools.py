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
                        "description": "Optional system prompt or scene description for the speaker.",
                    },
                    "reference_audio_data_path": {
                        "type": "string",
                        "description" : "Optional, path to the file containing base64 string of the voice to be cloned",
                    },
                    "reference_audio_text": {
                        "type": "string",
                        "description": "Optional text corresponding to the reference audio.",
                    }
                },
                "required": ["query"]
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
                    "chattemplate": {
                        "type": "object",
                        "description": "The chat template object generated for the speaker."
                    },
                    "temp_audio_path": {
                        "type": "string",
                        "description" : "Optional, path to the file containing base64 string of the voice to be cloned",
                    },
                    "seed": {
                        "type": "integer",
                        "description": "Optional random seed for deterministic synthesis."
                    }
                },
                "required": ["chattemplate"]
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
                    }
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_script",
            "description": "Generates a detailed script with dialogue, narration, and stage directions based on a prompt.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt or idea for the script."
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum number of tokens for the generated script.",
                        "default": 1024
                    }
                },
                "required": ["prompt"]
            }
        }
    }
]