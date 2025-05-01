from fastapi import FastAPI, APIRouter
from src.sse import create_sse_server
from mcp.server.fastmcp import FastMCP, Context
from pydantic import Field
from typing import Annotated
import time


app = FastAPI()
mcp = FastMCP(
    name="Echo",
    instructions="Echo the message you receive.",
)

# Mount the Starlette SSE server onto the FastAPI app
app.mount("/", create_sse_server(mcp))


@app.get("/")
def read_root():
    return {"Hello": "World"}


# If these arguments are not provided to @mcp.tool, they will have the following defaults:
# name = function name
# description = function docstring
# schema = type hints (can be Pydantic Fields)
@mcp.tool()
async def echo_tool(
    message: Annotated[str, Field(description="The message to echo")],
    context: Context = Field(
        description="The context of the tool invocation, including metadata."
    ),
) -> str:
    """Echo a message as a tool"""
    await context.info("Processing your message...")
    time.sleep(3)
    await context.report_progress(progress=100, total=100)
    return f"Tool echo: {message}"


@mcp.prompt()
def echo_prompt(message: str) -> str:
    """Create an echo prompt"""
    return f"Please process this message: {message}"


# If these arguments are not provided to @mcp.resource, they will have the following defaults:
# name = function name
# description = function docstring
# mime_type = "application/json"
# tags = empty set, {}
@mcp.resource(uri="echo://{message}")
def echo_resource(message: str) -> str:
    """Echo a message as a resource"""
    return f"Resource echo: {message}"
