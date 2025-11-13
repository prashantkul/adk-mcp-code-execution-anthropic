"""Integration tests for the MCP ADK prototype."""

import pytest
from pathlib import Path
from src.tool_generator import MCPToolGenerator


@pytest.mark.integration
def test_full_module_generation_and_import(tmp_path):
    """Test generating a module and verifying it can be imported (syntax check)."""
    generator = MCPToolGenerator("https://test.ngrok.io")

    tools = [
        {
            "name": "get_customer",
            "description": "Get customer by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Customer identifier"
                    }
                },
                "required": ["customer_id"]
            }
        },
        {
            "name": "create_customer",
            "description": "Create a new customer",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Customer name"},
                    "email": {"type": "string", "description": "Customer email"},
                    "age": {"type": "integer", "description": "Customer age"}
                },
                "required": ["name", "email"]
            }
        }
    ]

    # Generate module
    module_code = generator.generate_wrapper_module(tools, "customer")

    # Verify structure
    assert "async def get_customer(customer_id: str)" in module_code
    assert "async def create_customer(name: str, email: str, age: Optional[int] = None)" in module_code
    assert "async def _call_mcp_tool" in module_code
    assert "MCP_SERVER_URL" in module_code

    # Verify it's valid Python (syntax check)
    try:
        compile(module_code, "<string>", "exec")
    except SyntaxError as e:
        pytest.fail(f"Generated module has syntax errors: {e}")


@pytest.mark.integration
def test_token_comparison_calculations():
    """Test that token comparison calculations are reasonable."""
    from examples.token_comparison import calculate_traditional_tokens, calculate_code_execution_tokens

    traditional = calculate_traditional_tokens()
    code_exec = calculate_code_execution_tokens()

    # Traditional should be significantly higher
    assert traditional["total"] > code_exec["total"]

    # Code execution should have 0 schema tokens
    assert code_exec["tool_schemas"] == 0

    # Calculate reduction
    reduction = ((traditional["total"] - code_exec["total"]) / traditional["total"]) * 100

    # Should show significant reduction (>80%)
    assert reduction > 80, f"Expected >80% reduction, got {reduction:.1f}%"
