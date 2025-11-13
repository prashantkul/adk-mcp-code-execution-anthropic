"""Test the fixed tool generator."""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

sys.path.insert(0, str(Path(__file__).parent / "src"))

from shared import MCPClient, MCPToolGenerator


async def test_generator():
    """Test generating wrapper with the fixed code."""
    load_dotenv()

    ngrok_url = os.getenv("MCP_SERVER_URL", "https://1c8993014273.ngrok-free.app/mcp")

    print(f"🔍 Testing tool generator with MCP server: {ngrok_url}\n")

    # 1. List tools from MCP server
    client = MCPClient(ngrok_url)
    try:
        tools = await client.list_tools()
        print(f"✅ Found {len(tools)} tools from MCP server\n")

        # 2. Generate wrapper module
        generator = MCPToolGenerator(ngrok_url)
        tool_dicts = [tool.model_dump() for tool in tools]
        module_code = generator.generate_wrapper_module(tool_dicts, "customer")

        # 3. Save and display
        output_path = Path("mcp_tools/customer.py")
        generator.write_module_to_file(module_code, output_path)

        print(f"\n📄 Generated module preview (first 50 lines):")
        print("=" * 60)
        lines = module_code.split('\n')
        for i, line in enumerate(lines[:50], 1):
            print(f"{i:3d} | {line}")
        print("=" * 60)

        # 4. Verify the critical _call_mcp_tool function
        if 'jsonrpc": "2.0"' in module_code:
            print("\n✅ PASS: Generated code uses JSON-RPC 2.0 protocol")
        else:
            print("\n❌ FAIL: Generated code doesn't use JSON-RPC 2.0")

        if '"method": "tools/call"' in module_code:
            print("✅ PASS: Uses correct MCP method name")
        else:
            print("❌ FAIL: Incorrect method name")

        if 'response_text.startswith("data: ")' in module_code:
            print("✅ PASS: Handles SSE responses")
        else:
            print("❌ FAIL: Doesn't handle SSE responses")

        print(f"\n✅ Module successfully generated at: {output_path}")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_generator())
