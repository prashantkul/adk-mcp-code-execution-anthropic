"""Test DockerCodeExecutor with actual MCP call."""

import os
from dotenv import load_dotenv
from src.shared import DockerCodeExecutor
from google.genai.types import ExecutableCode

load_dotenv()

mcp_url = os.getenv('MCP_SERVER_URL')
print(f"Testing DockerCodeExecutor with MCP URL: {mcp_url}\n")

# Initialize executor
executor = DockerCodeExecutor(allowed_url=mcp_url, timeout=30)
print("✅ DockerCodeExecutor initialized\n")

# Create test code that calls the MCP server
test_code = f"""
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
        # Handle SSE format: extract JSON after "data: " prefix
        if text.startswith("data: "):
            lines = text.split('\\n')
            for line in lines:
                if line.startswith("data: "):
                    text = line[6:]  # Remove "data: " prefix
                    break
        data = json.loads(text)
        return data.get("result", {{}})

# Test: List customers
try:
    print("Calling list_customers...")
    result = call_mcp("list_customers")
    print(f"Success! Found {{len(result)}} customers")
    if result:
        print(f"First customer: {{result[0]}}")
except Exception as e:
    print(f"Error: {{e}}")
"""

print("🔧 Executing test code in Docker container...\n")
executable = ExecutableCode(code=test_code, language="PYTHON")
result = executor.execute_code(executable)

print(f"📊 Execution Result:")
print(f"   Outcome: {result.outcome}")
print(f"   Output:\n{result.output}\n")

if result.outcome.name == "OUTCOME_OK":
    print("✅ SUCCESS! Docker executor can access MCP server and execute code!")
else:
    print("❌ FAILED: Check output above for errors")
