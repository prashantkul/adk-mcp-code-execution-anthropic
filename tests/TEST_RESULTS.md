# Test Results: Traditional MCP vs Code Execution

Complete analysis of token usage, performance, and trade-offs between two approaches to MCP integration with Google ADK.

## Executive Summary

**For 10 sequential operations:**
- **Code Execution**: 89.8% token reduction, 66% faster
- **Traditional**: Better for 1-3 operations, worse for 10+

**Crossover point**: ~3-5 tool calls

---

## Test Environment

- **Model**: Gemini 2.0 Flash
- **MCP Server**: 6 customer management tools
- **Tools**: get_customer, list_customers, add_customer, update_customer, disable_customer, activate_customer
- **Code Executor**: DockerCodeExecutorOptimized (79% faster than baseline)
- **Test Date**: November 2024

---

## 1. Single Operation Tests

### Query: "Get customer with ID 2 and show their name and email"

#### Code Execution Approach
```
Context breakdown:
├── Instruction (with HTTP pattern): 336 tokens
├── User query: 3 tokens
├── Generated code: 281 tokens
├── Execution result: 18 tokens
└── Response: 20 tokens

Total: 658 tokens
Duration: 5.07s
Tool/Code calls: 1
```

#### Traditional MCP Approach
```
Context breakdown:
├── Instruction + tool schemas (6 tools): 305 tokens
├── User query: 3 tokens
├── Function call: 4 tokens
├── Tool result: 89 tokens
└── Response: 10 tokens

Total: 411 tokens
Duration: 3.13s
Tool calls: 1
```

### Result: Traditional Wins
- **Tokens**: 37% less (411 vs 658)
- **Speed**: 38% faster (3.13s vs 5.07s)
- **Why**: No code generation overhead, direct tool calling

---

## 2. List Operation Tests

### Query: "List all customers and tell me how many there are"

#### Code Execution Approach
```
Total: 1,192 tokens
Duration: 9.85s
```

#### Traditional MCP Approach
```
Total: 1,171 tokens
Duration: 3.22s
```

### Result: Nearly Equal on Tokens, Traditional Faster
- **Tokens**: Essentially equal (1% difference)
- **Speed**: Traditional 3x faster
- **Why**: Code generation + Docker overhead without benefit

---

## 3. Repeated Operations Test ⭐ CRITICAL

### Query: "Get details for customers 1 through 10, count active vs disabled"

This is where the fundamental difference emerges.

#### Code Execution Approach

```
Strategy: ALL 10 operations in ONE code block

Generated code:
─────────────────────────────────────────────────
import urllib.request
import json

MCP_URL = "https://..."

def call_mcp(tool_name, arguments):
    # ... helper function ...
    pass

# Main logic - ALL 10 calls happen HERE
active_count = 0
disabled_count = 0

for customer_id in range(1, 11):
    response = call_mcp("get_customer", {"customer_id": customer_id})
    data = json.loads(response["content"][0]["text"])
    customer = data.get("customer")

    if customer["status"] == "active":
        active_count += 1
    else:
        disabled_count += 1

# Only final summary returned
print(f"Active: {active_count}, Disabled: {disabled_count}")
─────────────────────────────────────────────────

Results:
├── Total context: 744 tokens (CONSTANT!)
├── Total processed: 744 tokens (1 LLM invocation)
├── Duration: 8.86s
├── Operations: 10 in 1 code block
└── Output: "Active: 8, Disabled: 2"
```

#### Traditional MCP Approach

```
Strategy: 10 SEQUENTIAL function calls + 1 summary

Turn 1: "Get customer 1"
  ├── Context: 223 (schemas) + 3 (Q) + 4 (call) + 89 (result)
  ├── Total: 315 tokens
  └── Duration: 2.58s

Turn 2: "Get customer 2"
  ├── Previous context STILL THERE: 315 tokens
  ├── New: 3 (Q) + 4 (call) + 89 (result)
  ├── Total: 407 tokens
  └── Duration: 2.71s

Turn 3: "Get customer 3"
  ├── Previous context STILL THERE: 407 tokens
  ├── New: 3 (Q) + 4 (call) + 89 (result)
  ├── Total: 498 tokens
  └── Duration: 2.32s

... pattern continues ...

Turn 10: "Get customer 10"
  ├── All 9 previous turns STILL THERE: 1,047 tokens
  ├── New: 3 (Q) + 4 (call) + 93 (result)
  ├── Total: 1,140 tokens
  └── Duration: 2.45s

Turn 11: "Based on all customers, count active vs disabled"
  ├── All 10 previous customer records in context: 1,140 tokens
  ├── New: 18 tokens
  ├── Total: 1,158 tokens
  └── LLM counts from context

Results:
├── Final context: 1,158 tokens
├── Total processed: 315 + 407 + 498 + ... + 1,158 = 7,268 tokens
├── Duration: 26.13s
├── Operations: 11 LLM round-trips
└── Output: "8 active, 2 disabled"
```

