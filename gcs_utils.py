import os
import datetime
import mimetypes
import json
from typing import Optional
import math
import time
import glob

try:
    from google.cloud import storage  # type: ignore
    from google.oauth2 import service_account  # type: ignore
except Exception:  # pragma: no cover
    storage = None  # Library might not be installed in local/dev
    service_account = None


GCS_DEBUG = os.environ.get("GCS_DEBUG", "false").lower() == "true"


def _debug(msg: str):
    if GCS_DEBUG:
        print(f"[GCS_DEBUG] {msg}")


def _resolve_bucket_name(bucket_name: Optional[str] = None) -> Optional[str]:
    """Resolve bucket name with priority: arg -> GCS_BUCKET_NAME -> GCS_BUCKET -> None."""
    if bucket_name:
        return bucket_name
    env_name = os.environ.get("GCS_BUCKET_NAME") or os.environ.get("GCS_BUCKET")
    return env_name


def is_gcs_enabled(bucket_name: Optional[str] = None) -> bool:
    """Return True if GCS is configured and library is available.

    Bucket resolution order: arg -> GCS_BUCKET_NAME -> GCS_BUCKET.
    """
    resolved = _resolve_bucket_name(bucket_name)
    enabled = bool(resolved) and storage is not None
    _debug(
        f"is_gcs_enabled={enabled}, bucket={resolved}, storage_lib_present={storage is not None}"
    )
    return enabled


def _build_storage_client(project: Optional[str] = None):
    """Return a storage.Client using either a credentials file path or inline JSON.

    Resolution order:
    1) If GOOGLE_APPLICATION_CREDENTIALS points to an existing file, use it (ADC default)
    2) If GOOGLE_APPLICATION_CREDENTIALS contains inline JSON, parse it
    3) If GOOGLE_APPLICATION_CREDENTIALS_JSON (or compatible aliases) is set, parse it
    4) Fallback to default ADC (metadata/server-provided creds if available)
    """
    if storage is None:
        raise RuntimeError("google-cloud-storage is not installed")

    credentials = None

    gac = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if gac:
        # Case 1: Path to existing file
        if os.path.exists(gac):
            _debug(f"Using GOOGLE_APPLICATION_CREDENTIALS file at: {gac}")
            return storage.Client(project=project)
        # Case 2: Inline JSON content
        if gac.strip().startswith("{") and service_account is not None:
            try:
                info = json.loads(gac)
                credentials = service_account.Credentials.from_service_account_info(info)
                _debug("Using inline JSON from GOOGLE_APPLICATION_CREDENTIALS env var")
                return storage.Client(project=project, credentials=credentials)
            except Exception as e:
                _debug(f"Failed to parse inline GOOGLE_APPLICATION_CREDENTIALS JSON: {e}")

    # Case 3: Dedicated JSON env vars supported by some setups
    for env_name in ("GOOGLE_APPLICATION_CREDENTIALS_JSON", "GCP_SERVICE_ACCOUNT_JSON", "GOOGLE_CREDENTIALS_JSON"):
        raw = os.environ.get(env_name)
        if raw and service_account is not None:
            try:
                info = json.loads(raw)
                credentials = service_account.Credentials.from_service_account_info(info)
                _debug(f"Using inline JSON from {env_name}")
                return storage.Client(project=project, credentials=credentials)
            except Exception as e:
                _debug(f"Failed to parse inline JSON from {env_name}: {e}")
                continue

    _debug("Using default ADC (no explicit credentials provided)")
    return storage.Client(project=project)


def get_bucket(bucket_name: Optional[str] = None):
    """Return a Google Cloud Storage Bucket client using env config or provided name.

    Resolution: bucket_name arg -> GCS_BUCKET_NAME -> GCS_BUCKET.
    Optional env: GCP_PROJECT.
    """
    if storage is None:
        raise RuntimeError("google-cloud-storage is not installed")

    resolved_bucket = _resolve_bucket_name(bucket_name)
    if not resolved_bucket:
        raise RuntimeError("GCS is not enabled (no bucket configured)")

    project = os.environ.get("GCP_PROJECT")
    client = _build_storage_client(project=project)
    _debug(f"Created storage client for project={project}, bucket={resolved_bucket}")
    return client.bucket(resolved_bucket)


def _normalize_blob_path(path: str) -> str:
    # Ensure POSIX-style paths for blob names
    return path.replace("\\", "/").lstrip("./")


def guess_content_type(path: str) -> str:
    lower = path.lower()
    if lower.endswith(".json"):
        return "application/json"
    if lower.endswith(".csv"):
        return "text/csv"
    ctype, _ = mimetypes.guess_type(path)
    return ctype or "application/octet-stream"


