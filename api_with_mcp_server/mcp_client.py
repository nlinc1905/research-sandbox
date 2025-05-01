from fastmcp.client import Client
import asyncio


# Note the `sse` path post-fix for sse servers
# For all transports, see https://gofastmcp.com/clients/client#transports
sse_url = "http://localhost:8002/sse"
client = Client(sse_url)


async def call_tool(tool_name, *args, **kwargs):
    """Call a tool on the server with the given name and arguments."""
    inputs = kwargs["inputs"] if "inputs" in kwargs else args[0]

    # Ensure the client is connected before calling the tool
    if not client.is_connected():
        print("Client is not connected. Attempting to connect...")
        await client.connect()

    # Check if the tool is available
    tools = await client.list_tools()
    tool_names = [tool.name for tool in tools]
    if tool_name not in tool_names:
        print(f"Tool {tool_name} is not available.")
        return

    # Call the tool with the given name and arguments
    print(f"Calling tool {tool_name} with arguments: {args}, {kwargs}")
    async with client:
        # Call the tool with the given name and arguments
        result = await client.call_tool(tool_name, inputs)
        return result


async def main():
    # Connection is established here
    async with client:
        print(f"Client connected: {client.is_connected()}")
        tools = await client.list_tools()
        print(f"Available tools: {tools}")

        # Call the add tool with arguments
        inputs = {"a": 1, "b": 2}
        result = await call_tool("add", inputs)
        print(f"Result from add: {result}")

    # Connection is closed automatically here
    print(f"Client connected: {client.is_connected()}")


if __name__ == "__main__":
    asyncio.run(main())
