import requests
import json
import os
import time

# API base URL - update this if your server is running on a different URL
BASE_URL = "http://localhost:8000"

def test_text_to_speech():
    """Test the text-to-speech endpoint"""
    print("\n=== Testing Text-to-Speech API ===")
    
    # Endpoint URL
    url = f"{BASE_URL}/api/text-to-speech"
    
    # Request payload
    payload = {
        "text": "Hello, this is a test of the text to speech API. How does it sound?"
    }
    
    # Send POST request
    print(f"Sending request to {url}...")
    response = requests.post(url, json=payload)
    
    # Check response
    if response.status_code == 200:
        data = response.json()
        print(f"Success! Audio file created at: {data['audio_path']}")
        print(f"Text: {data['text']}")
        return data['audio_path'].lstrip('/')  # Remove leading slash for local file access
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

def test_speech_to_text(audio_file_path):
    """Test the speech-to-text endpoint"""
    print("\n=== Testing Speech-to-Text API ===")
    
    # Endpoint URL
    url = f"{BASE_URL}/api/speech-to-text"
    
    # Check if file exists
    if not os.path.exists(audio_file_path):
        print(f"Error: Audio file not found at {audio_file_path}")
        return
    
    # Prepare file for upload
    files = {
        'file': (os.path.basename(audio_file_path), open(audio_file_path, 'rb'), 'audio/wav')
    }
    
    # Send POST request
    print(f"Sending request to {url} with file {audio_file_path}...")
    start_time = time.time()
    response = requests.post(url, files=files)
    
    # Check response
    if response.status_code == 200:
        data = response.json()
        print(f"Success! Processing time: {data.get('processing_time_seconds', 'N/A')} seconds")
        print(f"Transcript: {data['transcript']}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    # Test text-to-speech
    audio_file_path = test_text_to_speech()
    
    # If text-to-speech was successful, test speech-to-text with the generated audio
    if audio_file_path:
        # Wait a moment to ensure file is fully written
        time.sleep(1)
        test_speech_to_text(audio_file_path) 