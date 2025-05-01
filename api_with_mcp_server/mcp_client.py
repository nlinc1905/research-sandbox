from fastmcp.client import Client
import asyncio


# Note the `sse` path post-fix for sse servers
# For all transports, see https://gofastmcp.com/clients/client#transports
sse_url = "http://localhost:8000/sse"
client = Client(sse_url)


async def main():
    # Connection is established here
    async with client:
        print(f"Client connected: {client.is_connected()}")
        tools = await client.list_tools()
        print(f"Available tools: {tools}")

        if any(tool.name == "edit_file" for tool in tools):
            result = await client.call_tool(
                "edit_file",
                {
                    "filename": "hello-world.txt",
                    "line": "This text will be added to the file.",
                },
            )
            print(f"Greet result: {result}")

    # Connection is closed automatically here
    print(f"Client connected: {client.is_connected()}")


if __name__ == "__main__":
    asyncio.run(main())
