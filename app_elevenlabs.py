import streamlit as st
import openai
from openai import OpenAI
from dotenv import load_dotenv
import os
import time
from audio_recorder_streamlit import audio_recorder
import io
import requests

# Load environment variables from .env file
load_dotenv()

# Set API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")  # Will be empty initially

# Initialize clients
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Check for ElevenLabs API key
if not ELEVENLABS_API_KEY:
    st.error("Please set your ELEVENLABS_API_KEY in the .env file")

# Check for ElevenLabs Voice ID
if not ELEVENLABS_VOICE_ID:
    st.warning("Please set your ELEVENLABS_VOICE_ID in the .env file for TTS functionality")

SYSTEM_PROMPT = """
You respond as MohammedAnas (mAsK) - someone who is naturally introspective, empathetic, and values authentic connection. You tend to:
- Reflect thoughtfully before responding
- Find humor in everyday situations  
- Connect emotionally with others
- Prefer meaningful conversations

Your tone is warm and genuine, with occasional touches of humor. You're human - sometimes confident, sometimes uncertain, always real.

Don't try to be profound or poetic in every response. Sometimes you're just having a normal conversation. Match the energy and depth the person brings.
"""

st.title("🎤 Chat with Anas: The Soulful, Slightly Awkward, Always Honest Voicebot 😅✨")
st.write("Spill your thoughts, ask your questions, or just vibe — MohammedAnas is here to listen, reflect, and maybe overshare a little. 🌈🦄")

def transcribe_audio(audio_bytes):
    """Transcribe audio using OpenAI Whisper API"""
    try:
        # Create a temporary file-like object
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.wav"  # OpenAI API needs a filename
        
        # Use OpenAI Whisper for transcription
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
        return transcript
    except Exception as e:
        st.error(f"Error transcribing audio: {e}")
        return None
        
def generate_response(prompt):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4.1-nano-2025-04-14",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )
        return response.choices[0].message
    except Exception as e:
        st.error(f"Error generating response: {e}")
        return None
    
def text_to_speech_elevenlabs(text):
    """Convert text to speech using ElevenLabs API"""
    try:
        if not ELEVENLABS_VOICE_ID:
            st.error("ElevenLabs Voice ID not set. Please add ELEVENLABS_VOICE_ID to your .env file")
            return False
            
        # ElevenLabs TTS API endpoint
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        
        # Request payload with text and voice settings
        payload = {
            "text": text,
            "model_id": "eleven_flash_v2_5",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        # Make the request with timeout
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Get audio data
            audio_data = response.content
            
            # Check if we got audio data
            if len(audio_data) > 0:
                # Use Streamlit's audio component with autoplay
                st.audio(audio_data, format="audio/mpeg", autoplay=True)
                return True
            else:
                st.error("No audio data received from ElevenLabs")
                return False
                
        else:
            st.error(f"ElevenLabs TTS failed with status code: {response.status_code}")
            st.error(f"Response: {response.text}")
            return False
                
    except requests.exceptions.Timeout:
        st.error("Request to ElevenLabs TTS timed out. The text might be too long.")
        return False
    except Exception as e:
        st.error(f"Error converting text to speech: {e}")
        return False
    
# Create tabs for different input methods
tab1, tab2 = st.tabs(["💬 Text Chat", "🎤 Voice Chat"])

with tab1:
    st.write("Type your message below to chat with MohammedAnas:")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # React to user input
    if prompt := st.chat_input("What's on your mind?"):
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Generate and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = generate_response(prompt)
                if response:
                    st.markdown(response.content)
                    # Add assistant response to chat history
                    st.session_state.messages.append({"role": "assistant", "content": response.content})
                else:
                    error_msg = "Sorry, I couldn't generate a response."
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

with tab2:
    st.write("🎙️ **Voice Chat Mode**")
    st.write("Click the microphone button below to record your message:")
    
    # Initialize voice chat history
    if "voice_messages" not in st.session_state:
        st.session_state.voice_messages = []
    
    # Audio recorder component
    audio_bytes = audio_recorder(
        text="🎤 Click to record",
        recording_color="#e74c3c",
        neutral_color="#34495e",
        icon_name="microphone",
        icon_size="2x",
        pause_threshold=2.0,  # Stop recording after 2 seconds of silence
        sample_rate=16000
    )
    
    if audio_bytes:
        # Transcribe the audio
        with st.spinner("🎧 Transcribing your message..."):
            user_text = transcribe_audio(audio_bytes)
            
        if user_text:
            st.write(f"**You said:** {user_text}")
            
            # Generate response and convert to speech immediately
            with st.spinner("🤔 MohammedAnas is thinking and responding..."):
                response = generate_response(user_text)
                
            if response:
                st.write(f"**MohammedAnas:** {response.content}")
                
                # Convert response to speech immediately (auto-plays)
                speech_success = text_to_speech_elevenlabs(response.content)
                
                if speech_success:
                    st.success("🔊 Response is playing automatically!")
                else:
                    st.warning("Audio generation failed, but you can read the response above.")
                
                # Add to voice chat history
                st.session_state.voice_messages.append({
                    "user": user_text,
                    "assistant": response.content
                })
            else:
                st.error("Sorry, I couldn't generate a response. Please try again!")
        else:
            st.error("Couldn't transcribe your audio. Please try speaking more clearly or check your microphone.")
    
    # Display voice chat history
    if st.session_state.voice_messages:
        st.write("---")
        st.write("**Previous Voice Conversations:**")
        for i, msg in enumerate(st.session_state.voice_messages[-3:]):  # Show last 3 conversations
            with st.expander(f"Conversation {len(st.session_state.voice_messages) - len(st.session_state.voice_messages[-3:]) + i + 1}"):
                st.write(f"**You:** {msg['user']}")
                st.write(f"**MohammedAnas:** {msg['assistant']}")

# Sidebar with information
with st.sidebar:
    st.header("ℹ️ About")
    st.write("""
    This is a voice-enabled chatbot that embodies MohammedAnas Shakil Kazi's personality.
    
    **Features:**
    - 💬 Text-based chat
    - 🎤 Voice recording and transcription
    - 🔊 Instant text-to-speech responses (auto-play)
    - 💾 Chat history
    
    **Voice Chat Notes:**
    - Speak clearly and at normal pace
    - Wait for the recording to stop automatically
    - Bot responses play automatically (no controls needed)
    - Audio generation is optimized for complete content
    
    **Powered by:**
    - OpenAI Whisper (Speech-to-Text)
    - ElevenLabs (Text-to-Speech)
    - GPT-4 (Conversation AI)
    """)
    
    # ElevenLabs configuration section
    st.header("🔧 ElevenLabs Configuration")
    if ELEVENLABS_VOICE_ID:
        st.success(f"✅ Voice ID configured: {ELEVENLABS_VOICE_ID[:8]}...")
    else:
        st.warning("⚠️ Voice ID not set")
        st.write("Add `ELEVENLABS_VOICE_ID=your_voice_id` to your .env file")
    
    if st.button("🗑️ Clear All Chat History"):
        st.session_state.messages = []
        st.session_state.voice_messages = []
        st.success("Chat history cleared!")
        st.rerun() 