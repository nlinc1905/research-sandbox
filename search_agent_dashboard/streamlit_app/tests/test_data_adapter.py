import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import data_adapter


class AdapterTests(unittest.TestCase):
    def test_json_adapter_loads_all_datasets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = {
                "overview": {"banner": "x", "subtitle": "y"},
                "profiles": [{"id": "A"}],
                "customers": [{"id": "cust_a", "profile": "A"}],
                "batches": [{"id": "B-1", "customer_id": "cust_a"}],
                "documents": [{"id": "D-1", "batch_id": "B-1"}],
                "sessions": [{"id": "s-1"}],
                "traces": [{"id": "t-1"}],
            }
            for name, value in payload.items():
                (root / f"{name}.json").write_text(json.dumps(value), encoding="utf-8")

            loaded = data_adapter.JsonFileAdapter(root).load()
            self.assertEqual(loaded.overview["banner"], "x")
            self.assertEqual(loaded.profiles[0]["id"], "A")
            self.assertEqual(loaded.traces[0]["id"], "t-1")

    def test_create_adapter_routes_by_source(self):
        default = Path("/tmp/does-not-matter")
        adapter = data_adapter.create_adapter({"source": "json", "json_dir": "/tmp/demo"}, default)
        self.assertIsInstance(adapter, data_adapter.JsonFileAdapter)

        adapter = data_adapter.create_adapter({"source": "api", "api_base_url": "https://example.test"}, default)
        self.assertIsInstance(adapter, data_adapter.ApiAdapter)

        adapter = data_adapter.create_adapter({"source": "s3", "s3_bucket": "bucket"}, default)
        self.assertIsInstance(adapter, data_adapter.S3Adapter)

        adapter = data_adapter.create_adapter({"source": "mlflow", "mlflow_artifact_path": "runs:/x/artifacts/data"}, default)
        self.assertIsInstance(adapter, data_adapter.MlflowArtifactAdapter)

    def test_create_adapter_validates_required_config(self):
        default = Path("/tmp/does-not-matter")
        with self.assertRaises(ValueError):
            data_adapter.create_adapter({"source": "api"}, default)
        with self.assertRaises(ValueError):
            data_adapter.create_adapter({"source": "s3"}, default)
        with self.assertRaises(ValueError):
            data_adapter.create_adapter({"source": "mlflow"}, default)
        with self.assertRaises(ValueError):
            data_adapter.create_adapter({"source": "unknown"}, default)

    def test_resolve_adapter_config_reads_env(self):
        with patch.dict(
            "os.environ",
            {
                "MyAgent_DATA_SOURCE": "api",
                "MyAgent_API_BASE_URL": "https://example.test",
                "MyAgent_API_TOKEN": "token",
                "MyAgent_API_TIMEOUT_SECONDS": "4",
            },
            clear=True,
        ):
            cfg = data_adapter.resolve_adapter_config()
            self.assertEqual(cfg["source"], "api")
            self.assertEqual(cfg["api_base_url"], "https://example.test")
            self.assertEqual(cfg["api_token"], "token")
            self.assertEqual(cfg["api_timeout_seconds"], "4")


if __name__ == "__main__":
    unittest.main()
