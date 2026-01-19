#!/usr/bin/env python3
"""
Async example script to test with steptrace CLI.

Run with:
    python -m steptrace run examples/async_script.py --trace-async
    python -m steptrace run examples/async_script.py --trace-async --log-output STDOUT
"""

import asyncio


async def fetch_data(name: str, delay: float = 0.1) -> str:
    """Simulate an async data fetch."""
    await asyncio.sleep(delay)
    return f"data-{name}"


async def process_data(data: str) -> str:
    """Process data asynchronously."""
    await asyncio.sleep(0.05)
    return data.upper()


async def main():
    """Main async function."""
    print("Async script starting...")
    
    # Sequential fetches
    data1 = await fetch_data("first", 0.1)
    data2 = await fetch_data("second", 0.05)
    
    # Process sequentially
    result1 = await process_data(data1)
    result2 = await process_data(data2)
    
    print(f"Results: {result1}, {result2}")
    
    # Concurrent fetches
    results = await asyncio.gather(
        fetch_data("a", 0.05),
        fetch_data("b", 0.08),
        fetch_data("c", 0.03),
    )
    print(f"Gathered: {results}")
    
    print("Async script done!")


if __name__ == "__main__":
    asyncio.run(main())
