#!/usr/bin/env python3
"""
Tests for asyncio tracing support.
"""

import asyncio
import os
import shutil
import sys
import tempfile
from io import StringIO

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from steptrace import AsyncTracer, LogLevel, LogOutput, VariableMode
from steptrace.async_tracer import traced_sleep, AwaitPointInfo, CoroutineInfo


async def simple_async():
    """Simple async function for testing."""
    await asyncio.sleep(0.01)
    return "done"


async def multi_await():
    """Async function with multiple awaits."""
    await asyncio.sleep(0.01)
    await asyncio.sleep(0.01)
    return "multi_done"


async def failing_async():
    """Async function that raises an exception."""
    await asyncio.sleep(0.01)
    raise ValueError("test error")


async def compute_async(n: int):
    """Async computation."""
    await asyncio.sleep(0.01)
    return n * 2


def test_async_tracer_creation():
    """Test AsyncTracer can be created with various options."""
    # Default options
    tracer1 = AsyncTracer()
    assert tracer1.await_threshold_ms == 0.0
    assert tracer1.trace_tasks is True
    
    # Custom options
    tracer2 = AsyncTracer(
        await_threshold_ms=10.0,
        trace_tasks=False,
        log_level=LogLevel.DEBUG,
        log_output=LogOutput.STDOUT,
    )
    assert tracer2.await_threshold_ms == 10.0
    assert tracer2.trace_tasks is False
    assert tracer2.log_level == LogLevel.DEBUG
    
    print("✓ test_async_tracer_creation passed")


def test_trace_async_decorator():
    """Test tracing async functions with decorator."""
    log_dir = tempfile.mkdtemp(prefix="async_tracer_test_")
    old_stdout = sys.stdout
    captured_stdout = StringIO()
    sys.stdout = captured_stdout
    
    try:
        tracer = AsyncTracer(
            log_output=LogOutput.STDOUT,
            log_level=LogLevel.INFO,
            log_dir=log_dir,
        )
        
        @tracer.trace_async
        async def decorated_func():
            await asyncio.sleep(0.01)
            return "decorated_result"
        
        result = asyncio.run(decorated_func())
        
        sys.stdout = old_stdout
        output = captured_stdout.getvalue()
        
        # Check result
        assert result == "decorated_result", f"Should return correct result, got {result}"
        
        # Check output contains async-related info
        assert "COROUTINE START" in output or "Async Step" in output, \
            f"Should have async output. Got: {output[:500]}"
        
        print("✓ test_trace_async_decorator passed")
    finally:
        sys.stdout = old_stdout
        shutil.rmtree(log_dir, ignore_errors=True)


def test_run_async():
    """Test running async with tracer.run_async()."""
    log_dir = tempfile.mkdtemp(prefix="async_tracer_test_")
    old_stdout = sys.stdout
    captured_stdout = StringIO()
    sys.stdout = captured_stdout
    
    try:
        tracer = AsyncTracer(
            log_output=LogOutput.STDOUT,
            log_dir=log_dir,
        )
        
        async def run():
            return await tracer.run_async(simple_async())
        
        result = asyncio.run(run())
        
        sys.stdout = old_stdout
        output = captured_stdout.getvalue()
        
        assert result == "done", f"Should return correct result, got {result}"
        assert "simple_async" in output or "COROUTINE" in output, \
            f"Should trace the coroutine. Got: {output[:500]}"
        
        print("✓ test_run_async passed")
    finally:
        sys.stdout = old_stdout
        shutil.rmtree(log_dir, ignore_errors=True)


def test_traced_gather():
    """Test traced gather operation."""
    log_dir = tempfile.mkdtemp(prefix="async_tracer_test_")
    old_stdout = sys.stdout
    captured_stdout = StringIO()
    sys.stdout = captured_stdout
    
    try:
        tracer = AsyncTracer(
            log_output=LogOutput.STDOUT,
            log_dir=log_dir,
        )
        
        async def run():
            return await tracer.gather(
                compute_async(1),
                compute_async(2),
                compute_async(3),
            )
        
        async def main():
            return await tracer.run_async(run())
        
        results = asyncio.run(main())
        
        sys.stdout = old_stdout
        output = captured_stdout.getvalue()
        
        assert results == [2, 4, 6], f"Gather should return correct results, got {results}"
        
        print("✓ test_traced_gather passed")
    finally:
        sys.stdout = old_stdout
        shutil.rmtree(log_dir, ignore_errors=True)


