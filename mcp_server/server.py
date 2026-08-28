import httpx
import os
import re
from typing import Any, List
import mcp.types as types
from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field

# Initialize MCP server
mcp = MCPServer("SentinelMCP", version="1.0.0")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "system.log")

@mcp.tool()
async def get_current_telemetry() -> dict[str, Any]:
    """Fetches live telemetry data from the Sentinel backend."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/telemetry/current", timeout=5.0)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Backend returned status {response.status_code}", "details": response.text}
    except httpx.RequestError as e:
        return {"error": "Failed to connect to Sentinel backend", "details": str(e)}

@mcp.tool()
async def query_system_logs(
    keyword: str = Field(..., description="Keyword to search for in the logs (e.g., 'ERROR', 'SLAM')"),
    max_lines: int = Field(10, description="Maximum number of matching log lines to return")
) -> list[str]:
    """Reads local system log files and returns matching entries."""
    if not os.path.exists(LOG_FILE_PATH):
        return [f"Error: Log file not found at {LOG_FILE_PATH}"]
    
    matches = []
    try:
        with open(LOG_FILE_PATH, 'r') as f:
            for line in f:
                if keyword.lower() in line.lower():
                    matches.append(line.strip())
                    if len(matches) >= max_lines:
                        break
        if not matches:
            return [f"No logs found matching keyword '{keyword}'"]
        return matches
    except Exception as e:
        return [f"Error reading log file: {str(e)}"]

if __name__ == "__main__":
    # Typically run via stdio using `mcp.run()`
    mcp.run(transport='stdio')
