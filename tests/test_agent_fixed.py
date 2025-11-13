"""Test the fixed DockerCodeExecutorOptimized with ADK agent."""

import asyncio
import os
from dotenv import load_dotenv
from google.genai import types
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from src.shared.docker_code_executor_optimized import DockerCodeExecutorOptimized

load_dotenv()

async def main():
    mcp_url = os.getenv('MCP_SERVER_URL')
    print(f"Testing with MCP URL: {mcp_url}\n")

    # Create the optimized executor
    print("Creating DockerCodeExecutorOptimized...")
    executor = DockerCodeExecutorOptimized(
        allowed_url=mcp_url,
        timeout=30,
        image="mcp-executor-optimized:latest"
    )
    print("✅ Executor created\n")

    # Create agent with code executor
    print("Creating LlmAgent with code executor...")
    agent = LlmAgent(
        name="test_agent",
        model="gemini-2.0-flash",
        code_executor=executor,
        instruction=f"""You are a Python code execution agent.

When asked to call the MCP server, write Python code using urllib (no httpx):

```python
import urllib.request
import json

MCP_URL = "{mcp_url}"

def call_mcp(tool_name, arguments=None):
    req_data = {{
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {{"name": tool_name, "arguments": arguments or {{}}}},
        "id": 1
    }}
    req = urllib.request.Request(
        MCP_URL,
        data=json.dumps(req_data).encode('utf-8'),
        headers={{'Content-Type': 'application/json'}}
    )
    with urllib.request.urlopen(req) as response:
        text = response.read().decode('utf-8')
        if text.startswith("data: "):
            lines = text.split('\\n')
            for line in lines:
                if line.startswith("data: "):
                    text = line[6:]
                    break
        data = json.loads(text)
        return data.get("result", {{}})

# Use call_mcp to interact with the MCP server
```
""",
        description="Test agent with optimized executor"
    )
    print("✅ Agent created\n")

    # Setup session and runner
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="test_app",
        user_id="test_user",
        session_id="test_session"
    )

    runner = Runner(
        agent=agent,
        app_name="test_app",
        session_service=session_service
    )
    print("✅ Runner created\n")

    # Test with a simple query
    task = "Get customer with ID 2 from the MCP server"
    print(f"Task: {task}\n")
    print("=" * 60)

    content = types.Content(
        role="user",
        parts=[types.Part(text=task)]
    )

    async for event in runner.run_async(
        user_id="test_user",
        session_id="test_session",
        new_message=content
    ):
        # Print code execution
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.executable_code:
                    print(f"\n🔧 Generated Code:\n")
                    print("```python")
                    print(part.executable_code.code)
                    print("```\n")

                elif part.code_execution_result:
                    print(f"📊 Execution Result: {part.code_execution_result.outcome}")
                    if part.code_execution_result.output:
                        print(f"Output:\n{part.code_execution_result.output}\n")

        # Print final response
        if event.is_final_response():
            if event.content and event.content.parts:
                final_text = event.content.parts[0].text
                print(f"\n✅ Final Response:\n{final_text}\n")

    print("=" * 60)
    print("\n✅ Test completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
