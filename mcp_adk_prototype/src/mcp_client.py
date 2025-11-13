"""MCP Protocol Client for communicating with MCP servers."""

import httpx
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import json


class MCPTool(BaseModel):
    """Represents an MCP tool definition."""
    name: str
    description: Optional[str] = None
    inputSchema: Dict[str, Any]


class MCPClient:
    """Client for interacting with MCP servers via HTTP."""

    def __init__(self, server_url: str):
        """
        Initialize MCP client.

        Args:
            server_url: Base URL of the MCP server (e.g., ngrok URL)
        """
        self.server_url = server_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)

    async def list_tools(self) -> List[MCPTool]:
        """
        List all available tools from the MCP server.

        Returns:
            List of MCPTool objects
        """
        response = await self.client.post(
            f"{self.server_url}/mcp/v1/tools/list",
            json={}
        )
        response.raise_for_status()
        data = response.json()

        return [MCPTool(**tool) for tool in data.get('tools', [])]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a specific MCP tool.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            Tool execution result
        """
        response = await self.client.post(
            f"{self.server_url}/mcp/v1/tools/call",
            json={
                "name": tool_name,
                "arguments": arguments
            }
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
