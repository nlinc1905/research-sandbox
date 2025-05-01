from fastmcp import FastMCP


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
    return a + b


# Run with fastmcp run main.py:mcp --transport sse
# The server will be available at http://localhost:8002/sse
# Alternatively, run with python main.py
if __name__ == "__main__":
    mcp.run(transport="sse")