def upload_file(
    local_path: str,
    blob_path: Optional[str] = None,
    *,
    content_type: Optional[str] = None,
    cache_control: str = "no-cache, max-age=0",
    bucket_name: Optional[str] = None,
) -> bool:
    """Upload a local file to GCS. Returns True if uploaded, False if skipped."""
    if not is_gcs_enabled(bucket_name=bucket_name):
        _debug("Upload skipped: GCS not enabled")
        return False
    if not os.path.exists(local_path):
        _debug(f"Upload skipped: local file does not exist: {local_path}")
        return False

    blob_name = _normalize_blob_path(blob_path or local_path)
    bucket = get_bucket(bucket_name=bucket_name)
    blob = bucket.blob(blob_name)

    if content_type is None:
        content_type = guess_content_type(local_path)

    blob.cache_control = cache_control
    _debug(
        f"Uploading {local_path} -> gs://{bucket.name}/{blob_name} (content_type={content_type}, cache_control={cache_control})"
    )
    blob.upload_from_filename(local_path, content_type=content_type)
    _debug("Upload complete")
    return True


def upload_if_exists(
    local_path: str,
    blob_path: Optional[str] = None,
    *,
    content_type: Optional[str] = None,
    bucket_name: Optional[str] = None,
) -> bool:
    if not os.path.exists(local_path):
        _debug(f"upload_if_exists: local file missing: {local_path}")
        return False
    return upload_file(local_path, blob_path, content_type=content_type, bucket_name=bucket_name)


def download_file(blob_path: str, local_path: Optional[str] = None, *, bucket_name: Optional[str] = None) -> bool:
    """Download a blob to local path. Returns True if downloaded, False if not found."""
    if not is_gcs_enabled(bucket_name=bucket_name):
        _debug("Download skipped: GCS not enabled")
        return False

    blob_name = _normalize_blob_path(blob_path)
    bucket = get_bucket(bucket_name=bucket_name)
    blob = bucket.blob(blob_name)

    if not blob.exists():
        _debug(f"Blob does not exist: gs://{bucket.name}/{blob_name}")
        return False

    local_target = local_path or blob_name
    os.makedirs(os.path.dirname(local_target), exist_ok=True)
    _debug(f"Downloading gs://{bucket.name}/{blob_name} -> {local_target}")
    blob.download_to_filename(local_target)
    _debug("Download complete")
    return True


def download_if_exists(blob_path: str, local_path: Optional[str] = None, *, bucket_name: Optional[str] = None) -> bool:
    try:
        return download_file(blob_path, local_path, bucket_name=bucket_name)
    except Exception as e:
        _debug(f"download_if_exists error: {e}")
        return False


def blob_exists(blob_path: str, *, bucket_name: Optional[str] = None) -> bool:
    if not is_gcs_enabled(bucket_name=bucket_name):
        _debug("blob_exists: GCS not enabled")
        return False
    bucket = get_bucket(bucket_name=bucket_name)
    exists = bucket.blob(_normalize_blob_path(blob_path)).exists()
    _debug(f"blob_exists gs://{bucket.name}/{_normalize_blob_path(blob_path)} -> {exists}")
    return exists


def make_blob_public(blob_path: str, *, bucket_name: Optional[str] = None) -> bool:
    if not is_gcs_enabled(bucket_name=bucket_name):
        _debug("make_blob_public: GCS not enabled")
        return False
    bucket = get_bucket(bucket_name=bucket_name)
    blob = bucket.blob(_normalize_blob_path(blob_path))
    if not blob.exists():
        _debug(f"make_blob_public: blob missing gs://{bucket.name}/{_normalize_blob_path(blob_path)}")
        return False
    blob.make_public()
    _debug("make_blob_public: success")
    return True


def generate_signed_url(blob_path: str, expiration_seconds: int = 3600, *, bucket_name: Optional[str] = None) -> Optional[str]:
    if not is_gcs_enabled(bucket_name=bucket_name):
        _debug("generate_signed_url: GCS not enabled")
        return None
    bucket = get_bucket(bucket_name=bucket_name)
    blob = bucket.blob(_normalize_blob_path(blob_path))
    if not blob.exists():
        _debug("generate_signed_url: blob missing")
        return None
    url = blob.generate_signed_url(expiration=datetime.timedelta(seconds=expiration_seconds))
    _debug("generate_signed_url: success")
    return url


