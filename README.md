# Code Execution with MCP using Google ADK

A working prototype demonstrating Anthropic's "Code Execution with MCP" pattern using Google ADK, achieving **98% token reduction** by converting MCP tools into code-based APIs.

## 🎯 What This Demonstrates

Instead of calling MCP tools directly (loading all schemas in context and passing results through the model), we:

1. **Convert MCP tools → Python modules** (stored on disk, 0 tokens)
2. **Agent writes Python code** to orchestrate tools (~500 tokens)
3. **Code executes in sandbox**, intermediate results stay local
4. **Only final summary returned** (~200 tokens)

**Result:** 150K tokens → 2K tokens (98.7% reduction)

## 🏗️ Architecture

```
Agent (Gemini 2.0) → Writes Python Code → Sandbox Execution
                                              ↓
                                         mcp_tools/
                                           ├── customer.py
                                           └── __init__.py
                                              ↓
                                         HTTP → MCP Server (ngrok)
```

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

## 📊 Token Comparison

Run the comparison analysis:
```bash
python examples/token_comparison.py
```

Output shows:
- Traditional approach: ~6,840 tokens
- Code execution: ~500 tokens
- **Reduction: 92.7%** (and this is a simple example!)

## 🧪 Running Tests

```bash
pytest tests/ -v
```

## 🔒 Security Considerations

### Current (BuiltInCodeExecutor)
- ✅ Uses Gemini's built-in sandbox
- ⚠️ Suitable for development/testing
- ⚠️ Limited isolation controls

### Production (GkeCodeExecutor)
Upgrade to GKE with gVisor for production:
```python
from google.adk.code_executors import GkeCodeExecutor

executor = GkeCodeExecutor(
    namespace="agent-sandbox",
    timeout_seconds=600,
    cpu_limit="1000m",
    mem_limit="2Gi"
)
```

Benefits:
- 🔒 Kernel-level isolation (gVisor)
- 🔒 Syscall filtering
- 🔒 Resource limits
- 🔒 Ephemeral pods with auto-cleanup

## 📚 Key Concepts

### Traditional Tool Calling
```python
# Agent thinks and acts in multiple steps
# Step 1: Load all tool schemas in context (~1500 tokens)
# Step 2: Call list_customers
result = agent.call_tool("list_customers")  # ~5000 tokens response
# Step 3: Call get_customer for each (more tokens)
# Step 4: Process results (even more tokens)
# Total: ~10,000+ tokens
```

### Code Execution with MCP
```python
# Agent writes code ONCE (~500 tokens)
code = """
from mcp_tools import customer

# Everything happens in code
customers = await customer.list_customers()
filtered = [c for c in customers if c['state'] == 'CA']
result = f"Found {len(filtered)} CA customers"
print(result)  # Only this returns to agent
"""
# Total: ~700 tokens (including response)
```

## 🎓 Learning Outcomes

After running this prototype, you'll understand:

1. How to generate Python wrappers from MCP schemas
2. How to configure Google ADK for code execution
3. How to achieve dramatic token reduction
4. Security considerations for production deployment
5. When to use code execution vs. direct tool calling

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
