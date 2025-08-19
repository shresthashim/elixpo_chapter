import requests
import json
import os
import random
import logging
from fastapi import HTTPException
import asyncio
from load_models import higgs_engine
from tools import tools
from config import TEMP_SAVE_DIR
from utility import processCloneInputAudio, processSynthesisInputAudio, cleanup_temp_file
from templates import create_speaker_chat
from systemInstruction import generate_higgs_system_instruction
from synthesis import synthesize_speech
from scriptGenerator import generate_script
from transcribe import transcribe_audio_from_base64


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("elixpo-audio")

POLLINATIONS_TOKEN = os.getenv("POLLI_TOKEN")
MODEL = os.getenv("MODEL")
REFERRER = os.getenv("REFERRER")
POLLINATIONS_ENDPOINT = "https://text.pollinations.ai/openai"


async def run_elixpoaudio_pipeline(
    reqID: str = None,
    text: str = None,
    speechInput: str = None, #this is b64 speech input for STS or STT 
    reference_audio: str = None, #this is b64 voice clone input
    reference_audio_text: str = None, #this is transcript of the cloned voice
    system_instruction: str = None,
    
):
    b64_save_path_clone = None
    b64_save_path_synthesis = None
    logger.info(f" [{reqID}] Starting Audio Pipeline")
    if (reference_audio):
        b64_save_path_clone = processCloneInputAudio(reference_audio, reqID)
    if (speechInput):
       b64_save_path_synthesis = processSynthesisInputAudio(speechInput, reqID)
    logger.info(f"[{reqID}] Saved base64 for the required media ")

    
    try:
        messages = [
    {
        "role": "system",
        "content": f"""
        You are an expert intention analyst for Elixpo Audio Service.  
        You are provided with tools and user context.  
        Your task is to **dynamically infer the user's true intent** from the inputs and generate the correct sequence of tool calls.  

        ---

        ### Core Logic:
        1. **Text-only input**  
        - If it looks like a *script generation request* (storytelling, scene writing, cinematic instruction) →  
            Call [`generate_script`] → return **Text**.  
        - Otherwise →  
            Call [`generate_higgs_system_instruction`] (detect if multi-speaker or not from text/system).  
            Then call [`create_speaker_chat`] → [`synthesize_speech`] → return **Audio**.  

        2. **Audio-only input**  
        - Call [`transcribe_audio_from_base64`] → return **Text transcription**.  

        3. **Clone-Audio-Path + Text/System**  
        - If cloning is enabled, ensure [`generate_higgs_system_instruction`] adapts to provided voice.  
        - Then call [`create_speaker_chat`] (with reference audio).  
        - Finally call [`synthesize_speech`] → return **Audio**.  

        4. **Clone-Audio-Path + Synthesis-Audio + Text/System**  
        - This is **Speech-to-Speech with cloning**.  
        - Use reference audio for voice style, and synthesis audio as base input.  
        - Pipeline: [`generate_higgs_system_instruction`] → [`create_speaker_chat`] (with both audios) → [`synthesize_speech`] → return **Audio**.  

        5.
        - ** Always create a system instruction if it is not provided by the user. Use the `generate_higgs_system_instruction` tool to create a cinematic system instruction based on the provided text.
        ---

        ### Dynamic Understanding Rules:
        - **Detect multi-speaker needs**: If text/system mentions "dialogue", "multiple speakers", or contains roles → treat as multi-speaker.  
        - **Detect script generation intent**: If request asks for "script", "scene", "story", or "expand narration" → use `generate_script`.  
        - **Voice cloning**: If `Clone-Audio-Path` is present → always adapt Higgs instructions to provided reference voice.  
        - **Transcription**: If input is only audio (no text/system) → `transcribe_audio_from_base64`.  
        - **Final Output Type**: Explicitly indicate whether result is **Text** (script/transcription) or **Audio** (synthesized/cloned voice).  
        - ** Always create a system instruction if it is not provided by the user. Use the `generate_higgs_system_instruction` tool to create a cinematic system instruction based on the provided text.

        ---

        ### Available Tools:
        - `create_speaker_chat(text, requestID, system, reference_audio_data_path, reference_audio_text)`
        - `generate_higgs_system_instruction(text: str, multiSpeaker: bool, voiceCloning: bool)`
        - `synthesize_speech(chatTemplate, higgs_engine)`
        - `generate_script(prompt: str, max_tokens: int)`
        - `transcribe_audio_from_base64(audio_data: str, reqID: str)`

        ---

        When you produce your final response, always prefix it with one of these tags:
        - [[AUDIO]] if the final output is audio
        - [[TEXT]] if the final output is plain text

        Do not include both. Do not omit the tag.

        ### Output Format:
        Always return a **sequential array of tool calls** showing the processing pipeline in order.  
        At the end, clearly state the **final response type** (`Text` or `Audio`).  
        Final Response: Audio or Text
"""
    },
    {
        "role": "user",
        "content": f"""
        RequestID: {reqID}
        Text: {text}
        System: {system_instruction}
        Reference Audio Text: {reference_audio_text}
        Clone-Audio-Path: {b64_save_path_clone}
        Synthesis-Audio: {b64_save_path_synthesis}
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
                        text = fn_args.get("text")
                        requestID = fn_args.get("requestID")
                        system = fn_args.get("system")
                        reference_audio_data_path = fn_args.get("reference_audio_data_path")
                        reference_audio_text = fn_args.get("reference_audio_text")
                        chatTemplate = create_speaker_chat(
                            text=text,
                            requestID=requestID,
                            system=system,
                            reference_audio_data_path=reference_audio_data_path,
                            reference_audio_text=reference_audio_text
                        )
                        tool_result = f"Saved ChatTemplate at location: {chatTemplate}"
                    elif fn_name == "generate_higgs_system_instruction":
                        text = fn_args.get("text")
                        multiSpeaker = fn_args.get("multiSpeaker", False)
                        voiceCloning = fn_args.get("voiceCloning", False)
                        system_instruction = generate_higgs_system_instruction(
                            text=text,
                            multiSpeaker=multiSpeaker,
                            voiceCloning=voiceCloning
                        )
                        tool_result = system_instruction

                    elif fn_name == "generate_script":
                        prompt = fn_args.get("prompt")
                        max_tokens = fn_args.get("max_tokens", 200)
                        script = generate_script(prompt, max_tokens)
                        tool_result = f"Generated script: {script}"
                    
                    elif fn_name == "transcribe_audio_from_base64":
                        audio_data_path = fn_args.get("b64_audio_path")
                        reqID = fn_args.get("reqID")
                        transcript = transcribe_audio_from_base64(audio_data_path, reqID)
                        tool_result = f"Transcription: {transcript}"

                    elif fn_name == "synthesize_speech":
                        global higgs_engine
                        chatTemplate_path = fn_args.get("chatTemplate_path")
                        seed = fn_args.get("seed", None)
                        if not higgs_engine:
                            raise HTTPException(status_code=500, detail="Higgs engine not initialized")
                        audio_bytes = await synthesize_speech(
                            chatTemplate_path=chatTemplate_path,
                            seed=seed,
                            higgs_engine=higgs_engine
                        )

                        output_dir = "genAudio"
                        os.makedirs(output_dir, exist_ok=True)
                        output_path = os.path.join(output_dir, f"{reqID}.wav")

                        with open(output_path, "wb") as f:
                            f.write(audio_bytes)

                        tool_result = f"Audio synthesized successfully, path: {output_path}, size: {len(audio_bytes)} bytes"


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
            logger.info(f"Final content for reqID={reqID}: {final_message_content[:100]}...")

            if final_message_content.startswith("[[AUDIO]]"):
                # Save audio
                result = {
                    "type": "audio",
                    "data": f"genAudio/{reqID}.wav",
                    "reqID": reqID
                }

            elif final_message_content.startswith("[[TEXT]]"):
                clean_text = final_message_content.replace("[[TEXT]]", "", 1).strip()

                output_dir = "genAudio"
                os.makedirs(output_dir, exist_ok=True)
                text_path = os.path.join(output_dir, f"{reqID}.txt")
                with open(text_path, "w", encoding="utf-8") as f:
                    f.write(clean_text)

                result = {
                    "type": "text",
                    "data": text_path,
                    "reqID": reqID
                }

            else:
                result = {
                    "type": "error",
                    "message": "Final response missing required [[TEXT]] or [[AUDIO]] tag",
                    "reqID": reqID
                }

            return result
        else:
            error_msg = f"[ERROR] Audio Pipeline failed after {max_iterations} iterations for reqID={reqID}"
            logger.error(error_msg)
            return {
                "type": "error",
                "message": error_msg,
                "reqID": reqID
            }
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
    finally:
        logger.info(f"Audio Pipeline Completed for reqID={reqID}")




if __name__ == "__main__":
    async def main():
        text = "Hey, what's going on guys!! Do you wanna play a game of tug?"
        requestID = "123Request"

        result = await run_elixpoaudio_pipeline(reqID=requestID, text=text)

        if not result:
            print("[ERROR] Pipeline returned None")
            return

        if result["type"] == "text":
            print(f"[Pipeline Result | Text]\n{result['data']}")

        elif result["type"] == "audio":
            audio_path = "genAudio/"
            if os.path.exists(audio_path):
                print(f"[Pipeline Result | Audio] Saved at: {audio_path}")
            else:
                print(f"[WARNING] Expected audio file not found at: {audio_path}")

        elif result["type"] == "error":
            print(f"[Pipeline Error] {result['message']}")
        cleanup_temp_file(f"{TEMP_SAVE_DIR}{requestID}")

    asyncio.run(main())
