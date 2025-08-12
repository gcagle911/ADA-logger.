import os
import datetime
import mimetypes
import json
from typing import Optional

try:
    from google.cloud import storage  # type: ignore
    from google.oauth2 import service_account  # type: ignore
except Exception:  # pragma: no cover
    storage = None  # Library might not be installed in local/dev
    service_account = None


def is_gcs_enabled() -> bool:
    """Return True if GCS is configured via env var `GCS_BUCKET`."""
    return bool(os.environ.get("GCS_BUCKET")) and storage is not None


def _build_storage_client(project: Optional[str] = None):
    """Return a storage.Client using either a credentials file path or inline JSON.

    Resolution order:
    1) If GOOGLE_APPLICATION_CREDENTIALS points to an existing file, use it (ADC default)
    2) If GOOGLE_APPLICATION_CREDENTIALS contains inline JSON, parse it
    3) If GOOGLE_APPLICATION_CREDENTIALS_JSON (or compatible aliases) is set, parse it
    4) Fallback to default ADC (metadata/server-provided creds if available)
    """
    # If google auth libs are not available, let caller handle
    if storage is None:
        raise RuntimeError("google-cloud-storage is not installed")

    credentials = None

    gac = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if gac:
        # Case 1: Path to existing file
        if os.path.exists(gac):
            return storage.Client(project=project)
        # Case 2: Inline JSON content
        if gac.strip().startswith("{") and service_account is not None:
            try:
                info = json.loads(gac)
                credentials = service_account.Credentials.from_service_account_info(info)
                return storage.Client(project=project, credentials=credentials)
            except Exception:
                pass

    # Case 3: Dedicated JSON env vars supported by some setups
    for env_name in ("GOOGLE_APPLICATION_CREDENTIALS_JSON", "GCP_SERVICE_ACCOUNT_JSON", "GOOGLE_CREDENTIALS_JSON"):
        raw = os.environ.get(env_name)
        if raw and service_account is not None:
            try:
                info = json.loads(raw)
                credentials = service_account.Credentials.from_service_account_info(info)
                return storage.Client(project=project, credentials=credentials)
            except Exception:
                continue

    # Case 4: Default ADC
    return storage.Client(project=project)


def get_bucket():
    """Return a Google Cloud Storage Bucket client using env config.
    Requires env: GCS_BUCKET; optional: GCP_PROJECT.
    Supports credentials via file path or inline JSON (see _build_storage_client).
    """
    if not is_gcs_enabled():
        raise RuntimeError("GCS is not enabled or google-cloud-storage is not installed")

    bucket_name = os.environ["GCS_BUCKET"]
    project = os.environ.get("GCP_PROJECT")
    client = _build_storage_client(project=project)
    return client.bucket(bucket_name)


def _normalize_blob_path(path: str) -> str:
    # Ensure POSIX-style paths for blob names
    return path.replace("\\", "/").lstrip("./")


def guess_content_type(path: str) -> str:
    ctype, _ = mimetypes.guess_type(path)
    return ctype or "application/octet-stream"


def upload_file(local_path: str, blob_path: Optional[str] = None, *, content_type: Optional[str] = None, cache_control: Optional[str] = "no-cache") -> bool:
    """Upload a local file to GCS. Returns True if uploaded, False if skipped."""
    if not is_gcs_enabled():
        return False
    if not os.path.exists(local_path):
        return False

    blob_name = _normalize_blob_path(blob_path or local_path)
    bucket = get_bucket()
    blob = bucket.blob(blob_name)

    if content_type is None:
        content_type = guess_content_type(local_path)

    blob.cache_control = cache_control
    blob.upload_from_filename(local_path, content_type=content_type)
    return True


def upload_if_exists(local_path: str, blob_path: Optional[str] = None, *, content_type: Optional[str] = None) -> bool:
    if not os.path.exists(local_path):
        return False
    return upload_file(local_path, blob_path, content_type=content_type)


def download_file(blob_path: str, local_path: Optional[str] = None) -> bool:
    """Download a blob to local path. Returns True if downloaded, False if not found."""
    if not is_gcs_enabled():
        return False

    blob_name = _normalize_blob_path(blob_path)
    bucket = get_bucket()
    blob = bucket.blob(blob_name)

    if not blob.exists():
        return False

    local_target = local_path or blob_name
    os.makedirs(os.path.dirname(local_target), exist_ok=True)
    blob.download_to_filename(local_target)
    return True


def download_if_exists(blob_path: str, local_path: Optional[str] = None) -> bool:
    try:
        return download_file(blob_path, local_path)
    except Exception:
        return False


def blob_exists(blob_path: str) -> bool:
    if not is_gcs_enabled():
        return False
    bucket = get_bucket()
    return bucket.blob(_normalize_blob_path(blob_path)).exists()


def make_blob_public(blob_path: str) -> bool:
    if not is_gcs_enabled():
        return False
    bucket = get_bucket()
    blob = bucket.blob(_normalize_blob_path(blob_path))
    if not blob.exists():
        return False
    blob.make_public()
    return True


def generate_signed_url(blob_path: str, expiration_seconds: int = 3600) -> Optional[str]:
    if not is_gcs_enabled():
        return None
    bucket = get_bucket()
    blob = bucket.blob(_normalize_blob_path(blob_path))
    if not blob.exists():
        return None
    return blob.generate_signed_url(expiration=datetime.timedelta(seconds=expiration_seconds))