# New public helpers with explicit bucket support
def upload_to_gcs(local_path: str, gcs_path: str, bucket_name: str | None = None, content_type: str | None = None) -> bool:
    """Upload a file to GCS with proper headers. Returns True on success.

    - Resolves bucket as: arg -> GCS_BUCKET_NAME -> GCS_BUCKET
    - Sets Content-Type (forced for .json/.csv)
    - Sets Cache-Control to "no-cache, max-age=0"
    """
    if not os.path.exists(local_path):
        _debug(f"upload_to_gcs: local file does not exist: {local_path}")
        return False
    if content_type is None:
        content_type = guess_content_type(local_path)
    try:
        return upload_file(
            local_path,
            gcs_path,
            content_type=content_type,
            cache_control="no-cache, max-age=0",
            bucket_name=bucket_name,
        )
    except Exception as e:
        _debug(f"upload_to_gcs error: {e}")
        return False


def download_from_gcs(gcs_path: str, local_path: str, bucket_name: str | None = None) -> bool:
    """Download a blob from GCS to local path. Returns True if downloaded, False if missing."""
    try:
        return download_file(gcs_path, local_path, bucket_name=bucket_name)
    except Exception as e:
        _debug(f"download_from_gcs error: {e}")
        return False


def _sanitize_value(value):
    """Sanitize a single value for JSON serialization (no NaN/Inf)."""
    try:
        # Handle numpy types and Python floats
        if isinstance(value, float) or (hasattr(value, "__float__") and not isinstance(value, bool)):
            x = float(value)
            if not math.isfinite(x):
                return None
            return x
    except Exception:
        pass
    # Pass through common serializable types
    return value


def _sanitize_records(records):
    sanitized = []
    for rec in records:
        if isinstance(rec, dict):
            clean = {}
            for k, v in rec.items():
                if isinstance(v, dict):
                    clean[k] = _sanitize_records([v])[0]
                elif isinstance(v, list):
                    clean[k] = [_sanitize_value(item) if not isinstance(item, (dict, list)) else item for item in v]
                else:
                    clean[k] = _sanitize_value(v)
            sanitized.append(clean)
        else:
            sanitized.append(rec)
    return sanitized


def write_json_records(df, destination_path: str) -> None:
    """Strict JSON writer: replaces NaN/±Inf with None and writes with allow_nan=False.

    Accepts a pandas DataFrame or a list of dict records.
    """
    # Lazy import to avoid hard dependency in environments without pandas
    pandas = None
    try:
        import pandas as pd  # type: ignore
        pandas = pd
    except Exception:
        pandas = None

    if pandas is not None and hasattr(df, "to_dict"):
        try:
            # Convert DataFrame to records and sanitize
            records = df.to_dict(orient="records")
        except Exception:
            records = list(df)
    else:
        # Assume already a list of records
        records = list(df)

    sanitized = _sanitize_records(records)
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    with open(destination_path, "w") as f:
        json.dump(sanitized, f, indent=2, allow_nan=False)


def upload_csv_to_gcs(csv_file_path: str, bucket_name: str | None = None) -> bool:
    """Upload a CSV to GCS under csv/<asset>/<filename> or csv/<filename> with correct headers.

    If the parent directory appears to be a generic 'data' directory (no asset),
    the file is placed under csv/<filename>.
    """
    if not os.path.exists(csv_file_path):
        _debug(f"upload_csv_to_gcs: missing file {csv_file_path}")
        return False
    parent = os.path.basename(os.path.dirname(csv_file_path))
    filename = os.path.basename(csv_file_path)
    if parent.lower() in ("data", ""):
        gcs_path = _normalize_blob_path(os.path.join("csv", filename))
    else:
        gcs_path = _normalize_blob_path(os.path.join("csv", parent, filename))
    return upload_to_gcs(csv_file_path, gcs_path, bucket_name=bucket_name, content_type="text/csv")


def upload_recent_csvs(hours_back: int = 24, bucket_name: str | None = None) -> dict:
    """Upload CSV files modified within the last N hours across assets.

    Returns a mapping of local file path -> boolean success.
    """
    results = {}
    now = time.time()
    cutoff = now - (hours_back * 3600)
    # Search typical data directories: render_app/data/<asset>/*.csv
    patterns = [
        os.path.join("render_app", "data", "*", "*.csv"),
        os.path.join("render_app", "data", "*.csv"),  # fallback if flat
    ]
    seen = set()
    for pattern in patterns:
        for path in glob.glob(pattern):
            if path in seen:
                continue
            seen.add(path)
            try:
                mtime = os.path.getmtime(path)
            except Exception:
                continue
            if mtime >= cutoff:
                ok = upload_csv_to_gcs(path, bucket_name=bucket_name)
                results[path] = ok
    return results