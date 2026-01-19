#!/usr/bin/env python3
"""
Mixed Demo: Combining synchronous and asynchronous functions.

This script demonstrates tracing both sync and async code together.

Usage:
    # Basic tracing (sync functions only)
    python -m steptrace run examples/mixed_demo.py --log-output STDOUT

    # With async tracing enabled
    python -m steptrace run examples/mixed_demo.py --trace-async --log-output STDOUT

    # With variable change tracking
    python -m steptrace run examples/mixed_demo.py --trace-async --variable-mode CHANGED --log-output STDOUT

    # Only log slow awaits (>50ms)
    python -m steptrace run examples/mixed_demo.py --trace-async --async-threshold-ms 50 --log-output STDOUT
"""

import asyncio
import time


# ============== Synchronous Functions ==============

def calculate_fibonacci(n: int) -> int:
    """Calculate fibonacci number synchronously."""
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def process_numbers(numbers: list) -> dict:
    """Process a list of numbers synchronously."""
    total = sum(numbers)
    average = total / len(numbers)
    squared = [x ** 2 for x in numbers]
    return {
        "total": total,
        "average": average,
        "squared": squared,
        "count": len(numbers),
    }


def validate_data(data: dict) -> bool:
    """Validate data synchronously."""
    required_keys = ["name", "value"]
    for key in required_keys:
        if key not in data:
            return False
    if not isinstance(data["value"], (int, float)):
        return False
    return True


# ============== Asynchronous Functions ==============

async def fetch_user_data(user_id: int) -> dict:
    """Simulate fetching user data from an API."""
    await asyncio.sleep(0.05)  # Simulate network delay
    return {
        "id": user_id,
        "name": f"User_{user_id}",
        "email": f"user{user_id}@example.com",
    }


async def fetch_user_orders(user_id: int) -> list:
    """Simulate fetching user orders from an API."""
    await asyncio.sleep(0.08)  # Simulate network delay
    return [
        {"order_id": 1001 + user_id, "amount": 99.99},
        {"order_id": 1002 + user_id, "amount": 149.50},
    ]


async def process_user_async(user_id: int) -> dict:
    """Process a user by fetching their data and orders concurrently."""
    # Fetch user data and orders concurrently
    user_task = asyncio.create_task(fetch_user_data(user_id))
    orders_task = asyncio.create_task(fetch_user_orders(user_id))
    
    user_data = await user_task
    orders = await orders_task
    
    # Calculate total order amount (sync operation)
    total_amount = sum(order["amount"] for order in orders)
    
    return {
        "user": user_data,
        "orders": orders,
        "total_spent": total_amount,
    }


async def batch_process_users(user_ids: list) -> list:
    """Process multiple users concurrently."""
    tasks = [process_user_async(uid) for uid in user_ids]
    results = await asyncio.gather(*tasks)
    return results


# ============== Mixed Functions ==============

def prepare_input_data() -> dict:
    """Prepare input data synchronously."""
    print("Preparing input data...")
    
    # Generate some fibonacci numbers
    fib_numbers = [calculate_fibonacci(i) for i in range(10)]
    
    # Process the numbers
    stats = process_numbers(fib_numbers)
    
    # Validate sample data
    sample_data = {"name": "test", "value": 42}
    is_valid = validate_data(sample_data)
    
    return {
        "fibonacci": fib_numbers,
        "stats": stats,
        "sample_valid": is_valid,
        "user_ids": [1, 2, 3],
    }


async def run_async_operations(user_ids: list) -> dict:
    """Run async operations."""
    print("Running async operations...")
    
    # Process users
    user_results = await batch_process_users(user_ids)
    
    # Calculate overall statistics
    total_users = len(user_results)
    total_orders = sum(len(r["orders"]) for r in user_results)
    total_revenue = sum(r["total_spent"] for r in user_results)
    
    return {
        "users_processed": total_users,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "details": user_results,
    }


def analyze_results(sync_data: dict, async_data: dict) -> dict:
    """Analyze combined results synchronously."""
    print("Analyzing results...")
    
    analysis = {
        "fibonacci_sum": sum(sync_data["fibonacci"]),
        "fibonacci_avg": sync_data["stats"]["average"],
        "users_processed": async_data["users_processed"],
        "average_revenue_per_user": async_data["total_revenue"] / async_data["users_processed"],
        "data_valid": sync_data["sample_valid"],
    }
    
    return analysis


async def main_async():
    """Main async entry point."""
    print("=" * 60)
    print("Mixed Demo: Sync + Async Functions")
    print("=" * 60)
    
    # Step 1: Prepare data synchronously
    input_data = prepare_input_data()
    print(f"Prepared {len(input_data['fibonacci'])} fibonacci numbers")
    print(f"Stats: {input_data['stats']}")
    
    # Step 2: Run async operations
    async_results = await run_async_operations(input_data["user_ids"])
    print(f"Processed {async_results['users_processed']} users")
    print(f"Total revenue: ${async_results['total_revenue']:.2f}")
    
    # Step 3: Analyze results synchronously
    analysis = analyze_results(input_data, async_results)
    print(f"\nFinal Analysis:")
    for key, value in analysis.items():
        print(f"  {key}: {value}")
    
    print("=" * 60)
    print("Demo complete!")
    print("=" * 60)
    
    return analysis


def main():
    """Main entry point."""
    result = asyncio.run(main_async())
    return result


if __name__ == "__main__":
    main()
