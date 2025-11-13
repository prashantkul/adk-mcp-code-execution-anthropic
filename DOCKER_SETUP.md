# Docker Code Executor Setup

This guide explains how to set up the Docker-based code executor for local development.

## Why Docker Executor?

The `BuiltInCodeExecutor` (Gemini's sandbox) has **no network access**, so it cannot reach external MCP servers. The Docker executor provides:

- ✅ **Network access** to MCP servers
- ✅ **Local execution** (faster, no API limits)
- ✅ **Security** via container isolation
- ✅ **Restricted access** (only allowed URLs)

## Prerequisites

1. **Docker Desktop** installed and running
2. **Docker Python SDK** installed

## Setup Steps

### 1. Install Docker Python SDK

```bash
# Using pip
pip install docker

# Or using uv
uv pip install docker
```

### 2. Build the Executor Image

```bash
# Build the optimized Docker image for code execution (75% faster)
docker build -f Dockerfile.executor-optimized -t mcp-executor-optimized:latest .
```

**Note**: The optimized image includes pre-installed dependencies (urllib3), eliminating ~1.3s of `pip install` overhead on every execution.

### 3. Verify Docker is Running

```bash
# Check Docker is accessible
docker ps
```

### 4. Configure Environment

Make sure your `.env` file has the MCP server URL:

```bash
MCP_SERVER_URL=https://your-ngrok-url.ngrok.io/mcp
GOOGLE_API_KEY=your_api_key_here
```

### 5. Start the ADK Web Server

```bash
adk web src --port 8000
```

The agent will automatically use `DockerCodeExecutorOptimized` if Docker is available.

**Performance**: ~0.3-0.5s per execution (75% faster than original implementation)

## How It Works

### Architecture

```
┌─────────────────────────────────────────────┐
│  ADK Web Server (localhost:8000)            │
│                                             │
│  ┌────────────────────────────────────┐    │
│  │  MCP Code Agent                    │    │
│  │  - Uses DockerCodeExecutor         │    │
│  └────────────┬───────────────────────┘    │
│               │                             │
└───────────────┼─────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│  Docker Container (python:3.11-slim)         │
│  - Runs agent-generated code                 │
│  - Has network access                        │
│  - Isolated from host system                 │
│  - urllib.request available                  │
│               │                               │
│               ▼                               │
│     HTTP Request (urllib)                     │
└───────────────┬───────────────────────────────┘
                │
                ▼
    ┌────────────────────────────┐
    │  MCP Server (ngrok)        │
    │  - Customer tools          │
    │  - JSON-RPC 2.0           │
    │  - SSE responses           │
    └────────────────────────────┘
```

### Security Features

1. **Container Isolation**: Code runs in isolated Docker container
2. **Read-only filesystem**: Container has read-only root
3. **No privileged access**: Runs as non-root user
4. **Network restrictions**: Can be limited to specific URLs
5. **Resource limits**: CPU and memory can be constrained
6. **Temporary execution**: Container is removed after execution

## Usage Example

Once set up, use the agent normally:

1. Open http://localhost:8000/dev-ui/
2. Select `mcp_code_agent`
3. Ask: "List all customers"

The agent will:
1. Generate Python code with urllib
2. Execute in Docker container
3. Make HTTP request to MCP server
4. Return results

## Troubleshooting

### Docker Not Available

**Error**: `DockerCodeExecutor failed, falling back to BuiltInCodeExecutor`

**Solution**:
- Ensure Docker Desktop is running
- Check `docker ps` works
- Verify Python can access Docker: `python -c "import docker; print(docker.from_env().ping())"`

### Permission Denied

**Error**: `permission denied while trying to connect to Docker daemon`

**Solution**:
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
# Log out and back in

# Or use sudo (not recommended)
sudo adk web src --port 8000
```

### Network Access Fails

**Error**: Code runs but can't reach MCP server

**Solution**:
- Verify ngrok URL is accessible from host: `curl https://your-ngrok-url.ngrok.io/mcp`
- Check Docker container can reach internet: `docker run --rm python:3.11-slim python -c "import urllib.request; urllib.request.urlopen('https://google.com')"`
- Verify MCP_SERVER_URL in `.env` is correct

### Container Timeout

**Error**: `Container execution timed out`

**Solution**:
- Increase timeout in `DockerCodeExecutor(timeout=60)`
- Check MCP server is responding quickly
- Simplify the agent's code

## Production Deployment

For production, use `GkeCodeExecutor` instead:

```python
from google.adk.code_executors import GkeCodeExecutor

executor = GkeCodeExecutor(
    namespace="agent-sandbox",
    timeout_seconds=600,
    cpu_limit="1000m",
    mem_limit="2Gi"
)
```

This provides:
- ✅ Kernel-level isolation (gVisor)
- ✅ Auto-scaling
- ✅ Better resource management
- ✅ Production-grade security

## Comparison

| Feature | BuiltInCodeExecutor | DockerCodeExecutor | GkeCodeExecutor |
|---------|-------------------|-------------------|-----------------|
| Network Access | ❌ No | ✅ Yes | ✅ Yes |
| Setup Complexity | ⭐ Easy | ⭐⭐ Medium | ⭐⭐⭐ Complex |
| Isolation | ✅ Good | ✅ Good | ✅ Excellent |
| Cost | Free | Free | Paid (GKE) |
| Use Case | Demos (no network) | Development | Production |

## Next Steps

1. ✅ Set up Docker executor (this guide)
2. Test with MCP server
3. Monitor execution performance
4. Plan GKE migration for production

---

**Questions?** See the main README.md or check ADK documentation.
