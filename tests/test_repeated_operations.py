"""Test repeated operations to show context accumulation differences."""

import asyncio
import os
import time
import json
from dotenv import load_dotenv
from google.genai import types
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from src.shared.docker_code_executor_optimized import DockerCodeExecutorOptimized

load_dotenv()


def estimate_tokens(text: str) -> int:
    """Rough token estimation (4 chars ≈ 1 token)."""
    return len(text) // 4


async def test_code_execution_batch(mcp_url: str):
    """Test code execution with ALL operations in a SINGLE code block."""
    print("\n" + "=" * 80)
    print("CODE EXECUTION: 10 operations in ONE code block")
    print("=" * 80)

    executor = DockerCodeExecutorOptimized(
        allowed_url=mcp_url,
        timeout=30,
        image="mcp-executor-optimized:latest"
    )

    agent = LlmAgent(
        name="code_exec_batch",
        model="gemini-2.0-flash",
        code_executor=executor,
        instruction=f"""You are a Python code execution agent.

MCP URL: {mcp_url}

Write Python code using urllib to call the MCP server:

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

# Parse: content[0]['text'] contains JSON string
def get_customer_data(customer_id):
    response = call_mcp("get_customer", {{"customer_id": customer_id}})
    if response.get("content"):
        data = json.loads(response["content"][0]["text"])
        return data.get("customer")
    return None
```

Process data in code, return ONLY final summary."""
    )

    runner = InMemoryRunner(agent=agent, app_name="batch_test")
    session = await runner.session_service.create_session(
        app_name="batch_test",
        user_id="test_user"
    )

    # Single query that processes 10 customers
    query = "Get details for customers with IDs 1 through 10 and tell me how many are active vs disabled"

    print(f"\n📝 Query: {query}\n")

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=query)]
    )

    start_time = time.time()
    total_tokens = 0
    context_tokens = estimate_tokens(agent.instruction)

    async for event in runner.run_async(
        user_id="test_user",
        session_id=session.id,
        new_message=content
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.executable_code:
                    code_tokens = estimate_tokens(part.executable_code.code)
                    print(f"🔧 Generated code: {code_tokens} tokens")
                    total_tokens += code_tokens

                elif part.code_execution_result:
                    result_tokens = estimate_tokens(part.code_execution_result.output or "")
                    print(f"📊 Execution result: {result_tokens} tokens")
                    print(f"   Output: {part.code_execution_result.output}\n")
                    total_tokens += result_tokens

        if event.is_final_response():
            if event.content and event.content.parts and event.content.parts[0].text:
                final = event.content.parts[0].text
                print(f"✅ Final Answer: {final}")

    duration = time.time() - start_time
    total_tokens += context_tokens + estimate_tokens(query)

    print(f"\n📊 Token Summary:")
    print(f"   Context: {context_tokens} tokens")
    print(f"   Total: {total_tokens:,} tokens")
    print(f"   Duration: {duration:.2f}s")
    print(f"   Operations: 10 customers in 1 code block")

    return {
        "total_tokens": total_tokens,
        "context_tokens": context_tokens,
        "duration": duration,
        "operations": 10
    }


async def test_traditional_sequential(mcp_url: str):
    """Test traditional approach with 10 SEQUENTIAL tool calls."""
    print("\n" + "=" * 80)
    print("TRADITIONAL: 10 SEQUENTIAL tool calls (context accumulation)")
    print("=" * 80)

    toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(url=mcp_url)
    )

    instruction = """You are a customer management assistant.
Use MCP tools to get customer information.
Provide concise responses."""

    agent = LlmAgent(
        name="traditional_seq",
        model="gemini-2.0-flash",
        tools=[toolset],
        instruction=instruction
    )

    runner = InMemoryRunner(agent=agent, app_name="seq_test")
    session = await runner.session_service.create_session(
        app_name="seq_test",
        user_id="test_user"
    )

    # Get tool schemas
    tools = await toolset.get_tools()
    tool_schemas = [{"name": t.name, "description": t.description} for t in tools]
    context_tokens = estimate_tokens(instruction) + estimate_tokens(json.dumps(tool_schemas))

    print(f"📡 Loaded {len(tools)} tools\n")

    # Make 10 sequential queries
    customer_ids = list(range(1, 11))
    total_tokens = context_tokens
    total_duration = 0
    all_results = []

    for i, customer_id in enumerate(customer_ids, 1):
        query = f"Get customer {customer_id}"
        print(f"\n[{i}/10] Query: {query}")

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=query)]
        )

        start_time = time.time()
        query_tokens = estimate_tokens(query)
        tool_result_tokens = 0

        async for event in runner.run_async(
            user_id="test_user",
            session_id=session.id,
            new_message=content
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.function_call:
                        print(f"   🔧 Tool: {part.function_call.name}")

                    elif part.function_response:
                        response_str = json.dumps(part.function_response.response)
                        tool_result_tokens = estimate_tokens(response_str)

                    elif part.text:
                        print(f"   ✅ Response: {part.text[:80]}...")

        duration = time.time() - start_time
        total_duration += duration

        # IMPORTANT: After each turn, the context grows!
        # Previous queries + results stay in conversation history
        turn_tokens = query_tokens + tool_result_tokens
        total_tokens += turn_tokens

        print(f"   Tokens this turn: {turn_tokens}")
        print(f"   Cumulative tokens: {total_tokens:,}")
        print(f"   Duration: {duration:.2f}s")

        all_results.append({
            "customer_id": customer_id,
            "turn_tokens": turn_tokens,
            "cumulative_tokens": total_tokens
        })

    # Final summary query
    summary_query = "Based on all the customers I asked about, how many are active vs disabled?"
    print(f"\n[SUMMARY] Query: {summary_query}")

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=summary_query)]
    )

    start_time = time.time()
    async for event in runner.run_async(
        user_id="test_user",
        session_id=session.id,
        new_message=content
    ):
        if event.is_final_response():
            if event.content and event.content.parts and event.content.parts[0].text:
                print(f"   ✅ {event.content.parts[0].text}")

    total_duration += time.time() - start_time
    total_tokens += estimate_tokens(summary_query)

    await toolset.close()

    print(f"\n📊 Token Summary:")
    print(f"   Initial context: {context_tokens} tokens")
    print(f"   Total (with accumulation): {total_tokens:,} tokens")
    print(f"   Duration: {total_duration:.2f}s")
    print(f"   Operations: 10 sequential tool calls + 1 summary")

    return {
        "total_tokens": total_tokens,
        "context_tokens": context_tokens,
        "duration": total_duration,
        "operations": 11,  # 10 + 1 summary
        "results": all_results
    }


