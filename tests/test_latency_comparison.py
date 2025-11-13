"""Compare latency between original and optimized Docker executors."""

import os
import time
from dotenv import load_dotenv
from src.shared.docker_code_executor import DockerCodeExecutor
from src.shared.docker_code_executor_optimized import DockerCodeExecutorOptimized
from google.genai.types import ExecutableCode

load_dotenv()

mcp_url = os.getenv('MCP_SERVER_URL')

# Initialize both executors
original_executor = DockerCodeExecutor(allowed_url=mcp_url, timeout=30)
optimized_executor = DockerCodeExecutorOptimized(allowed_url=mcp_url, timeout=30)

# Test code
simple_code = ExecutableCode(code='print("Hello World")', language="PYTHON")

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

print("🔧 Latency Comparison: Original vs Optimized\n")
print("="*60)

# Test 1: Simple code
print("\nTest 1: Simple print statement")
print("-"*60)

print("Original executor:")
timings_original = []
for i in range(3):
    start = time.time()
    original_executor.execute_code(simple_code)
    duration = time.time() - start
    timings_original.append(duration)
    print(f"   Run {i+1}: {duration:.2f}s")
avg_original = sum(timings_original) / len(timings_original)
print(f"   Average: {avg_original:.2f}s\n")

print("Optimized executor:")
timings_optimized = []
for i in range(3):
    start = time.time()
    optimized_executor.execute_code(simple_code)
    duration = time.time() - start
    timings_optimized.append(duration)
    print(f"   Run {i+1}: {duration:.2f}s")
avg_optimized = sum(timings_optimized) / len(timings_optimized)
print(f"   Average: {avg_optimized:.2f}s\n")

improvement = ((avg_original - avg_optimized) / avg_original) * 100
print(f"⚡ Speedup: {improvement:.1f}% faster ({avg_original:.2f}s → {avg_optimized:.2f}s)")

# Test 2: MCP call
print("\n" + "="*60)
print("\nTest 2: MCP call (list_customers)")
print("-"*60)

print("Original executor:")
start = time.time()
result = original_executor.execute_code(mcp_code)
duration_original = time.time() - start
print(f"   Duration: {duration_original:.2f}s")
print(f"   Output: {result.output}\n")

print("Optimized executor:")
start = time.time()
result = optimized_executor.execute_code(mcp_code)
duration_optimized = time.time() - start
print(f"   Duration: {duration_optimized:.2f}s")
print(f"   Output: {result.output}\n")

improvement_mcp = ((duration_original - duration_optimized) / duration_original) * 100
print(f"⚡ Speedup: {improvement_mcp:.1f}% faster ({duration_original:.2f}s → {duration_optimized:.2f}s)")

print("\n" + "="*60)
print("\n✅ Optimization Summary:")
print(f"   Simple execution: {improvement:.1f}% faster")
print(f"   MCP calls: {improvement_mcp:.1f}% faster")
print(f"   Absolute savings: ~{(avg_original - avg_optimized):.2f}s per execution")
