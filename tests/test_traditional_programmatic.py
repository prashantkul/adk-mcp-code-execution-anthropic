"""Test traditional MCP agent programmatically using McpToolset."""

import asyncio
import os
from dotenv import load_dotenv
from google.genai import types
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams

load_dotenv()


async def test_traditional_agent():
    """Test traditional MCP agent with McpToolset."""
    mcp_url = os.getenv('MCP_SERVER_URL')
    if not mcp_url:
        print("❌ ERROR: MCP_SERVER_URL not set in .env file")
        return

    print("=" * 80)
    print("TRADITIONAL MCP AGENT - Programmatic Test")
    print("=" * 80)
    print(f"\n📡 MCP Server: {mcp_url}\n")

    # Create toolset
    toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(url=mcp_url)
    )

    # Create agent
    agent = LlmAgent(
        name="traditional_mcp_agent",
        model="gemini-2.0-flash",
        tools=[toolset],
        instruction="""You are a helpful customer management assistant.

You have access to a customer database through MCP tools:
- get_customer: Retrieve a specific customer by ID
- list_customers: List all customers
- add_customer: Add a new customer
- update_customer: Update customer information
- disable_customer: Disable a customer account
- activate_customer: Activate a customer account

Use these tools to help users manage customer data.
Always provide clear, friendly responses.
When performing operations, explain what you're doing.""",
        description="Traditional MCP agent using McpToolset"
    )

    # Setup runner
    runner = InMemoryRunner(agent=agent, app_name="traditional_test")
    session = await runner.session_service.create_session(
        app_name="traditional_test",
        user_id="test_user"
    )

    # Get available tools
    tools = await toolset.get_tools()
    print(f"✅ Connected to MCP server")
    print(f"📋 Available tools: {len(tools)}")
    for tool in tools:
        print(f"   - {tool.name}: {tool.description}")

    # Test queries
    test_queries = [
        "Get customer with ID 2 and show their name and email",
        "List all customers and count how many are active vs disabled"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'─' * 80}")
        print(f"Test {i}: {query}")
        print('─' * 80)

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=query)]
        )

        tool_calls = 0
        final_response = ""

        async for event in runner.run_async(
            user_id="test_user",
            session_id=session.id,
            new_message=content
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.function_call:
                        tool_calls += 1
                        print(f"🔧 Tool call {tool_calls}: {part.function_call.name}")

                    elif part.text:
                        final_response = part.text

            if event.is_final_response():
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            final_response = part.text

        print(f"\n✅ Response: {final_response}")
        print(f"📊 Tool calls made: {tool_calls}")

    await toolset.close()
    print("\n" + "=" * 80)
    print("✅ Traditional agent programmatic test complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_traditional_agent())
