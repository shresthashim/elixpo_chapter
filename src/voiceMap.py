import os
import sys
VOICE_BASE64_MAP = {
    "alloy":   "voices_b64/base64Data/alloy_b64.txt",
    "amuch":   "voices_b64/base64Data/amuch_b64.txt",
    "ash":     "voices_b64/base64Data/ash_b64.txt",
    "ballad":  "voices_b64/base64Data/ballad_b64.txt",
    "coral":   "voices_b64/base64Data/coral_b64.txt",
    "dan":     "voices_b64/base64Data/dan_b64.txt",
    "echo":    "voices_b64/base64Data/echo_b64.txt",
    "fable":   "voices_b64/base64Data/fable_b64.txt",
    "nova":    "voices_b64/base64Data/nova_b64.txt",
    "onyx":    "voices_b64/base64Data/onyx_b64.txt",
    "sage":    "voices_b64/base64Data/sage_b64.txt",
    "shimmer": "voices_b64/base64Data/shimmer_b64.txt",
    "verse":   "voices_b64/base64Data/verse_b64.txt",
}

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python voiceMap.py <voice_name>")
        print("Available voices:", ", ".join(VOICE_BASE64_MAP.keys()))
        exit(1)
    voice = sys.argv[1]
    path = VOICE_BASE64_MAP.get(voice)
    if path:
        abs_path = os.path.abspath(path)
        print(f"Base64 file for '{voice}': {abs_path}")
    else:
        print(f"Voice '{voice}' not found. Available voices: {', '.join(VOICE_BASE64_MAP.keys())}")