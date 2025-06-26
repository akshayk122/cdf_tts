from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import texttospeech
from google.cloud import speech
from pydantic import BaseModel
import os
import time
import uvicorn
import logging

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Create static folder for audio files if it doesn't exist
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Google Cloud clients
try:
    tts_client = texttospeech.TextToSpeechClient()
    stt_client = speech.SpeechClient()
    logger.info("Successfully initialized Google Cloud clients")
except Exception as e:
    logger.error(f"Error initializing Google Cloud clients: {e}")
    raise

# Define request model for text-to-speech
class TextToSpeechRequest(BaseModel):
    text: str

@app.get("/")
async def root():
    return {"message": "Text-to-Speech and Speech-to-Text API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    return {"status": "healthy"}

@app.post("/api/text-to-speech")
async def text_to_speech(request: TextToSpeechRequest):
    """
    Convert text to speech using Google Cloud Text-to-Speech API
    """
    try:
        text = request.text
        logger.info(f"Received text-to-speech request: {text[:50]}...")
        
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
            speaking_rate=1.0
        )
        
        # Perform the text-to-speech request
        response = tts_client.synthesize_speech(
            input=input_text,
            voice=voice,
            audio_config=audio_config
        )
        
        # Generate a unique filename using timestamp
        timestamp = int(time.time())
        audio_filename = f"static/output_{timestamp}.wav"
        
        # Save the audio file
        with open(audio_filename, "wb") as out:
            out.write(response.audio_content)
        
        logger.info(f"Successfully generated audio file: {audio_filename}")
        
        # Return the path to the audio file
        return {
            "audio_path": f"/static/output_{timestamp}.wav",
            "text": text
        }
        
    except Exception as e:
        logger.error(f"Error in text-to-speech: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/speech-to-text")
async def speech_to_text(file: UploadFile = File(...)):
    """
    Convert speech to text using Google Cloud Speech-to-Text API
    """
    try:
        start_time = time.time()
        logger.info(f"Received speech-to-text request: {file.filename}")
        
        # Read the audio file content
        audio_content = await file.read()
        
        if not audio_content:
            raise HTTPException(status_code=400, detail="Empty audio file")
        
        # Configure the speech recognition request
        audio = speech.RecognitionAudio(content=audio_content)
        
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=24000,  # Adjust based on your audio files
            language_code="en-US",
            model="command_and_search",  # Faster model for shorter audio clips
            audio_channel_count=1,
            enable_automatic_punctuation=True
        )
        
        # Try synchronous recognition first (faster for short clips)
        try:
            logger.info("Attempting synchronous speech recognition")
            response = stt_client.recognize(config=config, audio=audio)
            
            # Extract the transcription text
            transcript = ''.join([
                result.alternatives[0].transcript 
                for result in response.results 
                if result.alternatives
            ])
            
        except Exception as e:
            # Fall back to asynchronous recognition if synchronous fails
            logger.warning(f"Synchronous recognition failed: {e}, falling back to asynchronous")
            
            operation = stt_client.long_running_recognize(config=config, audio=audio)
            response = operation.result(timeout=90)
            
            # Extract the transcription text
            transcript = ''.join([
                result.alternatives[0].transcript 
                for result in response.results 
                if result.alternatives
            ])
        
        # Calculate processing time
        end_time = time.time()
        processing_time = end_time - start_time
        
        logger.info(f"Speech-to-text completed in {processing_time:.2f} seconds")
        
        if not transcript:
            return {"transcript": "No speech detected", "processing_time_seconds": round(processing_time, 2)}
        
        return {
            "transcript": transcript,
            "processing_time_seconds": round(processing_time, 2)
        }
        
    except Exception as e:
        logger.error(f"Error in speech-to-text: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run("app:app", host=host, port=port) 