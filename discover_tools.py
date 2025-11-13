"""Discover and analyze all available MCP tools."""

import asyncio
import os
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_client import MCPClient


async def discover_all_tools():
    """Discover all tools from the MCP server."""

    mcp_url = os.getenv("MCP_SERVER_URL", f"http://localhost:{os.getenv('CODESIGN_MCP_PORT', '20406')}")

    print("🔍 Discovering all available MCP tools...")
    print(f"📡 Server: {mcp_url}\n")

    client = MCPClient(mcp_url)

    try:
        tools = await client.list_tools()

        print(f"✅ Found {len(tools)} tool(s)\n")
        print("="*80)

        total_schema_tokens = 0

        for i, tool in enumerate(tools, 1):
            print(f"\n{i}. {tool.name}")
            print("   " + "─"*70)

            if tool.description:
                print(f"   Description: {tool.description}")

            # Parameters
            properties = tool.inputSchema.get('properties', {})
            required = tool.inputSchema.get('required', [])

            if properties:
                print(f"   Parameters ({len(properties)}):")
                for param_name, param_info in properties.items():
                    param_type = param_info.get('type', 'any')
                    param_desc = param_info.get('description', 'No description')
                    required_mark = " [REQUIRED]" if param_name in required else " [optional]"
                    print(f"      • {param_name}: {param_type}{required_mark}")
                    print(f"        {param_desc}")
            else:
                print("   Parameters: None")

            # Estimate token count for this tool's schema
            tool_schema_str = json.dumps(tool.model_dump())
            tool_tokens = len(tool_schema_str) // 4  # Rough estimate: 4 chars per token
            total_schema_tokens += tool_tokens

            print(f"   Estimated schema size: ~{tool_tokens} tokens")

        print("\n" + "="*80)
        print(f"\n📊 TOTAL SCHEMA SIZE: ~{total_schema_tokens} tokens")
        print(f"   (This is loaded in context for traditional approach)")
        print(f"   (Code execution approach: 0 tokens - schemas on disk)")

        print("\n" + "="*80)
        print("💡 Token Reduction Analysis")
        print("="*80)

        # Calculate token reduction for different scenarios

        # Simple workflow: Call 1 tool
        simple_traditional = total_schema_tokens + 200  # schemas + call + response
        simple_code_exec = 200  # just code + summary
        simple_reduction = ((simple_traditional - simple_code_exec) / simple_traditional) * 100

        # Medium workflow: Call 3 tools
        medium_traditional = total_schema_tokens + (3 * 300)  # schemas + 3 calls
        medium_code_exec = 350  # code orchestrating all 3
        medium_reduction = ((medium_traditional - medium_code_exec) / medium_traditional) * 100

        # Complex workflow: Call 5+ tools with data processing
        complex_traditional = total_schema_tokens + (5 * 400) + 1000  # + large response data
        complex_code_exec = 500  # code + summary only
        complex_reduction = ((complex_traditional - complex_code_exec) / complex_traditional) * 100

        print(f"""
Scenario 1: Simple (call 1 tool)
  Traditional:     ~{simple_traditional:,} tokens
  Code Execution:  ~{simple_code_exec:,} tokens
  Reduction:       {simple_reduction:.1f}%

Scenario 2: Medium (call 3 tools sequentially)
  Traditional:     ~{medium_traditional:,} tokens
  Code Execution:  ~{medium_code_exec:,} tokens
  Reduction:       {medium_reduction:.1f}%

Scenario 3: Complex (call 5+ tools + process data)
  Traditional:     ~{complex_traditional:,} tokens
  Code Execution:  ~{complex_code_exec:,} tokens
  Reduction:       {complex_reduction:.1f}%

💡 Key Insight: With {len(tools)} tool(s) available, the traditional approach
   pays the {total_schema_tokens:,}-token schema cost EVERY time, while code
   execution pays 0 tokens (schemas stored as Python modules).
        """)

        # Save tool info for later use
        tools_info = {
            "tool_count": len(tools),
            "total_schema_tokens": total_schema_tokens,
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "parameters": list(t.inputSchema.get('properties', {}).keys()),
                    "required": t.inputSchema.get('required', [])
                }
                for t in tools
            ]
        }

        with open("discovered_tools.json", "w") as f:
            json.dump(tools_info, f, indent=2)

        print(f"\n📝 Tool information saved to: discovered_tools.json")

        return tools

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(discover_all_tools())
