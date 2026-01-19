#!/usr/bin/env python3
"""
Simple example script to test with steptrace CLI.

Run with:
    python -m steptrace run examples/simple_script.py
    python -m steptrace run examples/simple_script.py --log-output STDOUT
    python -m steptrace run examples/simple_script.py --config steptrace.yaml
"""

import sys


def calculate(a, b):
    """Perform some calculations."""
    result = a + b
    squared = result ** 2
    return squared


def process_list(items):
    """Process a list of items."""
    total = 0
    for item in items:
        total += calculate(item, 1)
    return total


def main():
    """Main function."""
    print("Simple script starting...")
    
    x = 10
    y = 20
    z = calculate(x, y)
    print(f"calculate({x}, {y}) = {z}")
    
    items = [1, 2, 3, 4, 5]
    result = process_list(items)
    print(f"process_list({items}) = {result}")
    
    print("Simple script done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
