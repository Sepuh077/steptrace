#!/usr/bin/env python3
"""
Demo script for steptrace library.
Run this to see the different options in action.
"""

from steptrace import LogLevel, LogOutput, Tracer, VariableMode


def calculate_factorial(n):
    """Calculate factorial recursively."""
    if n <= 1:
        return 1
    return n * calculate_factorial(n - 1)


def fibonacci(n):
    """Calculate nth Fibonacci number."""
    if n <= 1:
        return n
    a, b = 0, 1
    for i in range(2, n + 1):
        a, b = b, a + b
    return b


def process_data(data):
    """Process a list of numbers."""
    total = 0
    doubled = []
    for item in data:
        total += item
        doubled.append(item * 2)
    average = total / len(data)
    return total, average, doubled


def main():
    """Main function that calls other functions."""
    x = 5
    y = 10

    # Some calculations
    fact = calculate_factorial(4)
    fib = fibonacci(6)

    # Process some data
    numbers = [1, 2, 3, 4, 5]
    total, avg, doubled = process_data(numbers)

    result = x + y + fact + fib
    return result


if __name__ == "__main__":
    print("=" * 60)
    print("DEMO 1: Default settings (INFO level, FILE output, ALL variables)")
    print("=" * 60)
    with Tracer(log_dir=".demo_tracer"):
        result = main()
    print(f"Result: {result}")
    print("Check .demo_tracer/tracer.log for output\n")

    print("=" * 60)
    print("DEMO 2: STDOUT output with CHANGED variables only")
    print("=" * 60)
    with Tracer(
        log_output=LogOutput.STDOUT,
        variable_mode=VariableMode.CHANGED,
        log_dir=".demo_tracer",
    ):
        result = main()
    print(f"\nResult: {result}\n")

    print("=" * 60)
    print("DEMO 3: WARNING level (same as INFO) to STDOUT")
    print("=" * 60)
    with Tracer(
        log_level=LogLevel.WARNING, log_output=LogOutput.STDOUT, log_dir=".demo_tracer"
    ):
        result = main()
    print(f"\nResult: {result}\n")

    print("=" * 60)
    print("DEMO 4: DEBUG level with NO variables to STDERR")
    print("=" * 60)
    with Tracer(
        log_level=LogLevel.DEBUG,
        log_output=LogOutput.STDERR,
        variable_mode=VariableMode.NONE,
        log_dir=".demo_tracer",
    ):
        result = main()
    print(f"\nResult: {result}\n")

    print("=" * 60)
    print("DEMO 5: Using decorator with CHANGED variables")
    print("=" * 60)

    tracer = Tracer(
        log_output=LogOutput.STDOUT,
        variable_mode=VariableMode.CHANGED,
        log_dir=".demo_tracer",
    )

    @tracer.trace
    def decorated_demo():
        a = 1
        b = 2
        a = 10  # This change will be tracked
        c = a + b
        return c

    result = decorated_demo()
    print(f"\nDecorated function result: {result}\n")

    print("=" * 60)
    print("DEMO 6: SILENT mode (no output, but tracing still works)")
    print("=" * 60)
    with Tracer(log_level=LogLevel.SILENT, log_dir=".demo_tracer"):
        result = main()
    print(f"Result (computed silently): {result}\n")

    print("=" * 60)
    print("All demos complete!")
    print("=" * 60)
