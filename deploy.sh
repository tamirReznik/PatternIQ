#!/bin/bash
# deploy.sh - Deploy PatternIQ to Google Cloud Platform

# Configuration
PROJECT_ID="your-gcp-project-id"
SERVICE_NAME="patterniq-batch"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/patterniq:latest"

echo "🚀 Deploying PatternIQ to Google Cloud Platform"
echo "================================================"

# Step 1: Build and push Docker image
echo "📦 Building Docker image..."
docker build -t ${IMAGE_NAME} .

echo "📤 Pushing image to Google Container Registry..."
docker push ${IMAGE_NAME}

# Step 2: Deploy to Cloud Run
echo "☁️ Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --memory 4Gi \
    --cpu 2 \
    --timeout 1800 \
    --max-instances 1 \
    --no-allow-unauthenticated \
    --set-env-vars PATTERNIQ_ALWAYS_ON=false,DB_MODE=auto,GENERATE_REPORTS=true

# Step 3: Create Cloud Scheduler job
echo "⏰ Setting up daily scheduler..."
gcloud scheduler jobs create http patterniq-daily-batch \
    --schedule="0 18 * * *" \
    --time-zone="America/New_York" \
    --uri="https://${SERVICE_NAME}-${REGION}.run.app" \
    --http-method=POST \
    --oidc-service-account-email="${SERVICE_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "✅ Deployment completed!"
echo "📊 Your PatternIQ will run daily at 6:00 PM EST"
echo "🌐 Monitor at: https://console.cloud.google.com/run"
