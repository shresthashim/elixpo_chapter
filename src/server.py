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
from requestID import reqID

# Import the pipeline functions
from tts import generate_tts
from ttt import generate_ttt
from sts import generate_sts
from stt import generate_stt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("elixpo-audio")

POLLINATIONS_TOKEN = os.getenv("POLLI_TOKEN")
MODEL = os.getenv("MODEL")
REFERRER = os.getenv("REFERRER")
POLLINATIONS_ENDPOINT = "https://text.pollinations.ai/openai"


async def run_audio_pipeline(
    reqID: str = None,
    text: str = None,
    synthesis_audio_path: str = None, #this is b64 speech input for STS or STT 
    clone_audio_path: str = None, #this is b64 voice clone input
    clone_audio_transcript: str = None, #this is transcript of the cloned voice
    system_instruction: str = None,
    voice: str = "alloy" #default voice
):
    logger.info(f" [{reqID}] Starting Audio Pipeline")
    logger.info(f"Synthesis audio {synthesis_audio_path} | Clone Audio {clone_audio_path}")
    
    # Process clone audio if provided
    if clone_audio_path:
        clone_audio_path = processCloneInputAudio(clone_audio_path, reqID)
    
    # Process synthesis audio if provided
    if synthesis_audio_path:
        synthesis_audio_path = processSynthesisInputAudio(synthesis_audio_path, reqID)
    
    logger.info(f"[{reqID}] Saved base64 for the required media")

    try:
        messages = [
{
    "role": "system",
    "content": """
You are Elixpo Audio, an advanced audio synthesis agent that routes requests to the appropriate pipeline.

Available Functions:
- generate_tts
- generate_ttt
- generate_sts
- generate_stt

Available pipelines:
- TTS (Text-to-Speech): Convert text to audio
- TTT (Text-to-Text): Generate text responses 
- STS (Speech-to-Speech): Convert speech input to speech output
- STT (Speech-to-Text): Convert speech to text

Your job is to analyze the inputs and determine which pipeline to use, then call the appropriate function:

1. **TTS Pipeline**: Use when text input is provided and audio output is desired
   - Call generate_tts with text, requestID, system, clone_path, clone_text, voice

2. **TTT Pipeline**: Use when text input is provided and text output is desired
   - Call generate_ttt with text, requestID, system

3. **STS Pipeline**: Use when synthesis_audio_path is provided and audio output is desired
   - Call generate_sts with text, synthesis_audio_path, requestID, system, clone_path, clone_text, voice

4. **STT Pipeline**: Use when synthesis_audio_path is provided and text output is desired
   - Call generate_stt with text, synthesis_audio_path, requestID, system

Decision logic:
- If synthesis_audio_path is provided:
  - If user wants audio response → STS
  - If user wants text response → STT
- If no synthesis audio is provided:
  - If user wants audio response → TTS
  - If user wants text response → TTT

Analyze the user's request to determine their intent for output type.
"""
},
{
    "role": "user",
    "content": f"""
    requestID: {reqID}
    prompt: {text}
    synthesis_audio_path: {synthesis_audio_path if synthesis_audio_path else None}
    system_instruction: {system_instruction if system_instruction else None}
    clone_audio_path: {clone_audio_path if clone_audio_path else None}
    clone_audio_transcript: {clone_audio_transcript if clone_audio_transcript else None}
    voice: {voice}
    
    Analyze this request and call the appropriate pipeline function.
    """
}
]
        
        max_iterations = 3
        current_iteration = 0
        
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
                final_content = assistant_message.get("content")
                if final_content:
                    logger.info(f"Final response: {final_content}")
                    return {
                        "type": "error",
                        "message": "No pipeline was executed",
                        "reqID": reqID
                    }
                break

            tool_outputs = []
            for tool_call in tool_calls:
                fn_name = tool_call["function"]["name"]
                fn_args = json.loads(tool_call["function"]["arguments"])
                logger.info(f"[reqID={reqID}] Executing pipeline: {fn_name} with args: {fn_args}")

                try:
                    if fn_name == "generate_tts":
                        audio_bytes = await generate_tts(
                            text=fn_args.get("text"),
                            requestID=fn_args.get("requestID"),
                            system=fn_args.get("system"),
                            clone_path=fn_args.get("clone_path"),
                            clone_text=fn_args.get("clone_text"),
                            voice=fn_args.get("voice", "alloy")
                        )
                        
                        # Save audio file
                        output_dir = "genAudio"
                        os.makedirs(output_dir, exist_ok=True)
                        output_path = os.path.join(output_dir, f"{reqID}.wav")
                        
                        with open(output_path, "wb") as f:
                            f.write(audio_bytes)
                        
                        return {
                            "type": "audio",
                            "data": output_path,
                            "reqID": reqID
                        }

                    elif fn_name == "generate_ttt":
                        text_result = await generate_ttt(
                            text=fn_args.get("text"),
                            requestID=fn_args.get("requestID"),
                            system=fn_args.get("system")
                        )
                        
                        # Save text file
                        output_dir = "genAudio"
                        os.makedirs(output_dir, exist_ok=True)
                        text_path = os.path.join(output_dir, f"{reqID}.txt")
                        
                        with open(text_path, "w", encoding="utf-8") as f:
                            f.write(text_result)
                        
                        return {
                            "type": "text",
                            "data": text_path,
                            "reqID": reqID
                        }

                    elif fn_name == "generate_sts":
                        audio_bytes = await generate_sts(
                            text=fn_args.get("text"),
                            audio_base64_path=fn_args.get("synthesis_audio_path"),
                            requestID=fn_args.get("requestID"),
                            system=fn_args.get("system"),
                            clone_path=fn_args.get("clone_path"),
                            clone_text=fn_args.get("clone_text"),
                            voice=fn_args.get("voice", "alloy")
                        )
                        
                        # Save audio file
                        output_dir = "genAudio"
                        os.makedirs(output_dir, exist_ok=True)
                        output_path = os.path.join(output_dir, f"{reqID}.wav")
                        
                        with open(output_path, "wb") as f:
                            f.write(audio_bytes)
                        
                        return {
                            "type": "audio",
                            "data": output_path,
                            "reqID": reqID
                        }

                    elif fn_name == "generate_stt":
                        text_result = await generate_stt(
                            text=fn_args.get("text"),
                            audio_base64_path=fn_args.get("synthesis_audio_path"),
                            requestID=fn_args.get("requestID"),
                            system=fn_args.get("system")
                        )
                        
                        # Save text file
                        output_dir = "genAudio"
                        os.makedirs(output_dir, exist_ok=True)
                        text_path = os.path.join(output_dir, f"{reqID}.txt")
                        
                        with open(text_path, "w", encoding="utf-8") as f:
                            f.write(text_result)
                        
                        return {
                            "type": "text",
                            "data": text_path,
                            "reqID": reqID
                        }

                    else:
                        tool_result = f"Unknown pipeline: {fn_name}"

                except Exception as e:
                    logger.error(f"Error executing pipeline {fn_name}: {e}", exc_info=True)
                    return {
                        "type": "error",
                        "message": f"Pipeline {fn_name} failed: {str(e)}",
                        "reqID": reqID
                    }

                tool_outputs.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": fn_name,
                    "content": "Pipeline executed successfully"
                })

            messages.extend(tool_outputs)

        return {
            "type": "error",
            "message": f"Pipeline execution failed after {max_iterations} iterations",
            "reqID": reqID
        }

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        return {
            "type": "error",
            "message": f"Pipeline error: {str(e)}",
            "reqID": reqID
        }
    finally:
        logger.info(f"Audio Pipeline Completed for reqID={reqID}")


if __name__ == "__main__":
    async def main():
        text = "Speak it out as it is -- 'This is an awesome solar event happening this year school students will be taken for a field trip!!'"
        requestID = reqID()
        voice = "alloy"

        result = await run_audio_pipeline(reqID=requestID, text=text, synthesis_audio_path=None, clone_audio_path=None, clone_audio_transcript=None, voice=voice)

        if not result:
            print("[ERROR] Pipeline returned None")
            return

        if result["type"] == "text":
            print(f"[Pipeline Result | Text] Saved at: {result['data']}")

        elif result["type"] == "audio":
            print(f"[Pipeline Result | Audio] Saved at: {result['data']}")

        elif result["type"] == "error":
            print(f"[Pipeline Error] {result['message']}")
            
        cleanup_temp_file(f"{TEMP_SAVE_DIR}{requestID}")

    asyncio.run(main())