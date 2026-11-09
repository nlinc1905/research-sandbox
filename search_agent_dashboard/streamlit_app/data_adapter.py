"""Lightweight adapter layer for dashboard data sources.

UI code consumes one stable shape from ``load_dashboard_data`` and does not care
whether records come from local JSON, S3, MLflow artifacts, or an API.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib import request

DATASET_NAMES = (
    "overview",
    "profiles",
    "customers",
    "batches",
    "documents",
    "sessions",
    "traces",
)


@dataclass(frozen=True)
class DashboardData:
    """Immutable data contract containing all dashboard datasets.
    
    All dashboard rendering functions accept one DashboardData instance.
    Adapters load data from various sources (JSON, API, S3, MLflow) and return
    a normalized DashboardData shape so UI code never knows the source.
    
    Frozen dataclass prevents accidental mutations and works with @st.cache_data.
    """
    overview: dict[str, Any]
    profiles: list[dict[str, Any]]
    customers: list[dict[str, Any]]
    batches: list[dict[str, Any]]
    documents: list[dict[str, Any]]
    sessions: list[dict[str, Any]]
    traces: list[dict[str, Any]]


class DashboardDataAdapter(Protocol):
    """Protocol for pluggable data source adapters.
    
    Any class implementing the load() method can be used as a data source.
    Adapters must return a normalized DashboardData shape regardless of underlying
    storage (local files, HTTP, S3, MLflow, etc).
    """
    def load(self) -> DashboardData:
        """Return all dashboard datasets in one stable shape.
        
        :return: DashboardData with all required datasets populated.
        :raises: Exception (depends on adapter) if data cannot be loaded.
        """
        ...


@dataclass(frozen=True)
class JsonFileAdapter:
    """Load dashboard datasets from local JSON files.
    
    Reads data_dir/overview.json, data_dir/profiles.json, etc. Each file must
    contain a complete dataset (e.g. profiles.json contains the profiles list).
    
    Decision: Frozen dataclass for immutability and @st.cache_data compatibility.
    """
    data_dir: Path

    def load(self) -> DashboardData:
        """Load all JSON files from data_dir into DashboardData.
        
        :return: DashboardData with datasets read from local files.
        :raises FileNotFoundError: If any expected JSON file is missing.
        :raises json.JSONDecodeError: If any JSON file is malformed.
        """
        return DashboardData(
            overview=self._load_json("overview"),
            profiles=self._load_json("profiles"),
            customers=self._load_json("customers"),
            batches=self._load_json("batches"),
            documents=self._load_json("documents"),
            sessions=self._load_json("sessions"),
            traces=self._load_json("traces"),
        )

    def _load_json(self, name: str) -> Any:
        """Load a single JSON file by name.
        
        :param name: Dataset name (e.g. "profiles" → data_dir/profiles.json).
        :return: Parsed JSON content (dict or list depending on dataset).
        :raises FileNotFoundError: If {name}.json does not exist in data_dir.
        :raises json.JSONDecodeError: If file is not valid JSON.
        """
        with (self.data_dir / f"{name}.json").open("r", encoding="utf-8") as handle:
            return json.load(handle)


@dataclass(frozen=True)
class ApiAdapter:
    """Load dashboard datasets from an HTTP API endpoint.
    
    Fetches {base_url}/overview.json, {base_url}/profiles.json, etc via GET requests.
    Supports optional bearer token authentication and configurable timeout.
    
    Decision: Uses urllib directly to avoid extra dependencies. Token is passed
    as Authorization: Bearer header.
    """
    base_url: str
    token: str | None = None
    timeout_seconds: float = 10

    def load(self) -> DashboardData:
        """Load all datasets from API endpoints.
        
        :return: DashboardData with datasets fetched from API.
        :raises urllib.error.URLError: If any GET request fails (network error, not found).
        :raises json.JSONDecodeError: If response is not valid JSON.
        :raises urllib.error.HTTPError: If any request returns HTTP error (401, 403, 500, etc).
        """
        return DashboardData(
            overview=self._get_json("overview"),
            profiles=self._get_json("profiles"),
            customers=self._get_json("customers"),
            batches=self._get_json("batches"),
            documents=self._get_json("documents"),
            sessions=self._get_json("sessions"),
            traces=self._get_json("traces"),
        )

    def _get_json(self, name: str) -> Any:
        """Fetch a single JSON dataset from API.
        
        :param name: Dataset name (e.g. "profiles" → {base_url}/profiles.json).
        :return: Parsed JSON content.
        :raises urllib.error.URLError: If request fails.
        :raises json.JSONDecodeError: If response is not valid JSON.
        """
        url = f"{self.base_url.rstrip('/')}/{name}.json"
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = request.Request(url=url, headers=headers)
        with request.urlopen(req, timeout=self.timeout_seconds) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))


@dataclass(frozen=True)
class S3Adapter:
    """Load dashboard datasets from S3 objects.
    
    Reads s3://{bucket}/{prefix}/overview.json, etc via boto3 client.
    Requires boto3 to be installed; raises RuntimeError if not available.
    
    Supports optional region_name and prefix (path within bucket).
    """
    bucket: str
    prefix: str = ""
    region_name: str | None = None

    def load(self) -> DashboardData:
        """Load all datasets from S3 bucket.
        
        :return: DashboardData with datasets fetched from S3.
        :raises RuntimeError: If boto3 is not installed.
        :raises botocore.exceptions.ClientError: If S3 operations fail (auth, missing bucket, etc).
        :raises json.JSONDecodeError: If object content is not valid JSON.
        """
        try:
            import boto3  # type: ignore[import-not-found]
        except Exception as exc:  # pragma: no cover - only hit without boto3
            raise RuntimeError("S3 adapter requires boto3. Install it or use source=json/api.") from exc

        client = boto3.client("s3", region_name=self.region_name)

        def get_json(name: str) -> Any:
            """Fetch a single JSON object from S3.
            
            :param name: Dataset name (e.g. "profiles" → {prefix}/profiles.json).
            :return: Parsed JSON content.
            """
            key = f"{self.prefix.rstrip('/')}/{name}.json".lstrip("/")
            payload = client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
            return json.loads(payload.decode("utf-8"))

        return DashboardData(
            overview=get_json("overview"),
            profiles=get_json("profiles"),
            customers=get_json("customers"),
            batches=get_json("batches"),
            documents=get_json("documents"),
            sessions=get_json("sessions"),
            traces=get_json("traces"),
        )


@dataclass(frozen=True)
class MlflowArtifactAdapter:
    """Load dashboard datasets from MLflow artifacts.

    Expected artifact layout under ``artifact_path``:
    - overview.json
    - profiles.json
    - customers.json
    - batches.json
    - documents.json
    - sessions.json
    - traces.json
    
    Decision: Downloads artifacts to a temporary local directory, then delegates to
    JsonFileAdapter for actual loading. This avoids duplicating JSON load logic.
    Requires mlflow to be installed; raises RuntimeError if not available.
    """

    artifact_path: str
    tracking_uri: str | None = None

    def load(self) -> DashboardData:
        """Download MLflow artifacts and load datasets from them.
        
        :return: DashboardData with datasets from downloaded artifacts.
        :raises RuntimeError: If mlflow is not installed.
        :raises mlflow.exceptions.MlflowException: If artifact download fails.
        :raises FileNotFoundError: If expected JSON files not in artifact directory.
        :raises json.JSONDecodeError: If JSON files are malformed.
        """
        try:
            import mlflow  # type: ignore[import-not-found]
            from mlflow import artifacts  # type: ignore[import-not-found]
        except Exception as exc:  # pragma: no cover - only hit without mlflow
            raise RuntimeError("MLflow adapter requires mlflow. Install it or use source=json/api.") from exc

        if self.tracking_uri:
            mlflow.set_tracking_uri(self.tracking_uri)

        local_dir = artifacts.download_artifacts(artifact_path=self.artifact_path)
        return JsonFileAdapter(Path(local_dir)).load()


def create_adapter(config: dict[str, str], default_json_dir: Path) -> DashboardDataAdapter:
    """Factory function to create an adapter based on source configuration.
    
    Routes to the appropriate adapter class (JSON, API, S3, MLflow) based on
    config["source"]. Each source has required and optional config keys that are
    validated before returning the adapter instance.
    
    Decision: Validation raises ValueError early with clear messages so errors
    are caught during startup, not later during load().
    
    :param config: Config dict with keys like "source", "api_base_url", "s3_bucket", etc.
                  Typically from resolve_adapter_config() or environment-derived dict.
    :param default_json_dir: Fallback data directory for json source if json_dir not in config.
    :return: Instantiated adapter (JsonFileAdapter, ApiAdapter, S3Adapter, or MlflowArtifactAdapter).
    :raises ValueError: If source is not recognized, or if required config for that source is missing.
    """
    source = config.get("source", "json").strip().lower()
    if source == "json":
        data_dir = Path(config.get("json_dir", str(default_json_dir))).expanduser().resolve()
        return JsonFileAdapter(data_dir)
    if source == "api":
        base_url = config.get("api_base_url", "").strip()
        if not base_url:
            raise ValueError("api source requires api_base_url")
        token = config.get("api_token") or None
        timeout = float(config.get("api_timeout_seconds", "10"))
        return ApiAdapter(base_url=base_url, token=token, timeout_seconds=timeout)
    if source == "s3":
        bucket = config.get("s3_bucket", "").strip()
        if not bucket:
            raise ValueError("s3 source requires s3_bucket")
        return S3Adapter(
            bucket=bucket,
            prefix=config.get("s3_prefix", ""),
            region_name=config.get("s3_region") or None,
        )
    if source == "mlflow":
        artifact_path = config.get("mlflow_artifact_path", "").strip()
        if not artifact_path:
            raise ValueError("mlflow source requires mlflow_artifact_path")
        return MlflowArtifactAdapter(
            artifact_path=artifact_path,
            tracking_uri=config.get("mlflow_tracking_uri") or None,
        )
    raise ValueError(f"Unsupported data source: {source}")


def resolve_adapter_config() -> dict[str, str]:
    """Resolve data source configuration from environment variables.
    
    Reads MyAgent_* environment variables and returns a filtered dict (empty
    values removed) suitable for create_adapter(). If an env var is not set,
    it is omitted from the result (not included with empty string).
    
    Recognized env vars:
    - MyAgent_DATA_SOURCE: json|api|s3|mlflow (default: json)
    - MyAgent_JSON_DIR: path to local data directory
    - MyAgent_API_BASE_URL: HTTP(S) API base URL (required for api source)
    - MyAgent_API_TOKEN: optional bearer token for API auth
    - MyAgent_API_TIMEOUT_SECONDS: request timeout (default: 10)
    - MyAgent_S3_BUCKET: S3 bucket name (required for s3 source)
    - MyAgent_S3_PREFIX: optional path prefix within bucket
    - MyAgent_S3_REGION: optional AWS region (default: auto)
    - MyAgent_MLFLOW_ARTIFACT_PATH: MLflow artifact path (required for mlflow source)
    - MyAgent_MLFLOW_TRACKING_URI: optional MLflow tracking server URI
    
    Decision: Empty values are filtered out so create_adapter() can distinguish
    "not set" from "set to empty string". This avoids unintended defaults.
    
    :return: Dict with source and source-specific config (e.g. {"source": "json", "json_dir": "/data"}).
    """
    config = {
        "source": os.getenv("MyAgent_DATA_SOURCE", "json"),
        "json_dir": os.getenv("MyAgent_JSON_DIR", ""),
        "api_base_url": os.getenv("MyAgent_API_BASE_URL", ""),
        "api_token": os.getenv("MyAgent_API_TOKEN", ""),
        "api_timeout_seconds": os.getenv("MyAgent_API_TIMEOUT_SECONDS", "10"),
        "s3_bucket": os.getenv("MyAgent_S3_BUCKET", ""),
        "s3_prefix": os.getenv("MyAgent_S3_PREFIX", ""),
        "s3_region": os.getenv("MyAgent_S3_REGION", ""),
        "mlflow_artifact_path": os.getenv("MyAgent_MLFLOW_ARTIFACT_PATH", ""),
        "mlflow_tracking_uri": os.getenv("MyAgent_MLFLOW_TRACKING_URI", ""),
    }
    return {k: v for k, v in config.items() if v}
