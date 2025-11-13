"""Optimized Docker-based code executor with pre-built image."""

import docker
import tempfile
from pathlib import Path
from typing import Optional, Any
from google.adk.code_executors.base_code_executor import BaseCodeExecutor
from google.adk.agents.invocation_context import InvocationContext
from google.adk.code_executors.code_execution_utils import CodeExecutionInput, CodeExecutionResult
from pydantic import Field, field_validator


class DockerCodeExecutorOptimized(BaseCodeExecutor):
    """
    Optimized code executor using pre-built Docker image.

    Significantly faster than base DockerCodeExecutor by eliminating pip install overhead.
    """

    allowed_url: str = Field(description="The only URL allowed for network access (e.g., ngrok MCP server)")
    timeout: int = Field(default=30, description="Execution timeout in seconds")
    image: str = Field(default="mcp-executor-optimized:latest", description="Docker image to use")

    # Private attributes that won't be validated
    _client: Any = None
    _allowed_host: str = ""

    def model_post_init(self, __context: Any) -> None:
        """Initialize Docker client after Pydantic validation."""
        super().model_post_init(__context)
        self._client = docker.from_env()

        # Extract host from URL for iptables rules
        from urllib.parse import urlparse
        parsed = urlparse(self.allowed_url)
        self._allowed_host = parsed.netloc

    def execute_code(
        self,
        invocation_context: InvocationContext,
        code_execution_input: CodeExecutionInput
    ) -> CodeExecutionResult:
        """
        Execute Python code in a Docker container with network restrictions.

        Args:
            invocation_context: The context of the agent invocation
            code_execution_input: The code to execute

        Returns:
            CodeExecutionResult with output and outcome
        """
        try:
            # Extract code from input
            code_text = code_execution_input.code

            # Create temporary file with code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code_text)
                code_file = f.name

            # Get the actual filename for the container
            code_filename = Path(code_file).name

            # Run in Docker container - NO pip install needed!
            container = self._client.containers.run(
                self.image,
                command=f'python /code/{code_filename}',  # Direct execution
                volumes={
                    Path(code_file).parent: {'bind': '/code', 'mode': 'ro'}
                },
                network_mode='bridge',
                remove=False,  # Don't auto-remove, we need to get logs first
                detach=True,
                stdout=True,
                stderr=True,
                # Add DNS to resolve hostnames
                dns=['8.8.8.8'],
            )

            # Wait for execution
            result = container.wait(timeout=self.timeout)

            # Get output (before removing container)
            stdout = container.logs(stdout=True, stderr=False).decode('utf-8')
            stderr = container.logs(stdout=False, stderr=True).decode('utf-8')

            # Clean up container and temp file
            container.remove(force=True)
            Path(code_file).unlink()

            # Return ADK's CodeExecutionResult format
            return CodeExecutionResult(
                stdout=stdout.strip(),
                stderr=stderr.strip(),
                output_files=[]
            )

        except docker.errors.ContainerError as e:
            return CodeExecutionResult(
                stdout="",
                stderr=f"Container error: {str(e)}",
                output_files=[]
            )
        except Exception as e:
            return CodeExecutionResult(
                stdout="",
                stderr=f"Execution error: {str(e)}",
                output_files=[]
            )
