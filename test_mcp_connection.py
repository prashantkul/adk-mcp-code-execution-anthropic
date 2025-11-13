"""Quick test script to verify MCP server connection."""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_client import MCPClient


async def test_connection():
    """Test MCP server connection."""
    # Use local server
    mcp_url = os.getenv("MCP_SERVER_URL", f"http://localhost:{os.getenv('CODESIGN_MCP_PORT', '20406')}")

    print(f"🔗 Connecting to MCP server: {mcp_url}")
    print(f"🔑 Using auth token: {os.getenv('CODESIGN_MCP_TOKEN', 'None')[:20]}...\n")

    client = MCPClient(mcp_url)

    try:
        # Test 1: List tools
        print("📋 Test 1: Listing available tools...")
        tools = await client.list_tools()
        print(f"✅ Success! Found {len(tools)} tools:\n")

        for tool in tools:
            print(f"  • {tool.name}")
            if tool.description:
                print(f"    Description: {tool.description}")
            print(f"    Parameters: {list(tool.inputSchema.get('properties', {}).keys())}")
            print()

        # Test 2: Try calling a tool (if any exist)
        if tools:
            print(f"\n🔧 Test 2: Calling first tool ({tools[0].name})...")
            try:
                # Get required parameters
                required = tools[0].inputSchema.get('required', [])
                properties = tools[0].inputSchema.get('properties', {})

                # Build arguments (use empty/default values for testing)
                arguments = {}
                for param in required:
                    param_type = properties.get(param, {}).get('type', 'string')
                    if param_type == 'string':
                        arguments[param] = "test_value"
                    elif param_type == 'integer':
                        arguments[param] = 123
                    elif param_type == 'boolean':
                        arguments[param] = True

                print(f"  Arguments: {arguments}")
                result = await client.call_tool(tools[0].name, arguments)
                print(f"✅ Tool call successful!")
                print(f"  Result: {result}")
            except Exception as e:
                print(f"⚠️  Tool call failed (expected for test data): {e}")

        print("\n" + "="*60)
        print("✅ MCP server connection test PASSED!")
        print("="*60)

    except Exception as e:
        print(f"\n❌ Connection test FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_connection())
