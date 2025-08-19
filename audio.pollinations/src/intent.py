import requests
import json
import os
import random
import logging
from datetime import datetime, timezone
from tools import tools
from boson_multimodal.serve.serve_engine import HiggsAudioServeEngine
import asyncio
from utility import encode_audio_base64, validate_and_decode_base64_audio, save_temp_audio
from templates import create_speaker_chat
from systemInstruction import generate_higgs_system_instruction
from synthesis import synthesize_speech


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("elixpo-audio")

POLLINATIONS_TOKEN = os.getenv("POLLI_TOKEN")
MODEL = "mistral"
REFERRER = os.getenv("REFERRER")
POLLINATIONS_ENDPOINT = "https://text.pollinations.ai/openai"


async def run_elixpoaudio_pipeline(
    text: str = None,
    system_instruction: str = None,
    reference_audio: str = None,
    reference_audio_text: str = None,
    reqID: str = None,
    event_id: str = None
):
    logger.info(f"Starting Audio Pipeline for reqID={reqID}")

    def format_sse(event: str, data: str) -> str:
        lines = data.splitlines()
        data_str = ''.join(f"data: {line}\n" for line in lines)
        return f"event: {event}\n{data_str}\n\n"

    def emit_event(event_type, message):
        if event_id:
            return format_sse(event_type, message)
        return None

    initial_event = emit_event("INFO", f" Initiating Audio Pipeline reqID={reqID} ")
    if initial_event:
        yield initial_event

    try:
        current_utc_time = datetime.now(timezone.utc)

        messages = [
            {
                "role": "system",
                "content": f"""
You are an intent router and pipeline orchestrator for a multimodal model called Higgs.

Inputs: 
- text (optional)
- system_instruction (optional)
- reference_audio_data (optional)
- reference_audio_url (optional)
- reference_audio_text (optional)

INTENTS:
- TTS: text → audio
- STT: audio → text
- STS: audio → audio
- TTT: text → text

Decision Framework:
1. If text + system_instruction → could be TTT or TTS.
   - If prompt looks like script/narration request → TTT (use generate_script).
   - Else → TTS (prepare chat template + synthesize_speech).
2. If text only → TTS (if narration) or TTT (if script request).
3. If audio only → STT (use transcribe_audio).
4. If audio + text → STS (default = clone voice, else synthesis).
5. If audio_url provided → download_audio → save_temp_audio.
6. Always propagate reqID in calls.

Performance Guidance:
- For TTS: If system_instruction not present, call generate_higgs_system_instruction to create it.
- For STS: Use reference_audio_text if provided for cloning context.
- Always return audio for TTS/STS, text for STT/TTT.
{current_utc_time}
"""
            },
            {
                "role": "user",
                "content": f"""RequestID: {reqID}
Text: {text}
System Instruction: {system_instruction}
Reference Audio Text: {reference_audio_text}
"""
            }
        ]

        max_iterations = 6
        current_iteration = 0
        final_message_content = None

        while current_iteration < max_iterations:
            current_iteration += 1
            logger.info(f"Iteration {current_iteration} for reqID={reqID}")

            payload = {
                "model": MODEL,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
                "token": POLLINATIONS_TOKEN,
                "referrer": REFERRER,
                "private": True,
                "seed": random.randint(1000, 9999)
            }

            headers = {"Content-Type": "application/json"}

            try:
                response = requests.post(POLLINATIONS_ENDPOINT, headers=headers, json=payload)
                response.raise_for_status()
                response_data = response.json()
            except requests.exceptions.RequestException as e:
                error_text = getattr(e.response, "text", "[No error text]")
                logger.error(f"Pollinations API call failed: {e}\n{error_text}")
                if event_id:
                    yield format_sse("error", f"[ERROR] Pollinations API failed: {e}")
                break

            assistant_message = response_data["choices"][0]["message"]
            messages.append(assistant_message)

            tool_calls = assistant_message.get("tool_calls")
            if not tool_calls:
                final_message_content = assistant_message.get("content")
                break

            tool_outputs = []
            for tool_call in tool_calls:
                fn_name = tool_call["function"]["name"]
                fn_args = json.loads(tool_call["function"]["arguments"])
                logger.info(f"[reqID={reqID}] Executing tool: {fn_name} with args: {fn_args}")

                try:
                    if fn_name == "create_speaker_chat":
                        # tool_result = create_speaker_chat(**fn_args)
                        pass

                    else:
                        tool_result = f"[ERROR] Unknown tool: {fn_name}"

                except Exception as e:
                    tool_result = f"[ERROR] Tool {fn_name} failed: {type(e).__name__}: {e}"
                    logger.error(f"Error executing tool {fn_name}: {e}", exc_info=True)

                tool_outputs.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": fn_name,
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })

            messages.extend(tool_outputs)
            logger.info(f"Completed tool execution for iteration {current_iteration} reqID={reqID}")

        if final_message_content:
            logger.info(f"Final content for reqID={reqID}")
            if event_id:
                yield format_sse("final", final_message_content)
            else:
                print(final_message_content)
            return
        else:
            error_msg = f"[ERROR] Audio Pipeline failed after {max_iterations} iterations for reqID={reqID}"
            logger.error(error_msg)
            if event_id:
                yield format_sse("error", error_msg)

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
    finally:
        logger.info(f"Audio Pipeline Completed for reqID={reqID}")




if __name__ == "__main__":

    async def main():
        audio = "audio.wav"
        # base64_audio = encode_audio_base64(audio)
        # audio_bytes = validate_and_decode_base64_audio(base64_audio)
        # saved_audio = save_temp_audio(audio_bytes, "test_req_id", useCase="clone")
        # print(saved_audio)
        audio_text = "Welcome to Elixpo"
        text = "Speak this out for me -- in a calm cozy voice 'Hey, welcome to the test run for MOE Service'"
        logger.info(f"Creating chat template now!")
        systemInstruction = generate_higgs_system_instruction(text, False)
        print(f"System Instruction: {systemInstruction}")
        text = "Hey, welcome to the test run for MOE Service"
        chatTemplate, reqID = create_speaker_chat(text, "test_req_id", system=systemInstruction, reference_audio_path=audio, reference_audio_text=audio_text)
        print(f"Chat Template created with request ID: {reqID}")
        # print(chatTemplate)
        higgs_engine = HiggsAudioServeEngine("bosonai/higgs-audio-v2-generation-3B-base", "bosonai/higgs-audio-v2-tokenizer")
        audio = await synthesize_speech(chatTemplate, higgs_engine=higgs_engine)
        with open("output_intent.wav", "wb") as f:
            f.write(audio)
        print("Audio saved as output_intent.wav")
    asyncio.run(main())