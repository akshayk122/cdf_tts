#!/bin/bash
set -e

# Configuration - REPLACE THESE VALUES
PROJECT_ID="your-project-id"  # Replace with your Google Cloud project ID
SERVICE_NAME="tts-stt-api"
REGION="us-central1"  # Replace with your preferred region

# Build the Docker image
echo "Building Docker image..."
docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME .

# Push the image to Google Container Registry
echo "Pushing image to Google Container Registry..."
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300s

echo "Deployment completed!"
echo "Your service is now available at:"
gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)' 