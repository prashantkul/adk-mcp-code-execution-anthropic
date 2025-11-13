# Test Suite

This directory contains all tests for the MCP Code Execution project, comparing Traditional MCP (function calling) vs Code Execution approaches.

## Test Categories

### 1. Core Functionality Tests

**test_mcp_client.py**
- Tests basic MCP client connection and tool listing
- Validates JSON-RPC protocol communication
- Verifies SSE format handling

**test_mcp_connection.py**
- Tests MCP server connectivity
- Validates tool discovery
- Checks error handling

**test_tool_generator.py**
- Tests auto-generation of Python wrappers from MCP schemas
- Validates type conversions (JSON Schema → Python types)
- Checks function signature generation

### 2. Code Execution Tests

**test_docker_executor.py**
- Tests DockerCodeExecutorOptimized
- Validates Docker container execution
- Checks network access restrictions
- Verifies timeout handling

**test_programmatic.py**
- Tests MCP Code Agent programmatically (outside ADK web)
- Validates code generation for MCP calls
- Tests with multiple queries

**test_traditional_programmatic.py**
- Tests Traditional MCP Agent programmatically
- Validates McpToolset integration
- Tests function calling approach

### 3. Performance & Comparison Tests

**test_token_comparison.py**
- Compares token usage between Traditional and Code Execution
- Tests with single operations
- **Result**: Traditional wins for 1-2 operations

**test_token_comparison_fixed.py**
- Fixed version using proper McpToolset
- More accurate token counting
- **Result**: Similar findings, Traditional better for simple queries

**test_repeated_operations.py** ⭐ **MOST IMPORTANT**
- Tests context accumulation with 10 sequential operations
- Demonstrates quadratic processing cost in Traditional approach
- **Result**: Code Execution achieves 89.8% token reduction

**test_latency.py**
- Measures execution time for code execution
- Benchmarks Docker container startup
- Tests optimization improvements

**test_latency_comparison.py**
- Compares latency between approaches
- Traditional: ~2.5s per operation
- Code Execution: ~5s first call, ~9s for 10 operations vs 26s traditional

### 4. Integration Tests

**test_integration.py**
- End-to-end integration testing
- Tests complete workflow from query to response
- Validates both agents work together

**test_agent_fixed.py**
- Tests agent setup and configuration
- Validates instruction building
- Checks tool schema conversion

### 5. Development Tests

**test_ngrok_mcp.py**
- Tests ngrok tunnel connectivity
- Validates external MCP server access
- Used during development setup

**test_wrapper_direct.py**
- Tests direct MCP wrapper execution
- Validates httpx-based wrappers
- Quick validation of generated code

**test_generator_fix.py**
- Tests fixes for tool generator
- Validates SSE format handling
- Checks JSON parsing edge cases

## Running Tests

### Individual Tests

```bash
# Test code execution approach
python tests/test_programmatic.py

# Test traditional approach
python tests/test_traditional_programmatic.py

# Run comparison (most important!)
python tests/test_repeated_operations.py
```

### All Tests

```bash
# Run all tests
pytest tests/

# Run specific category
pytest tests/test_token*.py
pytest tests/test_*comparison*.py
```

## Key Test Results

### Single Operation
- **Traditional**: 339 tokens, 2.5s ⚡ WINNER
- **Code Execution**: 658 tokens, 5s

### 10 Sequential Operations
- **Traditional**:
  - Final context: 1,158 tokens
  - **Total processed: 7,268 tokens**
  - Duration: 26s

- **Code Execution**:
  - Final context: 744 tokens
  - **Total processed: 744 tokens** ⚡ WINNER
  - Duration: 9s
  - **Savings: 89.8% tokens, 66% time**

### Context Growth Pattern
- **Traditional**: Linear context size, Quadratic processing cost O(n²)
- **Code Execution**: Constant O(1)

## Environment Requirements

```bash
# Required environment variables
MCP_SERVER_URL=https://your-ngrok-url/mcp

# Python dependencies
pip install -r requirements.txt

# Docker (for code execution tests)
docker build -f Dockerfile.executor-optimized -t mcp-executor-optimized:latest .
```

## Test Data

All tests use the same MCP server with 6 customer management tools:
- get_customer
- list_customers
- add_customer
- update_customer
- disable_customer
- activate_customer

## Interpreting Results

### Token Metrics
- **Context size**: What's loaded in LLM context at a given moment
- **Total processed**: Cumulative tokens across all LLM invocations
- **Processing cost**: Total processed × token price = actual cost

### When Each Approach Wins
- **Traditional**: 1-3 tool calls, <20 tools, latency-critical
- **Code Execution**: 10+ tool calls, 100+ tools, cost-critical, complex workflows

## Contributing New Tests

When adding tests:
1. Name clearly: `test_<feature>_<variant>.py`
2. Add docstring explaining what it tests
3. Include expected results in comments
4. Update this README with results
5. Add to appropriate category above
