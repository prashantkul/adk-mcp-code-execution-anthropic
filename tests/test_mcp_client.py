"""Tests for MCP client."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.mcp_client import MCPClient, MCPTool


@pytest.fixture
def mcp_client():
    """Create an MCP client for testing."""
    return MCPClient("https://test.ngrok.io")


@pytest.mark.asyncio
async def test_list_tools(mcp_client):
    """Test listing tools from MCP server."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "tools": [
            {
                "name": "get_customer",
                "description": "Get customer details",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "customer_id": {"type": "string"}
                    }
                }
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(mcp_client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        tools = await mcp_client.list_tools()

        assert len(tools) == 1
        assert tools[0].name == "get_customer"
        assert tools[0].description == "Get customer details"
        mock_post.assert_called_once_with(
            "https://test.ngrok.io/mcp/v1/tools/list",
            json={}
        )


@pytest.mark.asyncio
async def test_call_tool(mcp_client):
    """Test calling an MCP tool."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "content": [{"text": "Customer data"}]
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(mcp_client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        result = await mcp_client.call_tool("get_customer", {"customer_id": "123"})

        assert result == {"content": [{"text": "Customer data"}]}
        mock_post.assert_called_once_with(
            "https://test.ngrok.io/mcp/v1/tools/call",
            json={
                "name": "get_customer",
                "arguments": {"customer_id": "123"}
            }
        )


@pytest.mark.asyncio
async def test_close(mcp_client):
    """Test closing the client."""
    with patch.object(mcp_client.client, 'aclose', new_callable=AsyncMock) as mock_close:
        await mcp_client.close()
        mock_close.assert_called_once()
