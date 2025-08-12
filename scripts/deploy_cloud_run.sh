#!/usr/bin/env bash
set -euo pipefail

# Required:
#   PROJECT_ID - GCP project id
# Optional:
#   SERVICE_NAME - Cloud Run service name (default: crypto-logger)
#   REGION - Cloud Run region (default: us-central1)
#   BUCKET_NAME - GCS bucket name for data (default: ${PROJECT_ID}-crypto-data)

if [[ -z "${PROJECT_ID:-}" ]]; then
  echo "PROJECT_ID is required" >&2
  exit 1
fi

SERVICE_NAME=${SERVICE_NAME:-crypto-logger}
REGION=${REGION:-us-central1}
BUCKET_NAME=${BUCKET_NAME:-${PROJECT_ID}-crypto-data}

set -x

# Enable required services
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com storage.googleapis.com --project "$PROJECT_ID"

# Create bucket if not exists
if ! gsutil ls -p "$PROJECT_ID" "gs://$BUCKET_NAME" >/dev/null 2>&1; then
  gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://$BUCKET_NAME"
fi

IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Build and push image
gcloud builds submit --project "$PROJECT_ID" --tag "$IMAGE"

# Deploy to Cloud Run
gcloud run deploy "$SERVICE_NAME" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --image "$IMAGE" \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT="$PROJECT_ID",GCS_BUCKET="$BUCKET_NAME",GCS_SYNC_ON_START=true

# Output service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --project "$PROJECT_ID" --region "$REGION" --format 'value(status.url)')
set +x

echo ""
echo "Deployed to: $SERVICE_URL"
echo ""
echo "Environment configured: GCP_PROJECT=$PROJECT_ID, GCS_BUCKET=$BUCKET_NAME"
echo "Use the service URL + endpoints, e.g. $SERVICE_URL/recent.json or $SERVICE_URL/ADA/recent.json"