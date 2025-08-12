### Deploying to Google Cloud (Cloud Run + Cloud Storage)

This repo can run on Google Cloud Run and optionally sync generated data (JSON/CSV) to Google Cloud Storage for durability.

#### What this adds
- `gcs_utils.py`: Minimal helper around Google Cloud Storage
- GCS sync in `process_data.py` (uploads generated JSON and daily files)
- Periodic CSV upload in multi-asset logger (every 60s)
- Startup hydration from GCS in `multi_asset_server.py` when available
- Dockerfile for Cloud Run
- `scripts/deploy_cloud_run.sh` to build and deploy

#### Prerequisites
- gcloud CLI installed and authenticated
- Billing enabled on your GCP project

#### One-command deploy
```bash
export PROJECT_ID=your-gcp-project
# Optional overrides
export SERVICE_NAME=crypto-logger
export REGION=us-central1
export BUCKET_NAME=${PROJECT_ID}-crypto-data

bash scripts/deploy_cloud_run.sh
```

The script will:
- Enable required APIs
- Create a GCS bucket if missing
- Build and deploy the service to Cloud Run
- Set env vars: `GCP_PROJECT`, `GCS_BUCKET`, `GCS_SYNC_ON_START=true`

#### Service URL and endpoints
After deploy the script prints the service URL. Examples:
- Root status: `{SERVICE_URL}/` (multi-asset overview)
- Default crypto JSON: `{SERVICE_URL}/recent.json` and `{SERVICE_URL}/historical.json`
- Per-crypto JSON: `{SERVICE_URL}/{SYMBOL}/recent.json` (e.g., ADA, BTC, ETH)

#### How Cloud Storage is used
- When JSON files are generated (`recent.json`, `historical.json`, daily files), they are uploaded to `gs://$GCS_BUCKET/render_app/data/...`.
- Every 60 seconds, the active CSV file is also uploaded for durability.
- On startup, if `GCS_SYNC_ON_START=true`, the service attempts to download existing `recent.json` and `historical.json` for each crypto to warm the cache.

No special credentials are needed when deploying to Cloud Run in the same project; the default service account is used. If deploying cross-project, configure a service account with `Storage Object Admin` on the bucket.

#### Local development (optional)
- You can run locally with GCS disabled; files are written under `render_app/data`.
- To test GCS locally, set env vars and authenticate:
```bash
export GCP_PROJECT=your-gcp-project
export GCS_BUCKET=your-bucket
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
python multi_asset_server.py
```