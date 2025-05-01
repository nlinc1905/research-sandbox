# MCP Server with FastAPI

# DON'T USE THIS ONE, USE api_with_mcp_server3

A MCP Server is a FastAPI server that provides an API for the MCP (Multi-Channel Processing) system. It allows you to 
interact with the MCP system using HTTP requests. The server is designed to be run in a Docker container and can be 
accessed via a web browser or any HTTP client.

## How to Run

```commandline
docker compose up --build
```

Access the API at: http://localhost:8000/docs.
Access the SSE endpoint at: http://localhost:8000/sse.

## How to Test

Once it is running, start a virtualenv with the requirements and run:
```commandline
python mcp_client.py
```

## Bring it Down

```commandline
docker compose down
```
