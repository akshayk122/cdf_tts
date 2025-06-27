import io
import time
import os
import logging
import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Body
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import texttospeech
from google.cloud import speech
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Text-to-Speech and Speech-to-Text API",
    description="API for converting text to speech and speech to text using Google Cloud services",
    version="1.0.0"
)

# Add CORS middleware to allow cross-origin requests from the React app
# IMPORTANT: In a production environment, narrow 'allow_origins' to your specific frontend URL(s)

ALLOWED_ORIGINS = [
    "https://your-react-app-domain.com",  # Your React app's domain  # If using Netlify
    # Add other trusted domains that need access
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development ease. Restrict this for production.
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Allows all methods
    allow_headers=["Content-Type"], # Allows all headers
)

# Create static folder for audio files if it doesn't exist
# (Still useful if you plan to save files for other purposes, but not for direct TTS streaming)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Google Cloud clients
# These clients should ideally be initialized only once when the app starts
tts_client = None
stt_client = None

try:
    tts_client = texttospeech.TextToSpeechClient()
    stt_client = speech.SpeechClient()
    logger.info("Successfully initialized Google Cloud clients")
except Exception as e:
    logger.error(f"Error initializing Google Cloud clients: {e}")
    # In a real production app, you might want to gracefully degrade or exit here
    # For now, we'll let it raise to prevent the app from starting without clients.
    raise

# Define request model for text-to-speech
class TextToSpeechRequest(BaseModel):
    text: str

# Helper generator for StreamingResponse
def audio_stream_generator(audio_content_bytes: bytes):
    """
    A generator function to stream binary data in chunks.
    """
    buffer = io.BytesIO(audio_content_bytes)
    while True:
        chunk = buffer.read(4096)  # Read in 4KB chunks (adjust as needed)
        if not chunk:
            break
        yield chunk

@app.get("/")
async def root():
    return {"message": "Text-to-Speech and Speech-to-Text API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    return {"status": "healthy", "google_clients_initialized": tts_client is not None and stt_client is not None}

@app.post("/api/text-to-speech")
async def text_to_speech(request: TextToSpeechRequest):
    """
    Convert text to speech using Google Cloud Text-to-Speech API
    and stream the audio directly back to the client.
    """
    try:
        text = request.text
        logger.info(f"Received text-to-speech request for text: '{text[:50]}...'")
        
        if not text:
            raise HTTPException(status_code=400, detail="Please provide text to convert")
        
        # Configure the synthesis request
        input_text = texttospeech.SynthesisInput(text=text)
        
        # Build the voice request
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Studio-O"  # Using a high-quality voice
        )
        
        # Select the type of audio file
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            speaking_rate=1.0,
            sample_rate_hertz=24000 # Specify output sample rate for consistency
        )
        
        # Perform the text-to-speech request
        tts_response = tts_client.synthesize_speech(
            input=input_text,
            voice=voice,
            audio_config=audio_config
        )
        
        logger.info(f"Successfully synthesized speech for text: '{text[:50]}...'")
        
        # Return the audio content directly as a streaming response
        return StreamingResponse(
            audio_stream_generator(tts_response.audio_content),
            media_type="audio/wav", # Crucial: set the correct MIME type
            headers={"Content-Disposition": "inline; filename=synthesized_audio.wav"}
        )
        
    except Exception as e:
        logger.error(f"Error in text-to-speech: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to synthesize speech: {str(e)}")

@app.post("/api/speech-to-text")
async def speech_to_text(file: UploadFile = File(...)):
    """
    Convert speech to text using Google Cloud Speech-to-Text API.
    Optimized for quick response, designed for short audio clips.
    """
    start_time = time.time()
    logger.info(f"Received speech-to-text request for file: {file.filename}")
    
    # Read the audio file content
    audio_content = await file.read()
    
    if not audio_content:
        raise HTTPException(status_code=400, detail="Empty audio file")
    
    # Configure the speech recognition request
    audio = speech.RecognitionAudio(content=audio_content)
    
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=24000,  # Ensure this matches your audio source
        language_code="en-US",
        model="latest_short",  # Changed to 'latest_short' for general short audio speed
        audio_channel_count=1,
        enable_automatic_punctuation=True,
        # Consider enabling if high accuracy for unique words is needed, but might add latency
        # use_enhanced=True
    )
    
    try:
        logger.info("Attempting synchronous speech recognition (recognize method)")
        # Set a strict timeout for synchronous recognition
        response = stt_client.recognize(config=config, audio=audio, timeout=10) 
        
        # Extract the transcription text
        transcript = ''.join([
            result.alternatives[0].transcript 
            for result in response.results 
            if result.alternatives
        ])
        
        # Calculate processing time
        end_time = time.time()
        processing_time = end_time - start_time
        
        logger.info(f"Speech-to-text completed in {processing_time:.2f} seconds. Transcript: '{transcript[:50]}...'")
        
        if not transcript:
            return {"transcript": "No speech detected", "processing_time_seconds": round(processing_time, 2)}
        
        return {
            "transcript": transcript,
            "processing_time_seconds": round(processing_time, 2)
        }
        
    except Exception as e:
        # If synchronous recognition fails, it's likely a critical issue
        # (e.g., incorrect audio format, network problem, API quota)
        # Avoid falling back to long_running_recognize for quick response applications.
        logger.error(f"Synchronous speech-to-text failed: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Speech-to-text failed. Ensure audio format (encoding, sample rate) is correct and within limits, and check network. Error: {str(e)}"
        )

if __name__ == "__main__":
    # Get port from environment variable or use default
    # Cloud Run often sets the PORT environment variable.
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=True) # reload=True for development
