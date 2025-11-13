"""Generates Python wrapper modules from MCP tool schemas."""

from typing import List, Dict, Any
from pathlib import Path
import json
from textwrap import dedent, indent


class MCPToolGenerator:
    """Converts MCP tool schemas into importable Python modules."""

    def __init__(self, mcp_server_url: str):
        """
        Initialize tool generator.

        Args:
            mcp_server_url: URL of the MCP server for the wrappers to call
        """
        self.mcp_server_url = mcp_server_url

    def generate_wrapper_module(
        self,
        tools: List[Dict[str, Any]],
        module_name: str = "customer"
    ) -> str:
        """
        Generate a complete Python module with wrapper functions for MCP tools.

        Args:
            tools: List of MCP tool definitions
            module_name: Name of the module (e.g., 'customer')

        Returns:
            Python module source code as string
        """
        functions = []

        for tool in tools:
            func_code = self._generate_function(tool)
            functions.append(func_code)

        module_code = dedent(f'''
            """
            Auto-generated MCP tool wrappers for {module_name} operations.

            This module provides Python functions that call the MCP server.
            Generated from MCP tool schemas to enable code-based tool orchestration.
            """

            import httpx
            import json
            from typing import Dict, Any, Optional, List


            # MCP Server Configuration
            MCP_SERVER_URL = "{self.mcp_server_url}"


            async def _call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Any:
                """
                Internal function to call MCP tools via JSON-RPC 2.0.

                Args:
                    tool_name: Name of the MCP tool
                    arguments: Tool arguments

                Returns:
                    Tool execution result
                """
                request_id = 1  # Simple counter for this execution

                # Build JSON-RPC 2.0 request
                json_rpc_request = {{
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {{
                        "name": tool_name,
                        "arguments": arguments
                    }},
                    "id": request_id
                }}

                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        MCP_SERVER_URL,
                        json=json_rpc_request,
                        headers={{"Content-Type": "application/json"}}
                    )
                    response.raise_for_status()

                    # Handle SSE (Server-Sent Events) format
                    response_text = response.text

                    # Check if response is SSE format (starts with "data: ")
                    if response_text.startswith("data: "):
                        # Extract JSON from SSE format
                        lines = response_text.split('\\n')
                        for line in lines:
                            if line.startswith("data: "):
                                json_str = line[6:]  # Remove "data: " prefix
                                data = json.loads(json_str)
                                break
                        else:
                            # Fallback: try to parse as regular JSON
                            data = response.json()
                    else:
                        # Regular JSON response
                        data = response.json()

                    # Handle JSON-RPC error
                    if "error" in data:
                        raise Exception(f"MCP Error: {{data['error']}}")

                    # Extract result from JSON-RPC response
                    result = data.get("result", {{}})

                    # MCP tools/call returns result with content array
                    if "content" in result:
                        content = result["content"]
                        if content and len(content) > 0:
                            return content[0].get("text", content[0])
                        return content

                    return result


        ''')

        # Add all generated functions
        for func in functions:
            module_code += "\n" + func + "\n"

        return module_code.strip()

    def _generate_function(self, tool: Dict[str, Any]) -> str:
        """
        Generate a single Python function from an MCP tool definition.

        Args:
            tool: MCP tool definition

        Returns:
            Python function source code
        """
        name = tool['name']
        description = tool.get('description', f"Execute {name} operation")
        schema = tool.get('inputSchema', {})
        properties = schema.get('properties', {})
        required = schema.get('required', [])

        # Build function parameters
        params = []
        for param_name, param_schema in properties.items():
            param_type = self._python_type_from_json_schema(param_schema)
            is_required = param_name in required

            if is_required:
                params.append(f"{param_name}: {param_type}")
            else:
                params.append(f"{param_name}: Optional[{param_type}] = None")

        params_str = ", ".join(params) if params else ""

        # Build docstring
        docstring_lines = [f'"""{description}']
        if params:
            docstring_lines.append("\n    Args:")
            for param_name, param_schema in properties.items():
                param_desc = param_schema.get('description', param_name)
                docstring_lines.append(f"        {param_name}: {param_desc}")
        docstring_lines.append('    """')
        docstring = "\n".join(docstring_lines)

        # Build function body
        func_code = dedent(f'''
            async def {name}({params_str}) -> Any:
        ''').rstrip()

        # Add docstring with proper indentation
        func_code += "\n    " + docstring.replace("\n", "\n    ")

        # Add argument building
        func_code += "\n    arguments = {}"

        for param_name in properties.keys():
            func_code += f"\n    if {param_name} is not None:"
            func_code += f"\n        arguments['{param_name}'] = {param_name}"

        func_code += f"\n    \n    return await _call_mcp_tool('{name}', arguments)"

        return func_code

    def _python_type_from_json_schema(self, schema: Dict[str, Any]) -> str:
        """Convert JSON Schema type to Python type hint."""
        schema_type = schema.get('type', 'Any')

        type_mapping = {
            'string': 'str',
            'integer': 'int',
            'number': 'float',
            'boolean': 'bool',
            'object': 'Dict[str, Any]',
            'array': 'List[Any]',
        }

        return type_mapping.get(schema_type, 'Any')

    def write_module_to_file(self, module_code: str, output_path: Path):
        """
        Write generated module code to a file.

        Args:
            module_code: Generated Python code
            output_path: Path to write the module file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(module_code)
        print(f"✓ Generated module: {output_path}")

    def generate_init_file(self, output_dir: Path):
        """Generate __init__.py for the mcp_tools package."""
        init_code = dedent('''
            """
            MCP Tools Package

            Auto-generated Python wrappers for MCP server tools.
            Import these modules to interact with MCP tools via code execution.
            """

            __version__ = "0.1.0"
        ''')

        init_path = output_dir / "__init__.py"
        init_path.write_text(init_code.strip())
        print(f"✓ Generated: {init_path}")
