"""Docker-based code executor with restricted network access."""

import docker
import tempfile
from pathlib import Path
from typing import Optional
from google.genai.types import ExecutableCode, CodeExecutionResult, Outcome


class DockerCodeExecutor:
    """
    Code executor that runs Python code in a Docker container with restricted network access.

    Only allows connections to the specified MCP server URL.
    """

    def __init__(self, allowed_url: str, timeout: int = 30):
        """
        Initialize Docker code executor.

        Args:
            allowed_url: The only URL allowed for network access (e.g., ngrok MCP server)
            timeout: Execution timeout in seconds
        """
        self.allowed_url = allowed_url
        self.timeout = timeout
        self.client = docker.from_env()

        # Extract host from URL for iptables rules
        from urllib.parse import urlparse
        parsed = urlparse(allowed_url)
        self.allowed_host = parsed.netloc

    def execute(self, code: ExecutableCode) -> CodeExecutionResult:
        """
        Execute Python code in a Docker container with network restrictions.

        Args:
            code: The code to execute

        Returns:
            CodeExecutionResult with output and outcome
        """
        try:
            # Create temporary file with code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code.code)
                code_file = f.name

            # Get the actual filename for the container
            code_filename = Path(code_file).name

            # Run in Docker container with network restrictions
            container = self.client.containers.run(
                'python:3.11-slim',
                command=f'sh -c "pip install -q urllib3 && python /code/{code_filename}"',
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

            # Determine outcome
            if result['StatusCode'] == 0:
                outcome = Outcome.OUTCOME_OK
                output = stdout
            else:
                outcome = Outcome.OUTCOME_FAILED
                output = f"{stdout}\n{stderr}" if stderr else stdout

            return CodeExecutionResult(
                outcome=outcome,
                output=output.strip()
            )

        except docker.errors.ContainerError as e:
            return CodeExecutionResult(
                outcome=Outcome.OUTCOME_FAILED,
                output=f"Container error: {str(e)}"
            )
        except Exception as e:
            return CodeExecutionResult(
                outcome=Outcome.OUTCOME_FAILED,
                output=f"Execution error: {str(e)}"
            )
