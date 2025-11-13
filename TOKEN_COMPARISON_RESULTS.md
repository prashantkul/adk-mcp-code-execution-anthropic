# Token Usage Comparison: Traditional vs Code Execution

## Test Results Summary

### Query 1: "Get customer with ID 2 and show their name and email"

| Metric | Code Execution | Traditional | Difference |
|--------|----------------|-------------|------------|
| **Total Tokens** | 634 | 411 | +54% (code exec uses MORE) |
| **Duration** | 5.07s | 3.13s | +62% slower |
| **Tool/Code Calls** | 1 | 1 | Same |

**Breakdown**:
- Code Execution: 322 (context) + 13 (query) + 281 (code) + 18 (result) = **634 tokens**
- Traditional: 305 (context + schemas) + 13 (query) + 4 (call) + 89 (result) = **411 tokens**

### Query 2: "List all customers and tell me how many there are"

| Metric | Code Execution | Traditional | Difference |
|--------|----------------|-------------|------------|
| **Total Tokens** | 1,192 | 1,171 | +2% (nearly equal) |
| **Duration** | 9.85s | 3.22s | +206% slower |
| **Tool/Code Calls** | 1 | 1 | Same |

**Breakdown**:
- Code Execution: 322 (context) + 12 (query) + 284 (code) + 574 (result) = **1,192 tokens**
- Traditional: 305 (context + schemas) + 12 (query) + 0 (call) + 854 (result) = **1,171 tokens**

## Analysis: Why Code Execution Didn't Win

### The Key Factor: Number of Tools

Our test uses an MCP server with **only 6 tools**:
1. `get_customer`
2. `list_customers`
3. `add_customer`
4. `update_customer`
5. `disable_customer`
6. `activate_customer`

**Tool schemas overhead**: ~305 tokens for 6 tools

### When Does Code Execution Win?

Anthropic's article references scenarios with **100+ tools**. Let's extrapolate:

| Number of Tools | Traditional Context Overhead | Code Execution Overhead | Savings |
|-----------------|------------------------------|------------------------|---------|
| 6 tools (our test) | ~305 tokens | ~322 tokens | **-5%** (worse) |
| 50 tools | ~2,500 tokens | ~322 tokens | **87%** better |
| 100 tools | ~5,000 tokens | ~322 tokens | **94%** better |
| 200 tools | ~10,000 tokens | ~322 tokens | **97%** better |

**The 98% claim assumes 100+ tools!**

## Where Code Execution DOES Win

### 1. **Complex Multi-Step Workflows**

Example: "Find high-value customers and upgrade them to premium"

**Traditional approach** (multiple round trips):
```
1. Call list_customers() → 854 tokens result
2. LLM processes all customer data in context → wasteful
3. Call update_customer(id=1) → round trip
4. Call update_customer(id=5) → round trip
5. Call update_customer(id=9) → round trip
Total: Massive token overhead + latency
```

**Code execution approach** (single code block):
```python
customers = call_mcp("list_customers")
high_value = [c for c in customers if c.get('total_spent', 0) > 1000]
for customer in high_value:
    call_mcp("update_customer", {"id": customer['id'], "tier": "premium"})
print(f"Upgraded {len(high_value)} customers")
```
**Result**: "Upgraded 3 customers" (minimal tokens)

### 2. **Data Processing & Filtering**

When you need to:
- Filter large datasets locally
- Aggregate data before returning
- Transform results
- Compute statistics

**Example**: "List customers from California with >$1000 spend"

**Traditional**: Returns ALL customers (wasteful), filters in LLM context
**Code Execution**: Filters in code, returns only matching results

### 3. **Iterative Operations**

**Example**: "Create 10 test customers"

**Traditional**: 10 separate tool calls, each with full context
**Code Execution**: Single loop in code

```python
for i in range(10):
    call_mcp("add_customer", {
        "name": f"Test User {i}",
        "email": f"test{i}@example.com"
    })
print("Created 10 test customers")
```

## Performance Comparison

### Latency

**Traditional**: ⚡ **Faster** (3.13-3.22s)
- Direct tool calls via native MCP protocol
- No Docker overhead
- No code generation step

**Code Execution**: 🐢 **Slower** (5.07-9.85s)
- Docker container startup (~0.3s)
- Code generation by LLM
- Code execution in container

### When Speed Matters

- **Use Traditional** for: Simple single-tool queries, real-time interactions
- **Use Code Execution** for: Complex workflows where orchestration matters more than latency

## Verdict: When to Use Each Approach

### Use **Traditional MCP (McpToolset)**:
✅ Small number of tools (< 20)
✅ Simple, single-tool queries
✅ Latency-sensitive applications
✅ Direct, straightforward operations

### Use **Code Execution**:
✅ Large tool ecosystems (100+ tools)
✅ Complex multi-step workflows
✅ Data processing/filtering needed
✅ Iterative operations (loops)
✅ Need to minimize token costs at scale
✅ Orchestration logic required

## Real-World Token Savings Example

**Scenario**: Enterprise agent with 150 tools, processing 1000 queries/day

### Traditional Approach:
```
Context per query: 150 tools × ~50 tokens/tool = 7,500 tokens
Daily overhead: 7,500 × 1,000 = 7,500,000 tokens
Monthly cost: 7.5M × 30 = 225M tokens in context alone
```

### Code Execution Approach:
```
Context per query: ~500 tokens (instruction + MCP URL)
Daily overhead: 500 × 1,000 = 500,000 tokens
Monthly cost: 500K × 30 = 15M tokens
```

**Savings**: **210M tokens/month = 93% reduction**

At $0.15/$7.50 per 1M tokens (input/output):
- Traditional: ~$33-1,687/month in context overhead
- Code Execution: ~$2-$112/month
- **Savings: $31-1,575/month**

## Conclusion

Our test with 6 tools shows the traditional approach is actually more efficient for simple queries. However, Anthropic's code execution pattern shines when:

1. **Tool count is high** (100+ tools)
2. **Workflows are complex** (multiple steps, data processing)
3. **Scale matters** (many queries, cost-sensitive)

For our simple customer management demo:
- **Traditional wins** on tokens AND speed
- **Code execution** demonstrates the pattern for future scale

The true value proposition emerges at enterprise scale with extensive tool catalogs and complex orchestration needs.

---

**Test Environment**:
- MCP Server: 6 customer management tools
- Model: Gemini 2.0 Flash
- Code Executor: DockerCodeExecutorOptimized (79% faster than baseline)
- Queries: Simple 1-2 tool operations
