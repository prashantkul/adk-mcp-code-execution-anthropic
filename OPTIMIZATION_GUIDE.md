# Docker Code Executor - Optimization Guide

## Current Performance

### Baseline (Original Implementation)
- **Simple execution**: ~1.65s
- **MCP calls**: ~2.02s
- **Bottleneck**: `pip install urllib3` on every execution (~1.3s overhead)

### Optimized (Pre-built Image)
- **Simple execution**: ~0.34s ⚡ **79% faster**
- **MCP calls**: ~0.52s ⚡ **74% faster**
- **Savings**: ~1.3s per execution

## Optimization Strategies

### 1. ✅ Pre-built Image (Implemented)

**Impact**: 75-80% latency reduction

**Implementation**:
```dockerfile
# Dockerfile.executor-optimized
FROM python:3.11-slim
RUN pip install --no-cache-dir urllib3
RUN useradd -m -u 1000 sandbox
USER sandbox
WORKDIR /workspace
CMD ["python"]
```

**Build**:
```bash
docker build -f Dockerfile.executor-optimized -t mcp-executor-optimized:latest .
```

**Usage**:
```python
from src.shared.docker_code_executor_optimized import DockerCodeExecutorOptimized

executor = DockerCodeExecutorOptimized(
    allowed_url=mcp_server_url,
    timeout=30
)
```

### 2. Container Pooling (Advanced)

**Impact**: Could reduce to ~0.1-0.2s by reusing containers

**Concept**: Keep warm containers running instead of creating new ones each time.

```python
class PooledDockerExecutor:
    def __init__(self, pool_size=3):
        self.pool = []
        for _ in range(pool_size):
            container = self.client.containers.run(
                'mcp-executor-optimized:latest',
                command='sleep infinity',  # Keep alive
                detach=True,
                ...
            )
            self.pool.append(container)

    def execute(self, code):
        container = self.pool.pop()
        # Execute code in existing container
        container.exec_run(f'python /code/{filename}')
        self.pool.append(container)  # Return to pool
```

**Trade-offs**:
- ✅ Eliminates container startup overhead
- ❌ More complex lifecycle management
- ❌ Requires container cleanup strategy
- ❌ Memory overhead (containers always running)

### 3. Batch Execution

**Impact**: Amortize container overhead across multiple operations

**Concept**: If agent generates multiple independent MCP calls, batch them in one container.

```python
# Instead of:
result1 = call_mcp("get_customer", {"customer_id": 1})
result2 = call_mcp("get_customer", {"customer_id": 2})
result3 = call_mcp("get_customer", {"customer_id": 3})

# Agent could generate:
import concurrent.futures

def fetch_customer(cid):
    return call_mcp("get_customer", {"customer_id": cid})

with concurrent.futures.ThreadPoolExecutor() as executor:
    results = list(executor.map(fetch_customer, [1, 2, 3]))
```

**Trade-offs**:
- ✅ Single container for multiple calls
- ✅ Natural for workflows with parallel operations
- ❌ Requires agent to generate batched code
- ❌ Timeout management more complex

### 4. Local Subprocess (No Docker)

**Impact**: Could reduce to ~0.05s, but loses isolation

**Concept**: Execute in local subprocess instead of Docker.

```python
import subprocess

def execute_local(code):
    result = subprocess.run(
        ['python', '-c', code],
        capture_output=True,
        timeout=30
    )
    return result.stdout.decode()
```

**Trade-offs**:
- ✅ Fastest possible execution
- ❌ **No isolation** - security risk
- ❌ No network restrictions
- ❌ Can access host filesystem
- ⚠️  **Only use for trusted code**

### 5. Production: GkeCodeExecutor

**Impact**: Better latency at scale with proper infrastructure

Google's recommended production solution:

```python
from google.adk.code_executors import GkeCodeExecutor

executor = GkeCodeExecutor(
    namespace="agent-sandbox",
    timeout_seconds=600,
    cpu_limit="1000m",
    mem_limit="2Gi"
)
```

**Features**:
- ✅ Kernel-level isolation (gVisor)
- ✅ Auto-scaling based on load
- ✅ Better resource management
- ✅ Optimized for concurrent executions
- ✅ Production-grade security

**Expected latency**: ~0.5-1.0s (similar to optimized Docker, but scales better)

## Comparison Table

| Approach | Latency | Security | Complexity | Cost | Best For |
|----------|---------|----------|------------|------|----------|
| **Original Docker** | ~1.6s | ✅ Good | ⭐ Easy | Free | Initial dev |
| **Optimized Docker** | ~0.3s | ✅ Good | ⭐ Easy | Free | **Development** |
| **Pooled Containers** | ~0.1s | ✅ Good | ⭐⭐⭐ Complex | Free | High throughput |
| **Local Subprocess** | ~0.05s | ❌ None | ⭐ Easy | Free | Trusted code only |
| **GkeCodeExecutor** | ~0.5s | ✅ Excellent | ⭐⭐ Medium | $$$ | **Production** |

## Recommendations

### For Development (Current)
✅ **Use: Optimized Docker Executor**
- Excellent balance of speed, security, and simplicity
- 0.3-0.5s latency is acceptable for development
- Easy to set up and maintain

### For Production
✅ **Use: GkeCodeExecutor**
- Better isolation and scaling
- Handles concurrent agent requests efficiently
- Production-grade monitoring and logging

### For Experiments
If you want to push latency even lower:
1. Try **container pooling** (0.1-0.2s)
2. Consider **batch execution** patterns
3. Profile to identify other bottlenecks (network, MCP server response time)

## Measuring Impact

Run the latency comparison:
```bash
python test_latency_comparison.py
```

Monitor Docker containers during execution:
```bash
watch -n 0.5 'docker ps --format "table {{.ID}}\t{{.Status}}\t{{.CreatedAt}}"'
```

## Bottom Line

**Current state**: ~0.5s for MCP calls with optimized Docker executor
- Fast enough for interactive agent experiences
- Secure with container isolation
- Simple to maintain

**If you need faster**: Consider GkeCodeExecutor for production or container pooling for experimentation.

---

**Questions?** See DOCKER_SETUP.md for basic setup or test_latency_comparison.py for benchmarks.
