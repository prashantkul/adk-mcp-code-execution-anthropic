"""Measure latency of DockerCodeExecutor."""

import os
import time
from dotenv import load_dotenv
from src.shared import DockerCodeExecutor
from google.genai.types import ExecutableCode

load_dotenv()

mcp_url = os.getenv('MCP_SERVER_URL')
executor = DockerCodeExecutor(allowed_url=mcp_url, timeout=30)

# Simple code that just prints
simple_code = ExecutableCode(code='print("Hello World")', language="PYTHON")

# Code that calls MCP
mcp_code = ExecutableCode(code=f"""
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

result = call_mcp("list_customers")
print(f"Found {{len(result)}} customers")
""", language="PYTHON")

print("🔧 Measuring Docker Code Executor Latency\n")

# Test 1: Simple print (baseline)
print("Test 1: Simple print statement (baseline)")
start = time.time()
result = executor.execute_code(simple_code)
duration = time.time() - start
print(f"   Duration: {duration:.2f}s")
print(f"   Output: {result.output}\n")

# Test 2: MCP call
print("Test 2: MCP call (list_customers)")
start = time.time()
result = executor.execute_code(mcp_code)
duration = time.time() - start
print(f"   Duration: {duration:.2f}s")
print(f"   Output: {result.output}\n")

# Test 3: Run 3 times to see variance
print("Test 3: Multiple runs (simple code)")
timings = []
for i in range(3):
    start = time.time()
    executor.execute_code(simple_code)
    duration = time.time() - start
    timings.append(duration)
    print(f"   Run {i+1}: {duration:.2f}s")

print(f"\n   Average: {sum(timings)/len(timings):.2f}s")
print(f"   Min: {min(timings):.2f}s")
print(f"   Max: {max(timings):.2f}s")
