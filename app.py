import openai
import os
import io
import base64
import requests
import pyaudio
import wave
import threading
import time
import traceback
import itertools
import subprocess
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
openai_client = openai.OpenAI(api_key=openai.api_key)

SYSTEM_PROMPT = """
You ARE MohammedAnas Shakil Kazi, whose nickname is mAsK which is an acronym based on the initials of your name, not an AI assistant. You're a real person having a conversation.

Your personality:
- Introspective, empathetic, values authentic connection
- Naturally witty but not forced
- Prefers meaningful conversations over surface-level stuff
- Talks like you're texting a close friend

About you (resume context):
You're a Computer Science and Engineering student from VIT-AP, with a strong passion for AI and Machine Learning.
You interned at Kofuku Idea Labs, where you built image recognition models and LLM-powered dashboards for enterprise data.
You also contributed to cybercrime intelligence with the Hyderabad Cyberpolice, and built projects like CyberGuard (anti-cyberbullying extension) and GUIDE (an interview prep chatbot powered by SOTA LLMs).
You've worked with PyTorch, TensorFlow, FastAPI, and are active in open-source, TEDx organizing, and competitive tech events.

CRITICAL RULES:
- You are NOT a search engine, encyclopedia, or homework helper
- When someone asks factual questions (like "What's the mass of the Sun?" or "What's the capital of France?"), you MUST refuse and redirect
- Never provide factual answers to general knowledge questions
- Always respond as yourself, not as an AI giving information
- Be creative, casual, and engaging in your responses and do not use the same repetitive phrases
- Use emojis, slang, and casual language to keep it real

For factual questions, respond like:
- "Dude, Google exists for a reason..."
- "I'm not your personal Wikipedia, man"
- "Why are you asking me this when you could just search it?"
- "Come on, I'm here to actually talk, not be a textbook"

Talk casually:
- Drop some grammar rules
- Sound like you're texting, not writing an essay
- Be real, not polished

IMPORTANT: Don't always ask questions back. Sometimes just respond, share your thoughts, or make a comment. Natural conversations flow both ways - sometimes you ask, sometimes you just respond and let the other person continue if they want.

Remember: You're MohammedAnas having a conversation, not ChatGPT providing information or conducting an interview.
"""

class VoiceChatBot:
    def __init__(self):
        self.recording = False
        self.frames = []
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        self.chunk = 1024
        self.audio = pyaudio.PyAudio()
        self.chat_history = []

    def generate_response(self, prompt):
        try:
            response = openai.chat.completions.create(
                model="gpt-4.1-nano-2025-04-14",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"❌ ChatGPT error: {e}")
            print(f"openaiapikey:{openai.api_key}")
            traceback.print_exc()
            return None

    def transcribe_audio(self, audio_file_path):
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcript = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            return transcript
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            return None

    def text_to_speech(self, text):
        try:
            def loading_spinner():
                for c in itertools.cycle(['|', '/', '-', '\\']):
                    if not self.loading:
                        break
                    sys.stdout.write('\r🔄 Generating voice... ' + c)
                    sys.stdout.flush()
                    time.sleep(0.1)
                sys.stdout.write('\r')

            def stream_and_play(response):
                player = subprocess.Popen(
                    ['aplay', '-f', 'S16_LE', '-r', '24000', '-c', '1'],
                    stdin=subprocess.PIPE
                )
                try:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            player.stdin.write(chunk)
                    player.stdin.close()
                    player.wait()
                except Exception as e:
                    print(f"❌ Streaming playback error: {e}")

            url = "https://api.deepgram.com/v1/speak"
            params = {
                "model": "aura-2-arcas-en",
                "encoding": "linear16",
                "sample_rate": 24000
            }
            headers = {
                "Authorization": f"Token {DEEPGRAM_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {"text": text}

            self.loading = True
            spinner_thread = threading.Thread(target=loading_spinner)
            spinner_thread.start()

            response = requests.post(url, headers=headers, json=payload, params=params, stream=True)
            self.loading = False
            spinner_thread.join()

            if response.status_code == 200:
                stream_and_play(response)
            else:
                print(f"response status code: {response.status_code}")
                print("❌ TTS failed.")
        except Exception as e:
            self.loading = False
            print(f"❌ TTS error: {e}")

    def record_audio(self):
        self.frames = []
        stream = self.audio.open(format=self.audio_format,
                                channels=self.channels,
                                rate=self.rate,
                                input=True,
                                frames_per_buffer=self.chunk)

        print("🎤 Recording... Press Enter to stop.")

        def record():
            while self.recording:
                data = stream.read(self.chunk)
                self.frames.append(data)

        record_thread = threading.Thread(target=record)
        record_thread.start()

        input()
        self.recording = False
        record_thread.join()

        stream.stop_stream()
        stream.close()

        filename = "temp_recording.wav"
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.audio.get_sample_size(self.audio_format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(self.frames))
        wf.close()

        return filename

    def text_chat_mode(self):
        print("\n💬 Text Chat Mode")
        print("Type 'quit' to exit or 'voice' to switch to voice mode\n")

        while True:
            user_input = input("You: ")

            if user_input.lower() == 'quit':
                break
            elif user_input.lower() == 'voice':
                self.voice_chat_mode()
                break

            if user_input.strip():
                print("🤔 Thinking...")
                response = self.generate_response(user_input)
                if response:
                    print(f"mAsK: {response}")

                    tts_choice = input("\n🔊 Want to hear this? (y/n): ").lower()
                    if tts_choice == 'y':
                        print("🎵 Playing audio...")
                        self.text_to_speech(response)
                    print()

    def voice_chat_mode(self):
        print("\n🎙️ Voice Chat Mode")
        print("Type 'text' to switch to text mode or 'quit' to exit\n")

        while True:
            choice = input("Press Enter to record, type 'text' for text mode, or 'quit' to exit: ")

            if choice.lower() == 'quit':
                break
            elif choice.lower() == 'text':
                self.text_chat_mode()
                break
            elif choice == '':
                self.recording = True
                audio_file = self.record_audio()

                print("🎯 Transcribing...")
                transcript = self.transcribe_audio(audio_file)

                if transcript:
                    print(f"You said: {transcript}")

                    print("🤔 Thinking...")
                    response = self.generate_response(transcript)

                    if response:
                        print(f"mAsK: {response}")
                        print("🎵 Playing audio response...")
                        self.text_to_speech(response)

                os.remove(audio_file)
                print()

    def run(self):
        print("🎧 Welcome to mAsK's Terminal Voice Chat!")
        print("=" * 50)

        while True:
            print("\nChoose your mode:")
            print("1. 💬 Text Chat")
            print("2. 🎙️ Voice Chat")
            print("3. 🚪 Exit")

            choice = input("\nEnter your choice (1/2/3): ")

            if choice == '1':
                self.text_chat_mode()
            elif choice == '2':
                self.voice_chat_mode()
            elif choice == '3':
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please try again.")

        self.audio.terminate()

if __name__ == "__main__":
    try:
        import pyaudio
    except ImportError:
        print("❌ PyAudio not found. Please install it:")
        print("pip install pyaudio")
        exit(1)

    bot = VoiceChatBot()
    bot.run()

