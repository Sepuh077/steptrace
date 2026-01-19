#!/usr/bin/env python3
"""
Demo script for asyncio tracing with steptrace.
Run this to see async tracing in action.
"""

import asyncio
from steptrace import AsyncTracer, LogOutput, VariableMode


async def fetch_data(url: str, delay: float = 0.1) -> dict:
    """Simulate fetching data from a URL."""
    await asyncio.sleep(delay)
    return {"url": url, "data": f"Data from {url}"}


async def process_item(item: int) -> int:
    """Process a single item with some async delay."""
    await asyncio.sleep(0.05)
    result = item * 2
    return result


async def process_all(items: list) -> list:
    """Process all items concurrently."""
    tasks = [process_item(item) for item in items]
    results = await asyncio.gather(*tasks)
    return results


async def main_workflow():
    """Main async workflow demonstrating various async patterns."""
    print("Starting async workflow...")

    # Single await
    data1 = await fetch_data("https://api.example.com/data1", 0.1)
    print(f"Fetched: {data1}")

    # Multiple sequential awaits
    data2 = await fetch_data("https://api.example.com/data2", 0.05)
    data3 = await fetch_data("https://api.example.com/data3", 0.05)
    print(f"Fetched: {data2}, {data3}")

    # Concurrent processing
    items = [1, 2, 3, 4, 5]
    results = await process_all(items)
    print(f"Processed items: {results}")

    # Final result
    total = sum(results)
    return total


def main():
    """Entry point for the demo."""
    print("=" * 60)
    print("ASYNC DEMO 1: Basic async tracing with decorator")
    print("=" * 60)

    tracer = AsyncTracer(
        log_output=LogOutput.STDOUT,
        variable_mode=VariableMode.CHANGED,
        log_dir=".demo_async_tracer",
    )

    @tracer.trace_async
    async def decorated_async():
        result = await fetch_data("http://test.com")
        return result

    result = asyncio.run(decorated_async())
    print(f"Result: {result}\n")

    print("=" * 60)
    print("ASYNC DEMO 2: Full workflow tracing")
    print("=" * 60)

    tracer2 = AsyncTracer(
        log_output=LogOutput.STDOUT,
        variable_mode=VariableMode.NONE,
        log_dir=".demo_async_tracer",
        await_threshold_ms=0.0,  # Log all awaits
    )

    async def run_with_tracer():
        return await tracer2.run_async(main_workflow())

    result = asyncio.run(run_with_tracer())
    print(f"\nFinal result: {result}\n")

    print("=" * 60)
    print("ASYNC DEMO 3: Traced gather")
    print("=" * 60)

    tracer3 = AsyncTracer(
        log_output=LogOutput.STDOUT,
        variable_mode=VariableMode.NONE,
        log_dir=".demo_async_tracer",
    )

    async def gather_demo():
        results = await tracer3.gather(
            fetch_data("url1", 0.1),
            fetch_data("url2", 0.15),
            fetch_data("url3", 0.12),
        )
        return results

    async def run_gather():
        return await tracer3.run_async(gather_demo())

    results = asyncio.run(run_gather())
    print(f"\nGathered results: {results}\n")

    print("=" * 60)
    print("ASYNC DEMO 4: Task tracing")
    print("=" * 60)

    tracer4 = AsyncTracer(
        log_output=LogOutput.STDOUT,
        variable_mode=VariableMode.NONE,
        log_dir=".demo_async_tracer",
        trace_tasks=True,
    )

    async def task_demo():
        # Create traced tasks
        task1 = tracer4.wrap_task(fetch_data("task_url1", 0.1), "fetch_task_1")
        task2 = tracer4.wrap_task(fetch_data("task_url2", 0.08), "fetch_task_2")

        # Wait for both
        result1 = await task1
        result2 = await task2
        return [result1, result2]

    async def run_tasks():
        return await tracer4.run_async(task_demo())

    results = asyncio.run(run_tasks())
    print(f"\nTask results: {results}\n")

    print("=" * 60)
    print("All async demos complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
