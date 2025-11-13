"""MCP Code Execution Agent.

This agent uses Google ADK's code execution capabilities to orchestrate
MCP tools via generated Python code, achieving significant token reduction.
"""

from .agent import MCPCodeAgent

__all__ = ["MCPCodeAgent"]
