"""Google ADK agent configured for code execution with MCP tools."""

import asyncio
from pathlib import Path
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.code_executors import BuiltInCodeExecutor
from google.genai import types
from dotenv import load_dotenv
import os

from .mcp_client import MCPClient
from .tool_generator import MCPToolGenerator


class MCPCodeAgent:
    """Google ADK agent that uses code execution to interact with MCP tools."""

    def __init__(self, mcp_server_url: str):
        """
        Initialize the MCP Code Agent.

        Args:
            mcp_server_url: URL of the MCP server
        """
        self.mcp_server_url = mcp_server_url
        self.mcp_client = MCPClient(mcp_server_url)
        self.tools_dir = Path("mcp_tools")
        self.agent = None
        self.runner = None
        self.session_service = None

    async def setup(self):
        """Setup the agent by generating tool wrappers and initializing ADK components."""
        print("🔧 Setting up MCP Code Agent...")

        # Step 1: Fetch available tools from MCP server
        print(f"📡 Connecting to MCP server: {self.mcp_server_url}")
        tools = await self.mcp_client.list_tools()
        print(f"✓ Found {len(tools)} MCP tools")

        # Step 2: Generate Python wrapper modules
        print("🔨 Generating Python wrapper modules...")
        generator = MCPToolGenerator(self.mcp_server_url)

        tool_dicts = [tool.model_dump() for tool in tools]
        module_code = generator.generate_wrapper_module(tool_dicts, "customer")

        # Write the module
        generator.write_module_to_file(
            module_code,
            self.tools_dir / "customer.py"
        )
        generator.generate_init_file(self.tools_dir)

        # Step 3: Create agent instruction with tool information
        instruction = self._build_agent_instruction(tools)

        # Step 4: Initialize Google ADK agent
        print("🤖 Initializing Google ADK agent...")
        self.agent = LlmAgent(
            name="mcp_code_agent",
            model="gemini-2.0-flash",
            code_executor=BuiltInCodeExecutor(),
            instruction=instruction,
            description="Agent that executes Python code to orchestrate MCP tools efficiently"
        )

        # Step 5: Setup session and runner
        self.session_service = InMemorySessionService()
        self.session = await self.session_service.create_session(
            app_name="mcp_code_app",
            user_id="demo_user",
            session_id="demo_session"
        )

        self.runner = Runner(
            agent=self.agent,
            app_name="mcp_code_app",
            session_service=self.session_service
        )

        print("✅ MCP Code Agent ready!\n")

    def _build_agent_instruction(self, tools) -> str:
        """Build comprehensive agent instruction with tool details."""
        tool_list = "\n".join([
            f"  - {tool.name}: {tool.description or 'No description'}"
            for tool in tools
        ])

        instruction = f"""You are an expert Python developer with access to MCP tools via code execution.

**Available MCP Tools** (accessible via `mcp_tools.customer` module):
{tool_list}

**Your Capabilities:**
1. **Write Python code** to interact with MCP tools instead of calling them directly
2. **Chain multiple operations** in a single code block without token overhead
3. **Process data locally** - filter, transform, and aggregate before returning results
4. **Handle errors gracefully** with try-except blocks
5. **Return only final results** - keep intermediate data in the code execution environment

**Code Execution Guidelines:**

1. **Import the module:**
   ```python
   from mcp_tools import customer
   import asyncio
   ```

2. **Always use async/await** since MCP tools are async:
   ```python
   result = await customer.get_customer(customer_id="123")
   ```

3. **For complex workflows, orchestrate multiple tools:**
   ```python
   # Fetch all customers
   all_customers = await customer.list_customers()

   # Filter high-value customers
   high_value = [c for c in all_customers if c.get('total_spent', 0) > 1000]

   # Update each one
   for customer in high_value:
       await customer.update_customer(
           customer_id=customer['id'],
           tier='premium'
       )

   # Return summary only (not all intermediate data)
   print(f"Upgraded {{len(high_value)}} customers to premium tier")
   ```

4. **Use error handling:**
   ```python
   try:
       result = await customer.get_customer(customer_id="123")
       print(f"Customer: {{result['name']}}")
   except Exception as e:
       print(f"Error: {{str(e)}}")
   ```

5. **Keep token usage minimal** - process data in code, return concise summaries

**Example Tasks You Can Handle:**
- "Get customer 123's details" → Simple single tool call
- "List all customers from California" → Fetch all, filter in code
- "Create 5 test customers" → Loop in code, call create_customer multiple times
- "Find the customer who spent the most and upgrade them" → Complex multi-step workflow

**Remember:** Your superpower is writing efficient Python code that orchestrates MCP tools.
Write clean, production-quality code with proper error handling.
"""
        return instruction

    async def run_task(self, task: str) -> str:
        """
        Execute a task using the MCP code agent.

        Args:
            task: Natural language task description

        Returns:
            Agent's response
        """
        content = types.Content(
            role="user",
            parts=[types.Part(text=task)]
        )

        print(f"\n{'='*60}")
        print(f"📝 Task: {task}")
        print(f"{'='*60}\n")

        final_response = ""
        code_executed = []

        async for event in self.runner.run_async(
            user_id="demo_user",
            session_id="demo_session",
            new_message=content
        ):
            # Capture code execution
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.executable_code:
                        code_executed.append(part.executable_code.code)
                        print(f"🔧 Executing code:\n")
                        print("```python")
                        print(part.executable_code.code)
                        print("```\n")

                    elif part.code_execution_result:
                        print(f"📊 Result: {part.code_execution_result.outcome}")
                        if part.code_execution_result.output:
                            print(f"Output:\n{part.code_execution_result.output}\n")

            # Capture final response
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response = event.content.parts[0].text

        print(f"\n🎯 Final Answer: {final_response}\n")
        return final_response

    async def cleanup(self):
        """Cleanup resources."""
        await self.mcp_client.close()
