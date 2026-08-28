import asyncio
import os
import sys
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

async def main():
    server_script = os.path.join(os.path.dirname(__file__), "..", "mcp_server", "server.py")
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script]
    )

    print(f"Connecting to MCP server at {server_script}...")
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("Session initialized.")

            # List tools
            tools_response = await session.list_tools()
            print("\nAvailable tools:")
            for tool in tools_response.tools:
                print(f"- {tool.name}: {tool.description}")

            # Call get_current_telemetry
            print("\nCalling tool: get_current_telemetry")
            try:
                result = await session.call_tool("get_current_telemetry", {})
                print(f"Result: {result}")
            except Exception as e:
                print(f"Error calling tool: {e}")

            # Call query_system_logs
            print("\nCalling tool: query_system_logs")
            try:
                result = await session.call_tool("query_system_logs", {"keyword": "ERROR", "max_lines": 5})
                print(f"Result: {result}")
            except Exception as e:
                print(f"Error calling tool: {e}")

if __name__ == "__main__":
    asyncio.run(main())

