import os
import mlflow

# Both processes log to the same local SQLite store + experiment,
# but each process creates its OWN, unrelated traces.
TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
EXPERIMENT = os.environ.get("MLFLOW_EXPERIMENT", "chat-with-search")
SEARCH_URL = os.environ.get("SEARCH_MCP_URL", "http://127.0.0.1:8000/mcp")


def setup_mlflow():
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT)