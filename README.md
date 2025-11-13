# Code Execution with MCP using Google ADK

A comprehensive implementation demonstrating Anthropic's "Code Execution with MCP" pattern using Google ADK. Achieves **89.8% token reduction** for repeated operations by converting MCP tools into code-based APIs.

## 🎯 What This Demonstrates

Instead of calling MCP tools directly (loading all schemas in context and passing results through the model), we:

1. **Agent writes Python code** with inline HTTP calls to MCP server
2. **Code executes in optimized Docker sandbox** (79% faster than baseline)
3. **Intermediate results stay in code** - never enter LLM context
4. **Only final summary returned** to the agent

**Key Finding:** Context grows O(1) constant vs O(n²) quadratic in traditional approach

## 📊 Measured Results

### Single Operation
- Traditional: 411 tokens, 2.5s ⚡ **WINNER** (simpler is better)
- Code Execution: 658 tokens, 5s

### 10 Sequential Operations
- Traditional: **7,268 tokens processed**, 26s
- Code Execution: **744 tokens processed**, 9s ⚡
- **Savings: 89.8% tokens, 66% time**

> See [tests/TEST_RESULTS.md](tests/TEST_RESULTS.md) for complete analysis

## 🏗️ Architecture

### Two Approaches Implemented

**1. Traditional MCP Agent** (function calling via McpToolset)
```
User Query → LLM (with all tool schemas) → Function Call
                                              ↓
                                         McpToolset → HTTP → MCP Server
                                              ↓
                                         Result → LLM Context (grows!)
```

**2. Code Execution Agent** (this repository's focus)
```
User Query → LLM → Generates Python Code
                        ↓
                   DockerCodeExecutorOptimized
                        ↓
                   Code makes HTTP calls → MCP Server
                        ↓
                   Process ALL results in code
                        ↓
                   Return ONLY summary → LLM
```

**Key Difference**: Traditional reprocesses context on each tool call (quadratic cost), Code Execution keeps context constant.

## 📋 Prerequisites

- Python 3.11+
- Google Cloud account with API key
- Running MCP server (exposed via ngrok)
- UV package manager (or pip)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Using UV (recommended)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Or using pip
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Setup Environment

Create `.env` file:
```bash
MCP_SERVER_URL=https://your-ngrok-url.ngrok.io
GOOGLE_API_KEY=your_google_api_key_here
```

### 3. Run Demo

```bash
cd mcp_adk_prototype
python src/demo.py
```

## 🧪 Running Tests

### Quick Comparison (Most Important!)
```bash
# Demonstrates the 89.8% token reduction
python tests/test_repeated_operations.py
```

### All Tests
```bash
# Individual agents
python tests/test_programmatic.py              # Code execution agent
python tests/test_traditional_programmatic.py  # Traditional MCP agent

# Performance comparisons
python tests/test_token_comparison_fixed.py    # Single operation comparison
python tests/test_repeated_operations.py        # Sequential operations (⭐ key test)

# Run all tests
pytest tests/ -v
```

### Test Results
See comprehensive analysis in:
- **[tests/TEST_RESULTS.md](tests/TEST_RESULTS.md)** - Complete performance analysis
- **[tests/README.md](tests/README.md)** - Test suite documentation

**Key Findings:**
- **Crossover point**: 3-5 operations (Traditional better below, Code Execution better above)
- **Context growth**: Traditional O(n²), Code Execution O(1)
- **Use Traditional when**: Simple queries, <20 tools, latency critical
- **Use Code Execution when**: Complex workflows, 100+ tools, cost critical

## ⚡ Performance Optimization

### DockerCodeExecutorOptimized (Current Implementation)

**Problem**: BuiltInCodeExecutor has NO network access (can't reach MCP server)

**Solution**: Custom Docker executor with pre-built image

**Results**:
- **Baseline**: 1.65s per execution (pip install on every run)
- **Optimized**: 0.34s per execution ⚡
- **Improvement**: **79% faster**

```dockerfile
# Dockerfile.executor-optimized
FROM python:3.11-slim
RUN pip install --no-cache-dir urllib3  # Pre-installed!
RUN useradd -m -u 1000 sandbox
USER sandbox
WORKDIR /workspace
```

Build:
```bash
docker build -f Dockerfile.executor-optimized -t mcp-executor-optimized:latest .
```

## 🔒 Security Considerations

### Current (DockerCodeExecutorOptimized)
- ✅ Docker container isolation
- ✅ Network restricted to MCP server URL only
- ✅ Non-root user execution
- ✅ 30-second timeout
- ⚠️ Suitable for development/testing

### Production (GkeCodeExecutor)
For production, upgrade to GKE with gVisor:
```python
from google.adk.code_executors import GkeCodeExecutor

executor = GkeCodeExecutor(
    namespace="agent-sandbox",
    timeout_seconds=600,
    cpu_limit="1000m",
    mem_limit="2Gi"
)
```

Additional benefits:
- 🔒 Kernel-level isolation (gVisor)
- 🔒 Syscall filtering
- 🔒 Resource limits
- 🔒 Ephemeral pods with auto-cleanup

## 📚 Key Concepts

### Traditional Tool Calling (McpToolset)
```python
# Each operation is a separate LLM invocation
# Context grows with EVERY call

Turn 1: User: "Get customer 1"
  → LLM: function_call(get_customer, {id: 1})
  → Result in context: 315 tokens

Turn 2: User: "Get customer 2"
  → Previous context STILL THERE: 315 tokens
  → LLM: function_call(get_customer, {id: 2})
  → Result in context: 407 tokens (+92)

... continues growing ...

Turn 10: Context = 1,140 tokens
Total processed: 7,268 tokens (quadratic!)
```

### Code Execution with MCP (This Implementation)
```python
# Agent writes code ONCE with inline HTTP calls
# ALL operations happen in the code

code = """
import urllib.request
import json

MCP_URL = "https://your-ngrok-url/mcp"

def call_mcp(tool_name, arguments):
    # ... HTTP helper ...
    pass

# Process ALL 10 customers in code
for customer_id in range(1, 11):
    response = call_mcp("get_customer", {"customer_id": customer_id})
    # Process in code, not in LLM context!

print("Active: 8, Disabled: 2")  # Only this returns
"""

# Result: 744 tokens total (constant!)
```

**Key Insight**: Intermediate results (all 10 customer records) NEVER enter LLM context!

## 🎓 Learning Outcomes

After running this implementation, you'll understand:

1. **Why code execution isn't universally better** - Traditional wins for simple queries
2. **The quadratic cost problem** - O(n²) processing in traditional vs O(1) in code execution
3. **The crossover point** - 3-5 operations where code execution becomes advantageous
4. **Optimizing Docker executors** - Pre-built images achieve 79% speedup
5. **Two approaches to MCP integration**:
   - Traditional: McpToolset with function calling
   - Code Execution: Inline HTTP calls in generated Python code
6. **When to use each approach** - Based on operation count, tool count, and latency requirements

## 🔧 Extending the Prototype

### Add More MCP Servers

1. Update `tool_generator.py` to handle multiple servers
2. Generate separate modules (e.g., `mcp_tools/salesforce.py`)
3. Update agent instructions with new capabilities

### Deploy to GKE

1. Set up GKE cluster with gVisor
2. Create service account with RBAC permissions
3. Switch to `GkeCodeExecutor`
4. Configure resource limits

### Add Monitoring

```python
import google.cloud.logging

# Log all code executions
# Track token usage
# Monitor execution times
# Alert on errors
```

## 📖 References

- [Anthropic: Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [Model Context Protocol](https://modelcontextprotocol.io/)

## 🤝 Contributing

This is a research prototype. Feel free to extend and improve!

## 📝 License

MIT License - feel free to use for research and education.