### Comparison

| Metric | Traditional | Code Execution | Savings |
|--------|-------------|----------------|---------|
| **Final context** | 1,158 tokens | 744 tokens | 35.8% |
| **Total processed** | 7,268 tokens | 744 tokens | **89.8%** ⚡⚡⚡ |
| **LLM invocations** | 11 | 1 | 90.9% |
| **Duration** | 26.13s | 8.86s | 66.1% |
| **Cost (est.)** | $0.00109 | $0.00011 | 89.8% |

### Context Growth Visualization

```
Traditional (Linear context, Quadratic processing):
─────────────────────────────────────────────────
Turn  Context  Processed  Cumulative
1     315      315        315
2     407      407        722
3     498      498        1,220
4     589      589        1,809
5     680      680        2,489
6     772      772        3,261
7     864      864        4,125
8     956      956        5,081
9     1,047    1,047      6,128
10    1,140    1,140      7,268
─────────────────────────────────────────────────

Code Execution (Constant):
─────────────────────────────────────────────────
Turn  Context  Processed  Cumulative
1     744      744        744
─────────────────────────────────────────────────
```

---

## 4. Scaling Analysis

### Extrapolated Results for Different Operation Counts

| Operations | Traditional (tokens) | Code Execution (tokens) | Savings |
|------------|---------------------|-------------------------|---------|
| 1 | 339 | 658 | -94% (worse) |
| 3 | ~1,000 | ~750 | 25% |
| 5 | ~2,000 | ~750 | 62% |
| 10 | 7,268 | 744 | **89.8%** |
| 20 | ~30,000 | ~750 | **97.5%** |
| 50 | ~200,000 | ~800 | **99.6%** |
| 100 | ~800,000 | ~850 | **99.9%** |

**Formula:**
- Traditional: O(n²) where n = number of operations
- Code Execution: O(1) constant

### Cost Analysis (at $0.15 per 1M input tokens)

| Operations | Traditional Cost | Code Execution Cost | Monthly Savings (1K queries/day) |
|------------|-----------------|---------------------|----------------------------------|
| 10 | $0.00109 | $0.00011 | **$29.40** |
| 50 | $0.030 | $0.00012 | **$897.60** |
| 100 | $0.120 | $0.00013 | **$3,596** |

---

## 5. Latency Analysis

### Single Operation
```
Traditional:    █████ 2.5s ⚡ FASTER
Code Execution: ██████████ 5.0s
```
**Why Traditional wins:**
- Direct MCP call
- No code generation
- No Docker overhead

### 10 Operations
```
Traditional:    ██████████████████████████ 26s
Code Execution: █████████ 9s ⚡ FASTER
```
**Why Code Execution wins:**
- 1 code generation vs 10 LLM round-trips
- Parallel execution potential
- No context reprocessing

### Latency Breakdown

**Traditional (per operation):**
- LLM processing: ~1.5s
- MCP call: ~0.5s
- Context reprocessing: grows with each turn
- **Total per op**: ~2.5s
- **10 ops**: 10 × 2.5s = 25s+ (sequential)

**Code Execution:**
- LLM code generation: ~3s (one time)
- Docker startup: ~0.3s (optimized)
- 10 MCP calls in code: ~5s (can be parallel)
- **Total**: ~8-9s

---

## 6. Tool Count Impact

### With 6 Tools (Our Test)
- Traditional schema overhead: 223 tokens
- Code Execution overhead: 336 tokens (instruction)
- **Difference**: Not significant

### With 100 Tools (Enterprise)
- Traditional schema overhead: ~3,700 tokens
- Code Execution overhead: 336 tokens (same instruction)
- **Savings**: 91% just on schemas!

### With 500 Tools (Large Organization)
- Traditional schema overhead: ~18,500 tokens
- Code Execution overhead: 336 tokens
- **Savings**: 98.2% on schemas alone

**This is why Anthropic claimed "98% reduction"** - they assumed large tool ecosystems.

---

## 7. When Each Approach Wins

### Traditional MCP Wins When:
✅ 1-3 tool calls per query
✅ <20 tools total
✅ Latency is critical (real-time applications)
✅ Simple, straightforward operations
✅ Tools change frequently (no need to update code patterns)
✅ Streaming responses needed
✅ Native function calling preferred

### Code Execution Wins When:
✅ 5+ tool calls per query
✅ 100+ tools in ecosystem
✅ Complex workflows with data processing
✅ Batch/iterative operations
✅ Need to filter/transform data
✅ Cost optimization is priority
✅ Orchestration logic in code
✅ Context accumulation is a concern

