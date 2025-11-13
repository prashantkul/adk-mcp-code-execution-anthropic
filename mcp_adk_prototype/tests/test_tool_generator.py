"""Tests for tool generator."""

import pytest
from pathlib import Path
from src.tool_generator import MCPToolGenerator


@pytest.fixture
def generator():
    """Create a tool generator for testing."""
    return MCPToolGenerator("https://test.ngrok.io")


def test_python_type_from_json_schema(generator):
    """Test JSON schema to Python type conversion."""
    assert generator._python_type_from_json_schema({"type": "string"}) == "str"
    assert generator._python_type_from_json_schema({"type": "integer"}) == "int"
    assert generator._python_type_from_json_schema({"type": "number"}) == "float"
    assert generator._python_type_from_json_schema({"type": "boolean"}) == "bool"
    assert generator._python_type_from_json_schema({"type": "object"}) == "Dict[str, Any]"
    assert generator._python_type_from_json_schema({"type": "array"}) == "List[Any]"
    assert generator._python_type_from_json_schema({}) == "Any"


def test_generate_function(generator):
    """Test function generation from tool schema."""
    tool = {
        "name": "get_customer",
        "description": "Get customer details",
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "The customer ID"
                }
            },
            "required": ["customer_id"]
        }
    }

    func_code = generator._generate_function(tool)

    assert "async def get_customer" in func_code
    assert "customer_id: str" in func_code
    assert "Get customer details" in func_code
    assert "await _call_mcp_tool('get_customer', arguments)" in func_code


def test_generate_wrapper_module(generator):
    """Test complete module generation."""
    tools = [
        {
            "name": "get_customer",
            "description": "Get customer details",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"}
                },
                "required": ["customer_id"]
            }
        },
        {
            "name": "list_customers",
            "description": "List all customers",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        }
    ]

    module_code = generator.generate_wrapper_module(tools, "customer")

    assert "import httpx" in module_code
    assert "MCP_SERVER_URL = \"https://test.ngrok.io\"" in module_code
    assert "async def get_customer" in module_code
    assert "async def list_customers" in module_code
    assert "async def _call_mcp_tool" in module_code


def test_write_module_to_file(generator, tmp_path):
    """Test writing module to file."""
    module_code = "# Test module\nprint('Hello')"
    output_path = tmp_path / "test_module.py"

    generator.write_module_to_file(module_code, output_path)

    assert output_path.exists()
    assert output_path.read_text() == module_code


def test_generate_init_file(generator, tmp_path):
    """Test generating __init__.py file."""
    generator.generate_init_file(tmp_path)

    init_path = tmp_path / "__init__.py"
    assert init_path.exists()
    content = init_path.read_text()
    assert "MCP Tools Package" in content
    assert "__version__" in content