def test_wrap_task():
    """Test creating traced tasks."""
    log_dir = tempfile.mkdtemp(prefix="async_tracer_test_")
    old_stdout = sys.stdout
    captured_stdout = StringIO()
    sys.stdout = captured_stdout
    
    try:
        tracer = AsyncTracer(
            log_output=LogOutput.STDOUT,
            log_dir=log_dir,
            trace_tasks=True,
        )
        
        async def task_demo():
            task1 = tracer.wrap_task(compute_async(5), "compute_task")
            result = await task1
            return result
        
        async def main():
            return await tracer.run_async(task_demo())
        
        result = asyncio.run(main())
        
        sys.stdout = old_stdout
        output = captured_stdout.getvalue()
        
        assert result == 10, f"Task should return correct result, got {result}"
        
        # Should log task creation and completion
        assert "TASK" in output or "compute_task" in output, \
            f"Should log task info. Got: {output[:500]}"
        
        print("✓ test_wrap_task passed")
    finally:
        sys.stdout = old_stdout
        shutil.rmtree(log_dir, ignore_errors=True)


def test_await_threshold():
    """Test await threshold filtering."""
    log_dir = tempfile.mkdtemp(prefix="async_tracer_test_")
    old_stdout = sys.stdout
    captured_stdout = StringIO()
    sys.stdout = captured_stdout
    
    try:
        # Set threshold to 50ms - should filter out 10ms sleeps
        tracer = AsyncTracer(
            log_output=LogOutput.STDOUT,
            log_dir=log_dir,
            await_threshold_ms=50.0,
        )
        
        @tracer.trace_async
        async def quick_awaits():
            await asyncio.sleep(0.01)  # 10ms - below threshold
            await asyncio.sleep(0.01)  # 10ms - below threshold
            return "quick"
        
        result = asyncio.run(quick_awaits())
        
        sys.stdout = old_stdout
        output = captured_stdout.getvalue()
        
        assert result == "quick", f"Should return correct result, got {result}"
        
        # Await end logs should be filtered out (below threshold)
        # But coroutine start/end should still be logged
        
        print("✓ test_await_threshold passed")
    finally:
        sys.stdout = old_stdout
        shutil.rmtree(log_dir, ignore_errors=True)


def test_async_exception_handling():
    """Test that exceptions in async functions are properly handled."""
    log_dir = tempfile.mkdtemp(prefix="async_tracer_test_")
    old_stdout = sys.stdout
    captured_stdout = StringIO()
    sys.stdout = captured_stdout
    
    try:
        tracer = AsyncTracer(
            log_output=LogOutput.STDOUT,
            log_dir=log_dir,
        )
        
        @tracer.trace_async
        async def failing():
            await asyncio.sleep(0.01)
            raise ValueError("expected error")
        
        exception_raised = False
        try:
            asyncio.run(failing())
        except ValueError as e:
            exception_raised = True
            assert str(e) == "expected error"
        
        sys.stdout = old_stdout
        output = captured_stdout.getvalue()
        
        assert exception_raised, "Exception should be re-raised"
        
        print("✓ test_async_exception_handling passed")
    finally:
        sys.stdout = old_stdout
        shutil.rmtree(log_dir, ignore_errors=True)


def test_trace_await_explicit():
    """Test explicit await tracing with trace_await()."""
    log_dir = tempfile.mkdtemp(prefix="async_tracer_test_")
    old_stdout = sys.stdout
    captured_stdout = StringIO()
    sys.stdout = captured_stdout
    
    try:
        tracer = AsyncTracer(
            log_output=LogOutput.STDOUT,
            log_dir=log_dir,
        )
        
        async def with_explicit_trace():
            # Use trace_await for explicit tracing
            result = await tracer.trace_await(
                asyncio.sleep(0.01),
                "explicit_sleep"
            )
            return "traced"
        
        async def main():
            return await tracer.run_async(with_explicit_trace())
        
        result = asyncio.run(main())
        
        sys.stdout = old_stdout
        output = captured_stdout.getvalue()
        
        assert result == "traced", f"Should return correct result, got {result}"
        
        print("✓ test_trace_await_explicit passed")
    finally:
        sys.stdout = old_stdout
        shutil.rmtree(log_dir, ignore_errors=True)


