from flask import Flask, request, jsonify
from google.cloud import texttospeech
from google.cloud import speech
from google.cloud import storage
from google.cloud import language_v2
import json
import io
import os
import datetime

app = Flask(__name__, static_folder='static')
@app.route('/')
def index():
    return "Hello, World!"

@app.route('/generate_audio', methods=['GET', 'POST'])
def generate_audio():
    try:
        # Get text from form data or use default
        if request.method == 'POST':
            text = request.form.get('text_input', 'Hello, how are you?')
        else:
            text = 'Hello, how are you Akshay?'
        
        if not text:
            return jsonify({"error": "Please provide some text."}), 400
        
        client = texttospeech.TextToSpeechClient()
        input_text = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Studio-O"
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            speaking_rate=1.0
        )
        response = client.synthesize_speech(
            input=input_text, voice=voice, audio_config=audio_config
        )
        
        # Save audio file locally
        audio_filename = 'static/output.wav'
        os.makedirs('static', exist_ok=True)
        with open(audio_filename, 'wb') as out:
            out.write(response.audio_content)
        
        # Return response data
        response_data = {
            "audio_path": f'/static/output.wav',
            "text": text
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/generate_text', methods=['GET', 'POST'])
def generate_text():
    try:
        # Path to the audio file
        audio_path = 'static/output.wav'
        if not os.path.exists(audio_path):
            return jsonify({"error": "Audio file not found."}), 404

        # Read audio content
        with open(audio_path, 'rb') as audio_file:
            audio_content = audio_file.read()

        # Initialize Speech-to-Text Client
        sclient = speech.SpeechClient()
        # Configure recognition settings
        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=24000,  # LINEAR16 default sample rate, adjust if needed
            language_code="en-US",
            model="latest_long",
            audio_channel_count=1,
            enable_word_confidence=True,
            enable_word_time_offsets=True,
        )
        # Try speech recognition with retries
        for attempt in range(3):  # Retry mechanism
            try:
                operation = sclient.long_running_recognize(config=config, audio=audio)
                response = operation.result(timeout=90)
                break
            except Exception as api_exception:
                print(f"Speech-to-Text API failed: {api_exception}")
                if attempt < 2:
                    print(f"Retrying {attempt + 1}/3...")
                else:
                    return jsonify({"error": str(api_exception)}), 500
        print('response done')
        # Process the transcription result
        transcript = ''.join([
            result.alternatives[0].transcript for result in response.results if result.alternatives
        ])
        return jsonify({"transcript": transcript}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500
    


if __name__ == '__main__':
    app.run(debug=True)