async def main():
    mcp_url = os.getenv('MCP_SERVER_URL')
    if not mcp_url:
        print("❌ ERROR: MCP_SERVER_URL not set")
        return

    print("=" * 80)
    print("CONTEXT ACCUMULATION TEST: Repeated Operations")
    print("=" * 80)
    print(f"\n📡 MCP Server: {mcp_url}\n")

    # Test both approaches
    code_result = await test_code_execution_batch(mcp_url)
    traditional_result = await test_traditional_sequential(mcp_url)

    # Comparison
    print("\n\n" + "=" * 80)
    print("COMPARISON: Context Accumulation Over Multiple Operations")
    print("=" * 80)

    print(f"\n📊 Code Execution (batch in 1 code block):")
    print(f"   Total tokens: {code_result['total_tokens']:,}")
    print(f"   Duration: {code_result['duration']:.2f}s")
    print(f"   Strategy: Process all 10 customers in ONE code block")
    print(f"   Result: Only final summary in context")

    print(f"\n📊 Traditional (10 sequential calls):")
    print(f"   Total tokens: {traditional_result['total_tokens']:,}")
    print(f"   Duration: {traditional_result['duration']:.2f}s")
    print(f"   Strategy: 10 separate conversations + 1 summary")
    print(f"   Result: All 10 previous Q&A pairs in context by the end")

    savings = traditional_result['total_tokens'] - code_result['total_tokens']
    savings_pct = (savings / traditional_result['total_tokens'] * 100)

    print(f"\n💰 Token Savings:")
    print(f"   Saved: {savings:,} tokens ({savings_pct:.1f}%)")
    print(f"   Time difference: {abs(code_result['duration'] - traditional_result['duration']):.2f}s")

    print(f"\n🔍 Key Insight:")
    print(f"   Traditional approach accumulates context with EACH tool call")
    print(f"   Code execution keeps context minimal - only final summary")
    print(f"   Savings grow exponentially with more operations!")

    # Show accumulation
    print(f"\n📈 Context Growth (Traditional Approach):")
    for i, result in enumerate(traditional_result['results'][:5], 1):
        print(f"   After turn {i}: {result['cumulative_tokens']:,} tokens")
    print(f"   ...")
    print(f"   After turn 10: {traditional_result['results'][-1]['cumulative_tokens']:,} tokens")


if __name__ == "__main__":
    asyncio.run(main())
