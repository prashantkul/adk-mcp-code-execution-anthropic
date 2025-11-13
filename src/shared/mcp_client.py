"""MCP Protocol Client for communicating with MCP servers."""

import httpx
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import json
import os


class MCPTool(BaseModel):
    """Represents an MCP tool definition."""
    name: str
    description: Optional[str] = None
    inputSchema: Dict[str, Any]


class MCPClient:
    """Client for interacting with MCP servers via HTTP using JSON-RPC 2.0."""

    def __init__(self, server_url: str, auth_token: Optional[str] = None):
        """
        Initialize MCP client.

        Args:
            server_url: Base URL of the MCP server (e.g., http://localhost:20406)
            auth_token: Optional authentication token
        """
        self.server_url = server_url.rstrip('/')
        self.auth_token = auth_token or os.getenv("CODESIGN_MCP_TOKEN")
        self.request_id = 0

        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        self.client = httpx.AsyncClient(timeout=30.0, headers=headers)

    def _next_id(self) -> int:
        """Get next request ID."""
        self.request_id += 1
        return self.request_id

    async def _call_jsonrpc(self, method: str, params: Dict[str, Any] = None) -> Any:
        """
        Make a JSON-RPC 2.0 call to the MCP server.

        Args:
            method: The JSON-RPC method name
            params: Method parameters

        Returns:
            The result from the JSON-RPC response
        """
        request_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self._next_id()
        }

        response = await self.client.post(
            self.server_url,
            json=request_payload
        )
        response.raise_for_status()

        # Handle SSE (Server-Sent Events) format
        response_text = response.text

        # Check if response is SSE format (starts with "data: ")
        if response_text.startswith("data: "):
            # Extract JSON from SSE format
            # SSE format: "data: {json}\n\n"
            lines = response_text.split('\n')
            for line in lines:
                if line.startswith("data: "):
                    json_str = line[6:]  # Remove "data: " prefix
                    data = json.loads(json_str)
                    break
            else:
                # Fallback: try to parse as regular JSON
                data = response.json()
        else:
            # Regular JSON response
            data = response.json()

        if "error" in data:
            raise Exception(f"JSON-RPC Error: {data['error']}")

        return data.get("result", {})

    async def list_tools(self) -> List[MCPTool]:
        """
        List all available tools from the MCP server.

        Returns:
            List of MCPTool objects
        """
        result = await self._call_jsonrpc("tools/list", {})
        tools = result.get("tools", [])

        return [MCPTool(**tool) for tool in tools]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a specific MCP tool.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            Tool execution result
        """
        result = await self._call_jsonrpc("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })

        return result

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
