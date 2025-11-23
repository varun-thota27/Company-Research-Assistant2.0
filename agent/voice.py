# agent/voice.py
import os
import tempfile
import sounddevice as sd
import soundfile as sf
import pyttsx3

from google import genai
from config import GEMINI_API_KEY, GEMINI_AUDIO_MODEL

# Initialize GenAI client
genai_client = genai.Client(api_key=GEMINI_API_KEY)
AUDIO_MODEL = GEMINI_AUDIO_MODEL

def record_audio(duration_seconds=5, samplerate=16000, channels=1):
    """Record audio for duration_seconds and return local filepath."""
    try:
        duration = float(duration_seconds)
    except Exception:
        duration = 5.0
    samplerate = int(samplerate)
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    print(f"[voice] Recording {duration}s — please speak now...")
    recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=channels, dtype='int16')
    sd.wait()
    sf.write(path, recording, samplerate, subtype='PCM_16')
    print(f"[voice] Saved recording to {path}")
    return path

def transcribe_audio(filepath, model=AUDIO_MODEL):
    """
    Transcribes audio file using Gemini (via google-genai).
    Uses the audio understanding/transcription capability.
    """
    try:
        # The google-genai SDK supports audio transcription; method names vary by version.
        # Common usage (based on examples): client.audio.transcribe(file=..., model=...)
        with open(filepath, "rb") as audio_file:
            try:
                # Preferred high-level API if available
                resp = genai_client.audio.transcribe(model=model, file=audio_file)
                # Parse common resp shapes
                if hasattr(resp, "text"):
                    text = resp.text
                else:
                    text = resp.get("text", "") if isinstance(resp, dict) else str(resp)
            except Exception as inner_e:
                # Try alternate API surface (models.generate_content with audio input)
                # Some SDKs accept 'input_content' or 'contents' that include audio bytes.
                try:
                    # Example using models.generate_content with audio as payload
                    audio_bytes = audio_file.read()
                    response = genai_client.models.generate_content(
                        model=model,
                        contents={"audio": audio_bytes}
                    )
                    text = getattr(response, "text", str(response))
                except Exception as ex2:
                    raise RuntimeError(f"Transcription via genai failed: {inner_e} / {ex2}")
        text = text.strip()
        print(f"[voice] Transcription result: {text}")
        return text
    except Exception as e:
        print(f"[voice] Transcription failed: {e}")
        return ""

def speak_text(text):
    """Speak text using pyttsx3 (offline)."""
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 160)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"[voice] TTS failed: {e}")
