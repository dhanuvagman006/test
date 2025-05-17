import os
import asyncio
import edge_tts
import requests
import queue
import sounddevice as sd
import json
import subprocess
from vosk import Model, KaldiRecognizer

# === SETUP ===
MODEL_PATH = "models/vosk-model-small-en-us-0.15"
OUTPUT_PATH = "output.mp3"
VOICE = "en-US-JennyNeural"
RATE = "+7%"

API_KEY = 'add u'
API_URL = 'https://openrouter.ai/api/v1/chat/completions'
HEADERS = {
    'Authorization': f'Bearer {API_KEY}',
    'HTTP-Referer': 'https://www.sitename.com',
    'X-Title': 'SiteName',
    'Content-Type': 'application/json',
}

# Load model once
vosk_model = Model(MODEL_PATH)

# === Send message to OpenRouter ===
def send_message(user_input):
    body = {
        'model': 'google/gemma-3-4b-it:free',
        'messages': [
            {'role': 'system', 'content': 'You are a robot named Nexa developed by Nexus Tech club. Just answer in short sentences and don’t use emojis.'},
            {'role': 'user', 'content': user_input}
        ]
    }

    try:
        response = requests.post(API_URL, headers=HEADERS, json=body)
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error communicating with API: {e}")
        return "Sorry, I couldn't process that."

# === Text-to-Speech ===
async def speak(text):
    try:
        communicate = edge_tts.Communicate(text, voice=VOICE, rate=RATE)
        await communicate.save(OUTPUT_PATH)
        subprocess.run(["mpg123", OUTPUT_PATH], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"TTS Error: {e}")

# === Speech Recognition using Vosk ===
def recognize_speech():
    rec = KaldiRecognizer(vosk_model, 16000)
    q = queue.Queue()

    def callback(indata, frames, time, status):
        if status:
            print(status)
        q.put(bytes(indata))

    try:
        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                               channels=1, callback=callback):
            print("🎤 Say something... (or say 'stop' to exit)")
            while True:
                data = q.get()
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "")
                    if text:
                        return text
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return "stop"
    except Exception as e:
        print(f"Microphone error: {e}")
        return "stop"

# === Main Loop ===
def main_loop():
    print("🤖 Nexa is listening. Say 'stop' to exit.")
    loop = asyncio.get_event_loop()
    while True:
        user_input = recognize_speech()
        print(f"You: {user_input}")
        if user_input.lower() in ["exit", "stop", "quit", "shutdown"]:
            print("Nexa: Goodbye!")
            break
        response = send_message(user_input)
        print(f"Nexa: {response}")
        loop.run_until_complete(speak(response))

if __name__ == "__main__":
    main_loop()
