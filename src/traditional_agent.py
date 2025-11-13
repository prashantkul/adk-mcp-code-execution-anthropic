"""Traditional ADK agent using MCP tools directly (for comparison)."""

import asyncio
from pathlib import Path
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from dotenv import load_dotenv
import os
import json

from .mcp_client import MCPClient


class TraditionalMCPAgent:
    """Traditional ADK agent that uses MCP tools as direct function calls."""

    def __init__(self, mcp_server_url: str):
        """
        Initialize the Traditional MCP Agent.

        Args:
            mcp_server_url: URL of the MCP server
        """
        self.mcp_server_url = mcp_server_url
        self.mcp_client = MCPClient(mcp_server_url)
        self.agent = None
        self.runner = None
        self.session_service = None
        self.tools = []
        self.tool_schemas = []

    async def setup(self):
        """Setup the agent by fetching tools and configuring as ADK function tools."""
        print("🔧 Setting up Traditional MCP Agent...")

        # Step 1: Fetch available tools from MCP server
        print(f"📡 Connecting to MCP server: {self.mcp_server_url}")
        self.tools = await self.mcp_client.list_tools()
        print(f"✓ Found {len(self.tools)} MCP tools")

        # Step 2: Convert MCP tools to Google ADK function declarations
        print("🔨 Converting MCP tools to ADK function declarations...")
        function_declarations = self._convert_mcp_tools_to_functions()

        # Step 3: Create agent instruction
        instruction = self._build_agent_instruction()

        # Step 4: Initialize Google ADK agent with function tools
        print("🤖 Initializing Google ADK agent with function tools...")
        self.agent = LlmAgent(
            name="traditional_mcp_agent",
            model="gemini-2.0-flash",
            tools=function_declarations,
            instruction=instruction,
            description="Traditional agent that calls MCP tools directly as functions"
        )

        # Step 5: Setup session and runner
        self.session_service = InMemorySessionService()
        self.session = await self.session_service.create_session(
            app_name="traditional_mcp_app",
            user_id="demo_user",
            session_id="demo_session"
        )

        self.runner = Runner(
            agent=self.agent,
            app_name="traditional_mcp_app",
            session_service=self.session_service
        )

        print("✅ Traditional MCP Agent ready!\n")

    def _convert_mcp_tools_to_functions(self):
        """Convert MCP tool schemas to Google ADK function declarations."""
        function_declarations = []

        for tool in self.tools:
            # Convert MCP tool to Google function declaration format
            function_decl = types.FunctionDeclaration(
                name=tool.name,
                description=tool.description or f"Execute {tool.name} operation",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        name: types.Schema(
                            type=self._json_type_to_genai_type(prop.get("type", "string")),
                            description=prop.get("description", "")
                        )
                        for name, prop in tool.inputSchema.get("properties", {}).items()
                    },
                    required=tool.inputSchema.get("required", [])
                )
            )
            function_declarations.append(function_decl)
            self.tool_schemas.append(tool.model_dump())

        return function_declarations

    def _json_type_to_genai_type(self, json_type: str) -> types.Type:
        """Convert JSON Schema type to Google GenAI type."""
        type_mapping = {
            "string": types.Type.STRING,
            "integer": types.Type.INTEGER,
            "number": types.Type.NUMBER,
            "boolean": types.Type.BOOLEAN,
            "object": types.Type.OBJECT,
            "array": types.Type.ARRAY,
        }
        return type_mapping.get(json_type, types.Type.STRING)

    def _build_agent_instruction(self) -> str:
        """Build agent instruction for traditional approach."""
        tool_list = "\n".join([
            f"  - {tool.name}: {tool.description or 'No description'}"
            for tool in self.tools
        ])

        instruction = f"""You are an AI assistant with access to MCP tools.

**Available MCP Tools:**
{tool_list}

**Your Approach:**
1. **Call tools directly** using function calling
2. **Wait for results** from each tool call
3. **Process results** and make additional calls as needed
4. **Return final answer** to the user

**Guidelines:**
- Call tools one at a time or in sequence
- Wait for each tool's response before proceeding
- Combine results from multiple tool calls to answer complex queries
- Provide clear, comprehensive answers to user questions

**Example Workflow:**
User: "List all customers from California"
1. Call list_customers() → Get all customers
2. Filter the results in your response for California customers
3. Return the filtered list to the user

Remember: Each tool call goes through the model, so intermediate results are part of the conversation.
"""
        return instruction

    async def run_task(self, task: str) -> tuple[str, dict]:
        """
        Execute a task using the traditional MCP agent.

        Args:
            task: Natural language task description

        Returns:
            Tuple of (agent's response, token usage stats)
        """
        content = types.Content(
            role="user",
            parts=[types.Part(text=task)]
        )

        print(f"\n{'='*60}")
        print(f"📝 Task: {task}")
        print(f"{'='*60}\n")

        final_response = ""
        tool_calls_made = []
        token_count_estimate = 0

        # Estimate token count for tool schemas loaded in context
        tool_schemas_str = json.dumps(self.tool_schemas)
        token_count_estimate += len(tool_schemas_str) // 4  # Rough estimate

        async for event in self.runner.run_async(
            user_id="demo_user",
            session_id="demo_session",
            new_message=content
        ):
            # Capture tool calls
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        tool_name = part.function_call.name
                        tool_args = dict(part.function_call.args)
                        tool_calls_made.append({
                            "tool": tool_name,
                            "arguments": tool_args
                        })
                        print(f"🔧 Calling tool: {tool_name}")
                        print(f"   Arguments: {json.dumps(tool_args, indent=2)}")

                        # Execute the MCP tool
                        result = await self.mcp_client.call_tool(tool_name, tool_args)
                        print(f"   Result: {result}\n")

                        # Estimate tokens for this tool call
                        token_count_estimate += len(json.dumps(tool_args)) // 4
                        token_count_estimate += len(json.dumps(result)) // 4

                    elif hasattr(part, 'text') and part.text:
                        final_response = part.text

            # Capture final response
            if event.is_final_response():
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            final_response = part.text

        print(f"\n🎯 Final Answer: {final_response}\n")

        stats = {
            "tool_calls": len(tool_calls_made),
            "estimated_tokens": token_count_estimate,
            "tool_schemas_tokens": len(tool_schemas_str) // 4,
            "calls": tool_calls_made
        }

        return final_response, stats

    async def cleanup(self):
        """Cleanup resources."""
        await self.mcp_client.close()
