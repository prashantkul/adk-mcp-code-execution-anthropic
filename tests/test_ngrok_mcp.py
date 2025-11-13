"""Test accessing the ngrok MCP server."""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from shared import MCPClient


async def test_ngrok():
    """Test connection to ngrok MCP server."""

    ngrok_url = os.getenv("NGROK_URL", "https://1c8993014273.ngrok-free.app/mcp")

    print(f"🔗 Attempting to connect to: {ngrok_url}")
    print(f"🔑 Auth token: {os.getenv('CODESIGN_MCP_TOKEN', 'None')[:20]}...")

    # Try without auth first
    print("\n1️⃣ Trying without authentication...")
    client1 = MCPClient(ngrok_url, auth_token=None)

    try:
        tools = await client1.list_tools()
        print(f"✅ SUCCESS! Found {len(tools)} tools")
        for tool in tools:
            print(f"  • {tool.name}: {tool.description}")
        return tools
    except Exception as e:
        print(f"❌ Failed: {e}")
    finally:
        await client1.close()

    # Try with auth token
    print("\n2️⃣ Trying with CODESIGN_MCP_TOKEN...")
    client2 = MCPClient(ngrok_url, auth_token=os.getenv("CODESIGN_MCP_TOKEN"))

    try:
        tools = await client2.list_tools()
        print(f"✅ SUCCESS! Found {len(tools)} tools")
        for tool in tools:
            print(f"  • {tool.name}: {tool.description}")
        return tools
    except Exception as e:
        print(f"❌ Failed: {e}")
    finally:
        await client2.close()

    # Try different URL variations
    print("\n3️⃣ Trying without /mcp suffix...")
    base_url = ngrok_url.replace("/mcp", "")
    client3 = MCPClient(base_url, auth_token=None)

    try:
        tools = await client3.list_tools()
        print(f"✅ SUCCESS! Found {len(tools)} tools")
        for tool in tools:
            print(f"  • {tool.name}: {tool.description}")
        return tools
    except Exception as e:
        print(f"❌ Failed: {e}")
    finally:
        await client3.close()

    print("\n⚠️  All connection attempts failed.")
    print("\nPlease provide:")
    print("  1. Exact MCP server URL")
    print("  2. Authentication method (if any)")
    print("  3. Any required headers")


if __name__ == "__main__":
    asyncio.run(test_ngrok())
