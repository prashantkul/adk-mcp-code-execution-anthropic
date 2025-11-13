"""Compare token usage between traditional MCP agent and code execution agent."""

import asyncio
import os
import time
import json
from dotenv import load_dotenv
from google.genai import types
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from src.shared.docker_code_executor_optimized import DockerCodeExecutorOptimized
from src.shared import MCPClient

load_dotenv()


def estimate_tokens(text: str) -> int:
    """Rough token estimation (4 chars ≈ 1 token)."""
    return len(text) // 4


async def test_code_execution_agent(mcp_url: str, query: str):
    """Test the code execution approach and measure token usage."""
    print("\n" + "=" * 80)
    print("CODE EXECUTION AGENT (Optimized Approach)")
    print("=" * 80)

    # Create optimized executor
    executor = DockerCodeExecutorOptimized(
        allowed_url=mcp_url,
        timeout=30,
        image="mcp-executor-optimized:latest"
    )

    # Create agent
    agent = LlmAgent(
        name="code_exec_agent",
        model="gemini-2.0-flash",
        code_executor=executor,
        instruction=f"""You are a Python code execution agent with access to an MCP server.

When asked to interact with the MCP server, write concise Python code using urllib.

MCP URL: {mcp_url}

Use this helper function:
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

# Parse nested response:
response = call_mcp("tool_name", {{"arg": "value"}})
content = response.get("content", [])
for item in content:
    if item.get("type") == "text":
        data = json.loads(item["text"])
        print(data)  # Your result
```

Keep code concise. Only print final results.
""",
        description="Code execution agent"
    )

    runner = InMemoryRunner(agent=agent, app_name="code_exec_test")
    session = await runner.session_service.create_session(
        app_name="code_exec_test",
        user_id="test_user"
    )

    print(f"\n📝 Query: {query}\n")

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=query)]
    )

    start_time = time.time()
    code_executions = 0
    final_response = ""

    # Token counting
    context_tokens = estimate_tokens(agent.instruction)
    query_tokens = estimate_tokens(query)
    code_tokens = 0
    result_tokens = 0

    async for event in runner.run_async(
        user_id="test_user",
        session_id=session.id,
        new_message=content
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.executable_code:
                    code_executions += 1
                    code = part.executable_code.code
                    code_tokens += estimate_tokens(code)
                    print(f"🔧 Code Execution #{code_executions} ({estimate_tokens(code)} tokens)")

                elif part.code_execution_result:
                    output = part.code_execution_result.output or ""
                    result_tokens += estimate_tokens(output)
                    print(f"📊 Result: {part.code_execution_result.outcome} ({estimate_tokens(output)} tokens)")

        if event.is_final_response():
            if event.content and event.content.parts and event.content.parts[0].text:
                final_response = event.content.parts[0].text

    duration = time.time() - start_time

    total_tokens = context_tokens + query_tokens + code_tokens + result_tokens

    print(f"\n✅ Final Answer: {final_response}")
    print(f"\n📊 Token Usage Breakdown:")
    print(f"   - Context (instruction): {context_tokens:,} tokens")
    print(f"   - Query: {query_tokens:,} tokens")
    print(f"   - Generated code: {code_tokens:,} tokens")
    print(f"   - Execution results: {result_tokens:,} tokens")
    print(f"   - TOTAL: {total_tokens:,} tokens")
    print(f"\n⏱️  Duration: {duration:.2f}s")
    print(f"🔄 Code executions: {code_executions}")

    return {
        "approach": "code_execution",
        "total_tokens": total_tokens,
        "context_tokens": context_tokens,
        "query_tokens": query_tokens,
        "code_tokens": code_tokens,
        "result_tokens": result_tokens,
        "duration": duration,
        "executions": code_executions,
        "answer": final_response
    }


async def test_traditional_agent(mcp_url: str, query: str):
    """Test the traditional approach with direct MCP tool calling."""
    print("\n" + "=" * 80)
    print("TRADITIONAL AGENT (Direct Tool Calling)")
    print("=" * 80)

    # Fetch MCP tools
    mcp_client = MCPClient(mcp_url)
    tools = await mcp_client.list_tools()
    print(f"\n📡 Loaded {len(tools)} MCP tools from server")

    # Convert to function declarations
    function_declarations = []
    tool_schemas = []

    for tool in tools:
        function_decl = types.FunctionDeclaration(
            name=tool.name,
            description=tool.description or f"Execute {tool.name} operation",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    name: types.Schema(
                        type=_json_type_to_genai_type(prop.get("type", "string")),
                        description=prop.get("description", "")
                    )
                    for name, prop in tool.inputSchema.get("properties", {}).items()
                },
                required=tool.inputSchema.get("required", [])
            )
        )
        function_declarations.append(function_decl)
        tool_schemas.append(tool.model_dump())

    # Build instruction
    tool_list = "\n".join([
        f"  - {tool.name}: {tool.description or 'No description'}"
        for tool in tools
    ])

    instruction = f"""You are an AI assistant with access to MCP tools.

**Available Tools:**
{tool_list}

Call tools directly using function calling to answer user queries.
"""

    # Create agent with tools
    agent = LlmAgent(
        name="traditional_agent",
        model="gemini-2.0-flash",
        tools=function_declarations,
        instruction=instruction,
        description="Traditional MCP agent"
    )

    runner = InMemoryRunner(agent=agent, app_name="traditional_test")
    session = await runner.session_service.create_session(
        app_name="traditional_test",
        user_id="test_user"
    )

    print(f"\n📝 Query: {query}\n")

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=query)]
    )

    start_time = time.time()
    tool_calls = 0
    final_response = ""

    # Token counting
    tool_schemas_str = json.dumps(tool_schemas, indent=2)
    context_tokens = estimate_tokens(instruction) + estimate_tokens(tool_schemas_str)
    query_tokens = estimate_tokens(query)
    tool_call_tokens = 0
    tool_result_tokens = 0

    async for event in runner.run_async(
        user_id="test_user",
        session_id=session.id,
        new_message=content
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.function_call:
                    tool_calls += 1
                    tool_name = part.function_call.name
                    tool_args = dict(part.function_call.args) if part.function_call.args else {}

                    args_str = json.dumps(tool_args)
                    tool_call_tokens += estimate_tokens(args_str)

                    print(f"🔧 Tool Call #{tool_calls}: {tool_name} ({estimate_tokens(args_str)} tokens)")
                    print(f"   Arguments: {args_str}")

                    # Execute MCP tool
                    result = await mcp_client.call_tool(tool_name, tool_args)
                    result_str = json.dumps(result)
                    tool_result_tokens += estimate_tokens(result_str)

                    print(f"   Result: {result_str[:100]}... ({estimate_tokens(result_str)} tokens)\n")

                elif part.text:
                    final_response = part.text

        if event.is_final_response():
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        final_response = part.text

    await mcp_client.close()
    duration = time.time() - start_time

    total_tokens = context_tokens + query_tokens + tool_call_tokens + tool_result_tokens

    print(f"\n✅ Final Answer: {final_response}")
    print(f"\n📊 Token Usage Breakdown:")
    print(f"   - Context (instruction + tool schemas): {context_tokens:,} tokens")
    print(f"   - Query: {query_tokens:,} tokens")
    print(f"   - Tool calls: {tool_call_tokens:,} tokens")
    print(f"   - Tool results: {tool_result_tokens:,} tokens")
    print(f"   - TOTAL: {total_tokens:,} tokens")
    print(f"\n⏱️  Duration: {duration:.2f}s")
    print(f"🔄 Tool calls: {tool_calls}")

    return {
        "approach": "traditional",
        "total_tokens": total_tokens,
        "context_tokens": context_tokens,
        "query_tokens": query_tokens,
        "tool_call_tokens": tool_call_tokens,
        "tool_result_tokens": tool_result_tokens,
        "duration": duration,
        "tool_calls": tool_calls,
        "answer": final_response
    }


def _json_type_to_genai_type(json_type: str) -> types.Type:
    """Convert JSON Schema type to Google GenAI type."""
    type_mapping = {
        "string": types.Type.STRING,
        "integer": types.Type.INTEGER,
        "number": types.Type.NUMBER,
        "boolean": types.Type.BOOLEAN,
        "object": types.Type.OBJECT,
        "array": types.Type.ARRAY,
    }
    return type_mapping.get(json_type, types.Type.STRING)


async def main():
    mcp_url = os.getenv('MCP_SERVER_URL')
    if not mcp_url:
        print("❌ ERROR: MCP_SERVER_URL not set in .env file")
        return

    print("=" * 80)
    print("TOKEN USAGE COMPARISON: Traditional vs Code Execution")
    print("=" * 80)
    print(f"\n📡 MCP Server: {mcp_url}")

    # Test queries
    queries = [
        "Get customer with ID 2 and show their name and email",
        "List all customers and tell me how many there are",
    ]

    all_results = []

    for i, query in enumerate(queries, 1):
        print(f"\n\n{'#' * 80}")
        print(f"TEST {i}: {query}")
        print('#' * 80)

        # Test both approaches
        code_result = await test_code_execution_agent(mcp_url, query)
        traditional_result = await test_traditional_agent(mcp_url, query)

        all_results.append({
            "query": query,
            "code_execution": code_result,
            "traditional": traditional_result
        })

    # Summary
    print("\n\n" + "=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)

    for i, result in enumerate(all_results, 1):
        print(f"\n{'─' * 80}")
        print(f"Query {i}: {result['query']}")
        print('─' * 80)

        code = result['code_execution']
        trad = result['traditional']

        print(f"\nCode Execution Approach:")
        print(f"  Total tokens: {code['total_tokens']:,}")
        print(f"  Duration: {code['duration']:.2f}s")

        print(f"\nTraditional Approach:")
        print(f"  Total tokens: {trad['total_tokens']:,}")
        print(f"  Duration: {trad['duration']:.2f}s")

        token_savings = trad['total_tokens'] - code['total_tokens']
        savings_pct = (token_savings / trad['total_tokens'] * 100) if trad['total_tokens'] > 0 else 0

        print(f"\n💰 Savings:")
        print(f"  Tokens saved: {token_savings:,} ({savings_pct:.1f}%)")
        print(f"  Time difference: {abs(code['duration'] - trad['duration']):.2f}s")

    print("\n" + "=" * 80)
    print("\n✅ Comparison complete!")


if __name__ == "__main__":
    asyncio.run(main())