---

## 8. Real-World Scenario Analysis

### Scenario 1: Customer Support Dashboard
**Query**: "Show me the latest ticket for each customer in California"

**Traditional:**
1. list_customers() → 100 customers (wasteful!)
2. Filter CA in LLM context
3. get_ticket(id=5) for customer 5
4. get_ticket(id=12) for customer 12
... 25 more sequential calls
**Total**: 28 LLM round-trips, ~10,000 tokens

**Code Execution:**
```python
customers = call_mcp("list_customers")
ca_customers = [c for c in customers if c['state'] == 'CA']
for customer in ca_customers:
    ticket = call_mcp("get_ticket", {"customer_id": customer['id']})
    # process...
print(summary)
```
**Total**: 1 LLM call, ~850 tokens
**Savings**: 91.5%

### Scenario 2: Quick Lookup
**Query**: "What's the email for customer 42?"

**Traditional:**
1. get_customer(42) → instant
**Total**: 1 call, ~400 tokens, 2.5s ⚡

**Code Execution:**
1. Generate code
2. Execute in Docker
3. Return result
**Total**: 1 call, ~700 tokens, 5s

**Winner**: Traditional (simpler = better)

---

## 9. Performance Optimization Results

### Docker Executor Optimization
**Before (Baseline DockerCodeExecutor):**
- Execution time: 1.65s
- Bottleneck: `pip install urllib` on every run

**After (DockerCodeExecutorOptimized):**
- Execution time: 0.34s
- Improvement: **79% faster**
- Method: Pre-built Docker image with dependencies

**Impact on 10 operations:**
- Before: ~16.5s just for execution
- After: ~3.4s for execution
- **Savings: 13 seconds**

---

## 10. Error Analysis

### Code Execution Challenges Found
1. BuiltInCodeExecutor has NO network access → Had to use Docker
2. Two different `CodeExecutionResult` classes (GenAI vs ADK)
3. Pydantic validation requires proper Field declarations
4. SSE format handling needed in generated code

### Traditional MCP Challenges Found
1. Event loop conflicts when loading in ADK web
2. Must use McpToolset (not manual FunctionDeclaration)
3. Context accumulation hard to debug
4. No visibility into quadratic cost without instrumentation

---

## 11. Key Findings

### Finding 1: Context Size vs Processing Cost
**Context size** (what you see) is NOT the full story.
**Total processed** (what you pay for) is what matters.

Traditional with 10 operations:
- Context size: 1,158 tokens
- Total processed: **7,268 tokens** (6.3× more!)

### Finding 2: Growth Patterns
- Traditional context: O(n) linear
- Traditional processing: **O(n²) quadratic** ⚠️
- Code Execution: O(1) constant

### Finding 3: The Crossover Point
Around 3-5 operations, code execution becomes more efficient:
- 1-2 ops: Traditional wins
- 3-4 ops: Roughly equal
- 5+ ops: Code execution increasingly better
- 10+ ops: Code execution dramatically better

### Finding 4: Anthropic's 98% Claim
Valid, but requires:
- 100+ tools (massive schema overhead)
- Complex multi-step workflows
- NOT simple 1-2 tool queries

Our 6-tool test showed:
- Simple query: Traditional better
- Complex query (10 ops): 89.8% savings ✓

---

## 12. Recommendations

### Use Traditional MCP When:
- Prototyping quickly
- <10 tools
- Simple CRUD operations
- Real-time requirements
- Tools change frequently

### Use Code Execution When:
- Production at scale
- 50+ tools
- Complex orchestration
- Batch processing
- Cost is a concern
- Context window limits approached

### Hybrid Approach:
Use both! Route queries based on complexity:
```python
if tool_calls_needed <= 3:
    use_traditional_mcp()
else:
    use_code_execution()
```

---

## 13. Testing Methodology

All tests run with:
- Same MCP server (ngrok tunnel)
- Same model (Gemini 2.0 Flash)
- Same queries
- Token estimation: 4 chars ≈ 1 token
- Multiple runs for consistency

**Test Scripts:**
- `test_token_comparison_fixed.py` - Single operation comparison
- `test_repeated_operations.py` - Sequential operations (most important!)
- `test_programmatic.py` - Code execution validation
- `test_traditional_programmatic.py` - Traditional validation

---

## Conclusion

**Code Execution with MCP is not universally better** - it's better for specific scenarios:

✅ **Use when**: Many operations, large tool sets, cost-critical
❌ **Avoid when**: Simple queries, latency-critical, small tool sets

The 89.8% token reduction is real, but only applies to **repeated operations** with **context accumulation**. For simple queries, traditional MCP is more efficient.

**Key takeaway**: Choose the right tool for the job. Both approaches have valid use cases.
