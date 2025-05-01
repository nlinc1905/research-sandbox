# MCP Server

A MCP Server provides an API for the MCP (Multi-Channel Processing) system. It allows you to interact with the MCP system using HTTP requests. The server is designed to be run in a Docker container and can be accessed via a web browser or any HTTP client.

## How to Run

```commandline
docker compose up --build
```

Access the SSE endpoint at: http://localhost:8002/sse.

## How to Test

Once it is running, start a virtualenv with the requirements and run:
```commandline
python mcp_client.py
```

## Bring it Down

```commandline
docker compose down
```
