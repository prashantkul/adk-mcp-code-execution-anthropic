# Project Architecture

This document describes the refactored directory structure following Google ADK best practices.

## Directory Structure

```
src/
├── __init__.py
├── demo.py                          # Main demonstration script
├── comparison_demo.py               # Token comparison demo
│
├── mcp_code_agent/                  # Code Execution Agent
│   ├── __init__.py                  # Exports MCPCodeAgent
│   └── agent.py                     # Main agent implementation
│
├── traditional_mcp_agent/           # Traditional Direct Calling Agent
│   ├── __init__.py                  # Exports TraditionalMCPAgent
│   └── agent.py                     # Traditional agent for comparison
│
└── shared/                          # Shared utilities
    ├── __init__.py                  # Exports shared components
    ├── mcp_client.py                # MCP JSON-RPC 2.0 client
    └── tool_generator.py            # Python wrapper generator

mcp_tools/                           # Auto-generated tool wrappers
├── __init__.py
└── customer.py                      # Generated MCP tool wrappers

tests/                               # Test suite
└── ...

examples/                            # Usage examples
└── ...
```

## Component Overview

### 1. MCP Code Agent (`src/mcp_code_agent/`)

The main agent that implements the "Code Execution with MCP" pattern.

**Key Features:**
- Uses Google ADK's `BuiltInCodeExecutor`
- Generates Python wrapper modules from MCP tools
- Achieves 93-98% token reduction
- Agent writes Python code to orchestrate tools

**Usage:**
```python
from mcp_code_agent import MCPCodeAgent

agent = MCPCodeAgent(mcp_server_url)
await agent.setup()
result = await agent.run_task("List all customers from California")
```

**Files:**
- `agent.py` - Main `MCPCodeAgent` class implementation
- `__init__.py` - Package exports

---

### 2. Traditional MCP Agent (`src/traditional_mcp_agent/`)

Traditional agent for comparison that calls MCP tools directly through function calling.

**Key Features:**
- Registers MCP tools as ADK function declarations
- Calls tools one at a time through model context
- Used for token usage comparison

**Usage:**
```python
from traditional_mcp_agent import TraditionalMCPAgent

agent = TraditionalMCPAgent(mcp_server_url)
await agent.setup()
result, stats = await agent.run_task("List all customers")
```

**Files:**
- `agent.py` - Main `TraditionalMCPAgent` class
- `__init__.py` - Package exports

---

### 3. Shared Utilities (`src/shared/`)

Common utilities used by both agents.

#### MCPClient (`mcp_client.py`)

HTTP client for communicating with MCP servers via JSON-RPC 2.0.

**Features:**
- JSON-RPC 2.0 protocol implementation
- Server-Sent Events (SSE) response handling
- Tool listing and calling

**Usage:**
```python
from shared import MCPClient

client = MCPClient("https://your-mcp-server.com/mcp")
tools = await client.list_tools()
result = await client.call_tool("tool_name", {"arg": "value"})
```

#### MCPToolGenerator (`tool_generator.py`)

Generates Python wrapper modules from MCP tool schemas.

**Features:**
- Converts MCP JSON Schema → Python type hints
- Generates async/await wrapper functions
- Creates importable Python modules
- Follows JSON-RPC 2.0 protocol

**Usage:**
```python
from shared import MCPToolGenerator

generator = MCPToolGenerator(mcp_server_url)
module_code = generator.generate_wrapper_module(tools, "customer")
generator.write_module_to_file(module_code, Path("mcp_tools/customer.py"))
```

**Files:**
- `mcp_client.py` - MCP client implementation
- `tool_generator.py` - Wrapper generator
- `__init__.py` - Package exports

---

## Design Rationale

### Why This Structure?

1. **Agent Isolation:** Each agent has its own directory following ADK conventions
   - Clear separation of concerns
   - Easy to add new agent types
   - Self-contained with `agent.py` and `__init__.py`

2. **Shared Utilities:** Common code in `shared/` module
   - Avoids duplication
   - Single source of truth for MCP protocol
   - Easier to maintain and test

3. **Clean Imports:** Simplified import paths
   ```python
   from mcp_code_agent import MCPCodeAgent
   from traditional_mcp_agent import TraditionalMCPAgent
   from shared import MCPClient, MCPToolGenerator
   ```

4. **Scalability:** Easy to extend
   - Add new agents: create new directory under `src/`
   - Add new utilities: add to `src/shared/`
   - Each component is independently testable

---

## Import Paths

### From Root Directory Scripts

Scripts in the project root (like `test_ngrok_mcp.py`):

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from shared import MCPClient
from mcp_code_agent import MCPCodeAgent
```

### From src/ Directory Scripts

Scripts in `src/` (like `demo.py`, `comparison_demo.py`):

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp_code_agent import MCPCodeAgent
from traditional_mcp_agent import TraditionalMCPAgent
```

### Internal Imports (Within Agents)

From `src/mcp_code_agent/agent.py` or `src/traditional_mcp_agent/agent.py`:

```python
from ..shared import MCPClient, MCPToolGenerator
```

---

## Running the Project

### Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Set up environment
cp .env.example .env
# Edit .env with your MCP_SERVER_URL and GOOGLE_API_KEY

# Run main demo
python src/demo.py

# Run comparison demo
python src/comparison_demo.py

# Test MCP connection
python test_ngrok_mcp.py

# Test tool generator
python test_generator_fix.py
```

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Test specific components
python test_ngrok_mcp.py          # MCP client
python test_generator_fix.py      # Tool generator
python test_wrapper_direct.py     # Generated wrappers
```

---

## Adding a New Agent

To add a new agent type:

1. **Create agent directory:**
   ```bash
   mkdir src/my_new_agent
   ```

2. **Create agent.py:**
   ```python
   """My new agent implementation."""
   from ..shared import MCPClient, MCPToolGenerator

   class MyNewAgent:
       def __init__(self, mcp_server_url: str):
           self.mcp_client = MCPClient(mcp_server_url)
           # ... your implementation
   ```

3. **Create __init__.py:**
   ```python
   """My new agent package."""
   from .agent import MyNewAgent

   __all__ = ["MyNewAgent"]
   ```

4. **Use in demos:**
   ```python
   from my_new_agent import MyNewAgent

   agent = MyNewAgent(mcp_server_url)
   await agent.setup()
   ```

---

## Migration Notes

### Changes from Previous Structure

**Old Structure:**
```
src/
  adk_agent.py
  traditional_agent.py
  mcp_client.py
  tool_generator.py
```

**New Structure:**
```
src/
  mcp_code_agent/
    agent.py          # (was adk_agent.py)
  traditional_mcp_agent/
    agent.py          # (was traditional_agent.py)
  shared/
    mcp_client.py
    tool_generator.py
```

### Import Changes

**Old:**
```python
from adk_agent import MCPCodeAgent
from traditional_agent import TraditionalMCPAgent
from mcp_client import MCPClient
```

**New:**
```python
from mcp_code_agent import MCPCodeAgent
from traditional_mcp_agent import TraditionalMCPAgent
from shared import MCPClient
```

---

## Best Practices

1. **Agent Naming:** Use descriptive names ending in `_agent`
2. **File Structure:** Always include `agent.py` and `__init__.py`
3. **Shared Code:** Put reusable utilities in `src/shared/`
4. **Testing:** Test each component independently
5. **Documentation:** Update this file when adding new components

---

## References

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Anthropic: Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