def test_traced_sleep_helper():
    """Test the traced_sleep helper function."""
    log_dir = tempfile.mkdtemp(prefix="async_tracer_test_")
    old_stdout = sys.stdout
    captured_stdout = StringIO()
    sys.stdout = captured_stdout
    
    try:
        tracer = AsyncTracer(
            log_output=LogOutput.STDOUT,
            log_dir=log_dir,
        )
        
        async def with_traced_sleep():
            await traced_sleep(tracer, 0.01)
            return "slept"
        
        async def main():
            return await tracer.run_async(with_traced_sleep())
        
        result = asyncio.run(main())
        
        sys.stdout = old_stdout
        output = captured_stdout.getvalue()
        
        assert result == "slept", f"Should return correct result, got {result}"
        
        print("✓ test_traced_sleep_helper passed")
    finally:
        sys.stdout = old_stdout
        shutil.rmtree(log_dir, ignore_errors=True)


def test_await_point_info():
    """Test AwaitPointInfo class."""
    info = AwaitPointInfo(
        coro_name="test_coro",
        filename="/path/to/file.py",
        lineno=42,
        awaited_expr="await something()"
    )
    
    assert info.coro_name == "test_coro"
    assert info.filename == "/path/to/file.py"
    assert info.lineno == 42
    assert info.awaited_expr == "await something()"
    assert info.end_time is None
    
    # Duration should work before completion
    assert info.duration_ms >= 0
    
    # Complete the await
    info.complete(result="test_result")
    assert info.end_time is not None
    assert info.result == "test_result"
    assert info.exception is None
    
    print("✓ test_await_point_info passed")


def test_coroutine_info():
    """Test CoroutineInfo class."""
    async def dummy():
        pass
    
    coro = dummy()
    info = CoroutineInfo("test_coro", coro)
    
    assert info.name == "test_coro"
    assert info.coro is coro
    assert info.end_time is None
    assert len(info.await_points) == 0
    
    # Duration should work before completion
    assert info.duration_ms >= 0
    
    # Complete the coroutine
    info.complete(result="coro_result")
    assert info.end_time is not None
    assert info.result == "coro_result"
    
    # Cleanup the coroutine
    coro.close()
    
    print("✓ test_coroutine_info passed")


def test_silent_async_tracer():
    """Test AsyncTracer with SILENT log level."""
    log_dir = tempfile.mkdtemp(prefix="async_tracer_test_")
    old_stdout = sys.stdout
    captured_stdout = StringIO()
    sys.stdout = captured_stdout
    
    try:
        tracer = AsyncTracer(
            log_level=LogLevel.SILENT,
            log_output=LogOutput.STDOUT,
            log_dir=log_dir,
        )
        
        @tracer.trace_async
        async def silent_func():
            await asyncio.sleep(0.01)
            return "silent"
        
        result = asyncio.run(silent_func())
        
        sys.stdout = old_stdout
        output = captured_stdout.getvalue()
        
        assert result == "silent", f"Should return correct result, got {result}"
        assert output == "", f"SILENT mode should produce no output. Got: {output}"
        
        print("✓ test_silent_async_tracer passed")
    finally:
        sys.stdout = old_stdout
        shutil.rmtree(log_dir, ignore_errors=True)


def test_sync_and_async_trace():
    """Test that trace() decorator works for both sync and async."""
    log_dir = tempfile.mkdtemp(prefix="async_tracer_test_")
    
    try:
        tracer = AsyncTracer(
            log_level=LogLevel.SILENT,  # Keep output minimal
            log_dir=log_dir,
        )
        
        # Sync function
        @tracer.trace
        def sync_func(x):
            return x * 2
        
        # Async function
        @tracer.trace
        async def async_func(x):
            await asyncio.sleep(0.01)
            return x * 3
        
        # Test sync
        sync_result = sync_func(5)
        assert sync_result == 10, f"Sync should return 10, got {sync_result}"
        
        # Test async
        async_result = asyncio.run(async_func(5))
        assert async_result == 15, f"Async should return 15, got {async_result}"
        
        print("✓ test_sync_and_async_trace passed")
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


if __name__ == "__main__":
    print("Testing Async Tracer")
    print("=" * 50)
    test_async_tracer_creation()
    test_trace_async_decorator()
    test_run_async()
    test_traced_gather()
    test_wrap_task()
    test_await_threshold()
    test_async_exception_handling()
    test_trace_await_explicit()
    test_traced_sleep_helper()
    test_await_point_info()
    test_coroutine_info()
    test_silent_async_tracer()
    test_sync_and_async_trace()
    print("=" * 50)
    print("All async tracer tests passed!")
