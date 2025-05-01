# MCP Server with FastAPI

A MCP Server is a server that provides an interface between an API and a LLM. It allows the LLM to interact with the MCP system using HTTP requests. The server is designed to be run in a Docker container and can be accessed via a web browser or any HTTP client.

## How to Run

```commandline
bash scripts/up.sh
```

Access the API at: http://localhost:8001/docs.
Access the SSE endpoint at: http://localhost:8002/sse.

## How to Test

Once it is running, start a virtualenv with the requirements and run:
```commandline
python mcp_client.py
```

## Bring it Down

```commandline
bash scripts/down.sh
```
