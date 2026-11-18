"""Search agent, exposed as an MCP tool over streamable HTTP (separate process).

It has its own MLflow tracing: every tool call produces a standalone trace
rooted at `search_agent`.
"""
import json
import os
import time

import mlflow
from mcp.server.fastmcp import FastMCP
from mlflow.entities import SpanType

from config import setup_mlflow

setup_mlflow()

FAKE_CORPUS = {
    "python": "Python 3.13 added an experimental free-threaded (no-GIL) build.",
    "mlflow": "MLflow 3 added first-class tracing for GenAI apps, incl. LangChain/LangGraph autologging.",
    "mcp": "Model Context Protocol (MCP) is an open protocol for connecting LLM apps to tools and data.",
    "weather": "It is 18C and cloudy in the fake-weather dataset.",
}


@mlflow.trace(span_type=SpanType.CHAIN, name="plan_query")
def plan_query(query: str) -> list[str]:
    time.sleep(0.05)
    return [w for w in query.lower().replace("?", "").split() if len(w) >= 3]


@mlflow.trace(span_type=SpanType.RETRIEVER, name="retrieve")
def retrieve(terms: list[str]) -> list[str]:
    time.sleep(0.1)
    return [doc for key, doc in FAKE_CORPUS.items() if key in terms] or ["No results found."]


@mlflow.trace(span_type=SpanType.LLM, name="synthesize")
def synthesize(query: str, docs: list[str]) -> str:
    time.sleep(0.05)
    return " ".join(docs)


@mlflow.trace(span_type=SpanType.AGENT, name="search_agent")
def run_search_agent(query: str) -> str:
    terms = plan_query(query)
    docs = retrieve(terms)
    return synthesize(query, docs)


mcp = FastMCP("search-agent", host="127.0.0.1", port=8000)


ENVELOPE_KEY = "__mlflow_trace_envelope__"
FAIL_MODE = os.environ.get("FAIL_MODE", "")  # test hook: "", "no_trace", "bad_trace"


@mcp.tool()
def search_agent(query: str, include_trace: bool = False) -> str:
    """Search the knowledge base and return a short synthesized answer."""
    answer = run_search_agent(query)
    if not include_trace or FAIL_MODE == "no_trace":
        return answer
    # Try to attach the current trace to the response for the caller.
    # If the trace cannot be obtained, return the answer without the trace to avoid breaking the caller.
    try:
        # Get the trace with flush=True to ensure the trace is fully written before fetching it.
        trace = mlflow.get_trace(mlflow.get_last_active_trace_id(), flush=True)
        if trace is None:
            return answer
        trace_dict = {"bogus": True} if FAIL_MODE == "bad_trace" else json.loads(trace.to_json())
        return json.dumps({
            ENVELOPE_KEY: True,
            "answer": answer,
            "original_trace_id": trace.info.trace_id,
            "trace": trace_dict,
        })
    except Exception:
        return answer


if __name__ == "__main__":
    print("Search agent MCP server on http://127.0.0.1:8000/mcp")
    mcp.run(transport="streamable-http")
