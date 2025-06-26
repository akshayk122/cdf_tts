# Text-to-Speech and Speech-to-Text API

A FastAPI application that provides endpoints for text-to-speech and speech-to-text conversion using Google Cloud services.

## Features

- **Text-to-Speech Endpoint**: Convert text input to audio output
- **Speech-to-Text Endpoint**: Convert audio input to text output
- **Fast and Efficient**: Optimized for quick response times
- **RESTful API**: Simple JSON interface for easy integration with frontend applications

## Requirements

- Python 3.8+
- Google Cloud account with Text-to-Speech and Speech-to-Text APIs enabled
- Google Cloud credentials configured

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up Google Cloud credentials:
   ```
   export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/credentials.json"
   ```

## Usage

1. Start the server:
   ```
   uvicorn app:app --reload
   ```

2. The API will be available at http://localhost:8000

3. API Documentation is available at http://localhost:8000/docs

## API Endpoints

### Text-to-Speech

**Endpoint**: `/api/text-to-speech`

**Method**: POST

**Request Body**:
```json
{
  "text": "Text to convert to speech"
}
```

**Response**:
```json
{
  "audio_path": "/static/output_1234567890.wav",
  "text": "Text to convert to speech"
}
```

### Speech-to-Text

**Endpoint**: `/api/speech-to-text`

**Method**: POST

**Request**: Form data with audio file

**Response**:
```json
{
  "transcript": "Transcribed text from the audio file",
  "processing_time_seconds": 1.23
}
```

## Integration with React

This API is designed to be easily integrated with a React frontend application. The frontend can:

1. Send text to the text-to-speech endpoint and receive audio to play
2. Send recorded audio to the speech-to-text endpoint and receive transcribed text

## License

MIT 