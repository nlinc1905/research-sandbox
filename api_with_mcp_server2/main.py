from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
from pydantic import Field
from typing import Annotated

app = FastAPI()


@app.get("/add", operation_id="add_two_numbers")
async def add_tool(
    a: Annotated[float, Field(description="First number")],
    b: Annotated[float, Field(description="Second number")],
) -> float:
    """Add two numbers together"""
    return a + b


mcp = FastApiMCP(
    app,
    name="API MCP",
    description="MCP server for FastAPI",
    describe_all_responses=True,  # Include all possible response schemas
    describe_full_response_schema=True  # Include full JSON schema details
)
# Mount the MCP server directly to your FastAPI app
mcp.mount()


if __name__ == "__main__":
    # Run the FastAPI app with Uvicorn
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)

# access at http://localhost:8002/mcp
