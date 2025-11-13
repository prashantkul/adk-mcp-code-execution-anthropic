"""Compare token usage between traditional tool calling and code execution."""

import asyncio
from typing import Dict, Any


def calculate_traditional_tokens() -> Dict[str, Any]:
    """Simulate token usage for traditional MCP approach."""

    # Tool schemas loaded in context
    tool_schemas = {
        "get_customer": 300,
        "list_customers": 280,
        "create_customer": 350,
        "update_customer": 340,
        "delete_customer": 290
    }

    schema_tokens = sum(tool_schemas.values())  # ~1,560 tokens

    # Complex workflow: List customers → Filter → Get details → Update
    workflow_steps = [
        {"tool": "list_customers", "request": 50, "response": 5000},  # Large response
        {"tool": "get_customer", "request": 40, "response": 200},
        {"tool": "get_customer", "request": 40, "response": 200},
        {"tool": "update_customer", "request": 150, "response": 100},
    ]

    workflow_tokens = sum(
        step["request"] + step["response"] for step in workflow_steps
    )

    total = schema_tokens + workflow_tokens

    return {
        "approach": "Traditional Tool Calling",
        "tool_schemas": schema_tokens,
        "workflow": workflow_tokens,
        "total": total,
        "breakdown": workflow_steps
    }


def calculate_code_execution_tokens() -> Dict[str, Any]:
    """Simulate token usage for code execution approach."""

    # Tool schemas on disk - not in context
    schema_tokens = 0

    # Single code block that does everything
    code_block = """
from mcp_tools import customer

# Get all customers
all_customers = await customer.list_customers()

# Filter for high-value customers (done in code, not through context)
high_value = [c for c in all_customers if c.get('total_spent', 0) > 1000]

# Get details for top 2
top_2 = high_value[:2]
details = []
for cust in top_2:
    detail = await customer.get_customer(customer_id=cust['id'])
    details.append(detail)

# Update them
for customer_detail in details:
    await customer.update_customer(
        customer_id=customer_detail['id'],
        tier='premium'
    )

# Return only summary (not all data)
print(f"Processed {len(high_value)} customers, upgraded {len(details)} to premium")
"""

    code_tokens = 450  # The code itself
    summary_response = 50  # Only the final print statement is returned

    total = schema_tokens + code_tokens + summary_response

    return {
        "approach": "Code Execution with MCP",
        "tool_schemas": schema_tokens,
        "code_block": code_tokens,
        "summary_response": summary_response,
        "total": total,
        "note": "Intermediate data (5000+ tokens) never enters model context"
    }


def print_comparison():
    """Print detailed token comparison."""
    traditional = calculate_traditional_tokens()
    code_exec = calculate_code_execution_tokens()

    reduction = ((traditional["total"] - code_exec["total"]) / traditional["total"]) * 100

    print("\n" + "="*70)
    print("TOKEN USAGE COMPARISON")
    print("="*70)

    print(f"\n{'Traditional Tool Calling':<40} | {'Code Execution':<25}")
    print("-"*70)
    print(f"{'Tool schemas in context:':<40} | {'Tool schemas on disk:':<25}")
    print(f"{traditional['tool_schemas']:>40} | {code_exec['tool_schemas']:>25}")
    print(f"\n{'Workflow execution:':<40} | {'Single code block:':<25}")
    print(f"{traditional['workflow']:>40} | {code_exec['code_block']:>25}")
    print(f"\n{'(includes large responses)':<40} | {'Summary only:':<25}")
    print(f"{'':>40} | {code_exec['summary_response']:>25}")
    print("-"*70)
    print(f"{'TOTAL:':<40} | {'TOTAL:':<25}")
    print(f"{traditional['total']:>40} | {code_exec['total']:>25}")
    print("="*70)

    print(f"\n📊 Token Reduction: {reduction:.1f}%")
    print(f"💰 Cost Savings: ~{reduction:.1f}%")
    print(f"⚡ Latency: Reduced (single execution vs. multiple round-trips)")

    print(f"\n💡 Key Insight:")
    print(f"   Intermediate data ({traditional['workflow'] - code_exec['code_block']} tokens)")
    print(f"   stayed in code execution environment, never entering model context!")

    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    print_comparison()
