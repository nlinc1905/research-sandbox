from fastmcp import FastMCP
import requests

# Create an MCP server
mcp = FastMCP(
    name="Calculator",
    host="0.0.0.0",
    port=8002,
)


@mcp.tool(
    name="add",
    description="Add two numbers together",
)
def add(a: int, b: int) -> int:
    """Add two numbers together"""
    # Replace the URL with the actual URL of your API
    response = requests.get("http://172.17.0.1:8001/add", params={"a": a, "b": b})
    return response.json()


# Run with fastmcp run main.py:mcp --transport sse
# The server will be available at http://localhost:8002/sse
# Alternatively, run with python main.py
if __name__ == "__main__":
    mcp.run(transport="sse")
