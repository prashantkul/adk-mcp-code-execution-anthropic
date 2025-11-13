"""Test the generated wrapper functions directly."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Import the generated module
from mcp_tools import customer


async def test_wrapper_functions():
    """Test calling the generated wrapper functions."""

    print("🧪 Testing Generated MCP Wrapper Functions\n")
    print("=" * 60)

    # Test 1: List customers
    print("\n1️⃣ Testing list_customers()...")
    try:
        customers = await customer.list_customers()
        print(f"✅ SUCCESS! Got response:")
        print(f"   {customers[:200]}..." if len(str(customers)) > 200 else f"   {customers}")
    except Exception as e:
        print(f"❌ FAILED: {e}")

    # Test 2: Get specific customer
    print("\n2️⃣ Testing get_customer(customer_id=1)...")
    try:
        result = await customer.get_customer(customer_id=1)
        print(f"✅ SUCCESS! Got response:")
        print(f"   {result}")
    except Exception as e:
        print(f"❌ FAILED: {e}")

    # Test 3: Add customer
    print("\n3️⃣ Testing add_customer()...")
    try:
        result = await customer.add_customer(
            name="Test User",
            email="test@example.com"
        )
        print(f"✅ SUCCESS! Got response:")
        print(f"   {result}")
    except Exception as e:
        print(f"❌ FAILED: {e}")

    print("\n" + "=" * 60)
    print("✅ Wrapper function tests completed!\n")


if __name__ == "__main__":
    asyncio.run(test_wrapper_functions())
