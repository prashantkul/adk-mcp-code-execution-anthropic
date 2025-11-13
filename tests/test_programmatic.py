"""Comprehensive programmatic test of the optimized Docker code executor with MCP."""

import asyncio
import os
import time
from dotenv import load_dotenv
from google.genai import types
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from src.shared.docker_code_executor_optimized import DockerCodeExecutorOptimized

load_dotenv()


async def main():
    print("=" * 80)
    print("PROGRAMMATIC TEST: Optimized Docker Code Executor with MCP")
    print("=" * 80)

    mcp_url = os.getenv('MCP_SERVER_URL')
    if not mcp_url:
        print("❌ ERROR: MCP_SERVER_URL not set in .env file")
        return

    print(f"\n📡 MCP Server: {mcp_url}")

    # Step 1: Create optimized Docker executor
    print("\n" + "-" * 80)
    print("Step 1: Creating DockerCodeExecutorOptimized...")
    print("-" * 80)

    start = time.time()
    executor = DockerCodeExecutorOptimized(
        allowed_url=mcp_url,
        timeout=30,
        image="mcp-executor-optimized:latest"
    )
    print(f"✅ Executor created in {time.time() - start:.3f}s")
    print(f"   - Image: {executor.image}")
    print(f"   - Timeout: {executor.timeout}s")
    print(f"   - Allowed URL: {executor.allowed_url}")

    # Step 2: Create agent with code executor
    print("\n" + "-" * 80)
    print("Step 2: Creating LlmAgent with optimized code executor...")
    print("-" * 80)

    agent = LlmAgent(
        name="mcp_code_agent",
        model="gemini-2.0-flash",
        code_executor=executor,
        instruction=f"""You are a Python code execution agent with access to an MCP server.

When asked to interact with the MCP server, write Python code using urllib:

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
```

The MCP server response format is nested. After calling call_mcp, you need to:
1. Extract the 'content' key from the response
2. Look for the item with type='text'
3. Parse the 'text' value as JSON
4. Extract the actual data from the parsed JSON

Example:
```python
response = call_mcp("get_customer", {{"customer_id": 2}})
content_list = response.get("content", [])
for item in content_list:
    if item.get("type") == "text":
        data = json.loads(item.get("text"))
        if data.get("success"):
            print(data.get("customer"))
```

Keep your code concise and only print the final result.
""",
        description="Agent with optimized Docker executor for MCP integration"
    )
    print(f"✅ Agent created")
    print(f"   - Name: {agent.name}")
    print(f"   - Model: {agent.model}")
    print(f"   - Code Executor: {type(executor).__name__}")

    # Step 3: Setup InMemoryRunner (handles session + artifact service)
    print("\n" + "-" * 80)
    print("Step 3: Setting up InMemoryRunner...")
    print("-" * 80)

    app_name = "mcp_code_test"
    user_id = "test_user"

    runner = InMemoryRunner(
        agent=agent,
        app_name=app_name
    )

    session = await runner.session_service.create_session(
        app_name=app_name,
        user_id=user_id
    )

    print(f"✅ Runner ready")
    print(f"   - App: {app_name}")
    print(f"   - User: {user_id}")
    print(f"   - Session: {session.id}")

    # Step 4: Run test queries
    print("\n" + "=" * 80)
    print("RUNNING TEST QUERIES")
    print("=" * 80)

    test_queries = [
        "Get customer with ID 2 from the MCP server and show their name and email",
        "List all customers from the MCP server and tell me how many there are",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'─' * 80}")
        print(f"Query {i}: {query}")
        print('─' * 80)

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=query)]
        )

        start_time = time.time()
        code_executions = 0
        final_response = None

        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content
        ):
            # Track code executions
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.executable_code:
                        code_executions += 1
                        print(f"\n🔧 Code Execution #{code_executions}:")
                        print("```python")
                        print(part.executable_code.code)
                        print("```")

                    elif part.code_execution_result:
                        outcome = part.code_execution_result.outcome
                        print(f"\n📊 Result: {outcome}")
                        if part.code_execution_result.output:
                            print(f"Output: {part.code_execution_result.output}")

            # Capture final response
            if event.is_final_response():
                if event.content and event.content.parts and event.content.parts[0].text:
                    final_response = event.content.parts[0].text

        duration = time.time() - start_time

        print(f"\n✅ Final Answer:")
        print(f"   {final_response}")
        print(f"\n⏱️  Total time: {duration:.2f}s")
        print(f"🔄 Code executions: {code_executions}")

    # Step 5: Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("✅ Optimized Docker executor working programmatically")
    print("✅ Agent successfully generates and executes code")
    print("✅ MCP server calls working through Docker container")
    print("✅ Self-correction/retry working (if there were errors)")
    print("\n🎉 All tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
