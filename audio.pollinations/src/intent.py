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
from scriptGenerator import generate_reply
from transcribe import transcribe_audio_from_base64
from voiceMap import VOICE_BASE64_MAP
from requestID import reqID


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("elixpo-audio")

POLLINATIONS_TOKEN = os.getenv("POLLI_TOKEN")
MODEL = os.getenv("MODEL")
REFERRER = os.getenv("REFERRER")
POLLINATIONS_ENDPOINT = "https://text.pollinations.ai/openai"

# synthesis_audio: {b64_save_path_synthesis if b64_save_path_synthesis else None}
# clone_audio_text: {reference_audio_text if reference_audio_text else None}

async def run_elixpoaudio_pipeline(
    reqID: str = None,
    text: str = None,
    speechInput: str = None, #this is b64 speech input for STS or STT 
    clone_audio_path: str = None, #this is b64 voice clone input
    reference_audio_text: str = None, #this is transcript of the cloned voice
    system_instruction: str = None,
    voice: str = "alloy" #default voice
    
):
    clone_audio_path = None
    b64_save_path_synthesis = None
    logger.info(f" [{reqID}] Starting Audio Pipeline")
    if (clone_audio_path):
        clone_audio_path = processCloneInputAudio(clone_audio_path, reqID)
    else:
        if(voice):
            clone_audio_path = VOICE_BASE64_MAP.get(voice, "alloy")

    if (speechInput):
       b64_save_path_synthesis = processSynthesisInputAudio(speechInput, reqID)
    logger.info(f"[{reqID}] Saved base64 for the required media ")

    
    try:
        messages = [
    {
    "role": "system",
    "content": """
You are Elixpo Audio, an advanced audio synthesis agent. You must follow the pipeline strictly. 
You have access to these tools:
- create_speaker_chat(text, requestID, system, reference_audio_data_path, reference_audio_text)
- generate_higgs_system_instruction(text: str, multiSpeaker: bool, voiceCloning: bool)
- synthesize_speech(chatTemplate_path, higgs_engine)
- generate_reply(prompt: str, max_tokens: int)
- transcribe_audio_from_base64(audio_data: str, reqID: str)

There are 4 Types 
Text to Speech (Direct TTS or Reply TTS) [AUDIO OUTPUT]
Text to Text (Reply TTT) [TEXT OUTPUT]
Speech to Text (Direct STT or Reply STT) [TEXT OUTPUT]
Speech to Speech (Reply STS) [AUDIO OUTPUT]

Read the inputs which will be given to you 
The Prompt, System instruction, Voice-Cloning-Path, User-Provided-Speech, RequestID

From the prompt figure out what the user wants:- 
1. If the user wants TTS then follow this pipeline:
1.1 If the prompt is like generic sentence then get to reply mode
call the generate_reply function to get a reply of the text
1.2 Generate a system instruction if not provided by the user using generate_higgs_system_instruction
1.3 pass the reply and system_instruction to create_speaker_chat
1.4 call the synthesize_speech and generate the audio
1.5 return the audio path with [AUDIO] tag

2. If the user wants TTT then follow this pipeline:
2.1 If the prompt is like generic sentence then get to reply mode
call the generate_reply function to get a reply of the text
2.2 return the text response with [TEXT] tag

3. If the user wants STS then follow this pipeline:
3.1 Pass the Synthesis-Audio path to the transcribe_audio_from_base64 and get the text
3.2 Understand the text and if the text is like generic sentence then get to reply mode
call the generate_reply function to get a reply of the text
3.3 pass the reply and system_instruction to create_speaker_chat
3.4 call the synthesize_speech and generate the audio
3.5 return the audio path with [AUDIO] tag

4. If the user wants STT then follow this pipeline:
4.1  Pass the Synthesis-Audio path to the transcribe_audio_from_base64 and get the text
4.2 Understand the text and if the text is like generic sentence then get to reply mode
call the generate_reply function to get a reply of the text
4.3 return the text response with [TEXT] tag.

Important:- If clone_audio_path is provided then regardless of whether 
the system is TTS or STS 
add the clone_audio_path to the create_speaker_chat 

Make sure that the pipeline is strict and all the details are decided -- 
ALWAYS -- call the create_speaker_chat function before the synthesize_speech function 
should be called only once with all the arguments set, so process everything before function calling.
Always make a system_instruction ready
The final message must contain only one tag: [AUDIO] or [TEXT]
    """
    },
    {
        "role": "user",
        "content": f"""
        RequestID: {reqID}
        prompt: {text}
        system_instruction: {system_instruction if system_instruction else None}
        clone_audio_path: {clone_audio_path if clone_audio_path else None}
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
            print(tool_calls)
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
                        clone_audio_path = fn_args.get("clone_audio_path")
                        reference_audio_text = fn_args.get("reference_audio_text")
                        chatTemplate = create_speaker_chat(
                            text=text,
                            requestID=requestID,
                            system=system,
                            clone_audio_path=clone_audio_path,
                            reference_audio_text=reference_audio_text if reference_audio_text else None
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

                    elif fn_name == "generate_reply":
                        prompt = fn_args.get("prompt")
                        max_tokens = fn_args.get("max_tokens", 100)
                        script = generate_reply(prompt, max_tokens)
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

            if final_message_content.startswith("[AUDIO]"):
                # Save audio
                result = {
                    "type": "audio",
                    "data": f"genAudio/{reqID}.wav",
                    "reqID": reqID
                }

            elif final_message_content.startswith("[TEXT]"):
                clean_text = final_message_content.replace("[TEXT]", "", 1).strip()

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
                    "message": "Final response missing required [TEXT] or [AUDIO] tag",
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
        requestID = reqID()
        voice = "ash"

        result = await run_elixpoaudio_pipeline(reqID=requestID, text=text, speechInput=None, clone_audio_path=None, reference_audio_text=None, voice=voice)

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
