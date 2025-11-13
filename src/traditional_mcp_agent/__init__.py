"""Traditional MCP Agent (for comparison).

This agent uses direct tool calling approach, where each MCP tool is registered
as a function and called individually through the model context.
"""

from .agent import TraditionalMCPAgent

__all__ = ["TraditionalMCPAgent"]
