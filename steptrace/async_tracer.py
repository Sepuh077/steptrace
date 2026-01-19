"""
Asyncio tracing support for steptrace.

Provides tracing of asyncio coroutines, await points, and their durations.
"""

import asyncio
import functools
import inspect
import sys
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Union

from .tracer import LogLevel, LogOutput, Tracer, VariableMode


class AwaitPointInfo:
    """Information about an await point."""

    def __init__(
        self,
        coro_name: str,
        filename: str,
        lineno: int,
        awaited_expr: str = "",
    ):
        self.coro_name = coro_name
        self.filename = filename
        self.lineno = lineno
        self.awaited_expr = awaited_expr
        self.start_time = time.perf_counter()
        self.end_time: Optional[float] = None
        self.result: Any = None
        self.exception: Optional[Exception] = None

    @property
    def duration_ms(self) -> float:
        """Duration in milliseconds."""
        if self.end_time is None:
            return (time.perf_counter() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000

    def complete(self, result: Any = None, exception: Exception = None):
        """Mark the await as complete."""
        self.end_time = time.perf_counter()
        self.result = result
        self.exception = exception


class CoroutineInfo:
    """Information about a traced coroutine."""

    def __init__(self, name: str, coro: Coroutine):
        self.name = name
        self.coro = coro
        self.start_time = time.perf_counter()
        self.end_time: Optional[float] = None
        self.await_points: List[AwaitPointInfo] = []
        self.result: Any = None
        self.exception: Optional[Exception] = None

    @property
    def duration_ms(self) -> float:
        """Total duration in milliseconds."""
        if self.end_time is None:
            return (time.perf_counter() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000

    def complete(self, result: Any = None, exception: Exception = None):
        """Mark the coroutine as complete."""
        self.end_time = time.perf_counter()
        self.result = result
        self.exception = exception


class AsyncTracer(Tracer):
    """
    Extended tracer with asyncio support.

    Traces:
    - Regular Python code (like base Tracer)
    - Coroutine creation and completion
    - Await points and their durations
    - Async context managers
    - Async iterations
    """

    def __init__(
        self,
        await_threshold_ms: float = 0.0,
        trace_tasks: bool = True,
        **kwargs,
    ):
        """
        Initialize AsyncTracer.

        Args:
            await_threshold_ms: Only log await points taking longer than this (ms).
                               0.0 means log all await points.
            trace_tasks: Whether to trace asyncio.Task creation/completion.
            **kwargs: Arguments passed to base Tracer.
        """
        super().__init__(**kwargs)
        self.await_threshold_ms = await_threshold_ms
        self.trace_tasks = trace_tasks

        # Async-specific tracking
        self._active_coroutines: Dict[int, CoroutineInfo] = {}
        self._current_await: Optional[AwaitPointInfo] = None
        self._async_step = 0

        # For tracking awaitable entry/exit
        self._await_stack: List[AwaitPointInfo] = []
        self._coro_stack: List[CoroutineInfo] = []

    def _log_async(self, message: str, level: str = "INFO"):
        """Write an async-specific log message."""
        if self.log_level >= LogLevel.SILENT:
            return

        self._async_step += 1
        timestamp = time.perf_counter() - self._timer

        text = f"--------------------- Async Step {self._async_step} ---------------------\n"
        text += f"Time: {timestamp * 1000:.4f} ms | {level}\n"
        text += message + "\n"

        self._write_output(text)

    def _log_await_start(self, await_info: AwaitPointInfo):
        """Log the start of an await."""
        if self.log_level >= LogLevel.SILENT:
            return

        msg = f"⏳ AWAIT START: {await_info.coro_name}\n"
        msg += f"   File: {await_info.filename}:{await_info.lineno}\n"
        if await_info.awaited_expr:
            msg += f"   Expression: {await_info.awaited_expr}\n"

        self._log_async(msg, "AWAIT")

    def _log_await_end(self, await_info: AwaitPointInfo):
        """Log the end of an await."""
        if self.log_level >= LogLevel.SILENT:
            return

        # Check threshold
        if await_info.duration_ms < self.await_threshold_ms:
            return

        status = "✓" if await_info.exception is None else "✗"
        msg = f"⌛ AWAIT END: {await_info.coro_name} {status}\n"
        msg += f"   File: {await_info.filename}:{await_info.lineno}\n"
        msg += f"   Duration: {await_info.duration_ms:.4f} ms\n"

        if await_info.exception:
            msg += f"   Exception: {type(await_info.exception).__name__}: {await_info.exception}\n"
        elif self.log_level <= LogLevel.DEBUG:
            try:
                result_repr = repr(await_info.result)
                if len(result_repr) > 100:
                    result_repr = result_repr[:100] + "..."
                msg += f"   Result: {result_repr}\n"
            except Exception:
                pass

        self._log_async(msg, "AWAIT")

    def _log_coro_start(self, coro_info: CoroutineInfo):
        """Log the start of a coroutine."""
        if self.log_level >= LogLevel.SILENT:
            return

        msg = f"🚀 COROUTINE START: {coro_info.name}\n"

        self._log_async(msg, "CORO")

    def _log_coro_end(self, coro_info: CoroutineInfo):
        """Log the end of a coroutine."""
        if self.log_level >= LogLevel.SILENT:
            return

        status = "✓" if coro_info.exception is None else "✗"
        msg = f"🏁 COROUTINE END: {coro_info.name} {status}\n"
        msg += f"   Total duration: {coro_info.duration_ms:.4f} ms\n"
        msg += f"   Await points: {len(coro_info.await_points)}\n"

        if coro_info.await_points:
            total_await_time = sum(ap.duration_ms for ap in coro_info.await_points)
            msg += f"   Total await time: {total_await_time:.4f} ms\n"

        if coro_info.exception:
            msg += f"   Exception: {type(coro_info.exception).__name__}: {coro_info.exception}\n"

        self._log_async(msg, "CORO")

    def _log_task_start(self, task_name: str):
        """Log asyncio task creation."""
        if self.log_level >= LogLevel.SILENT or not self.trace_tasks:
            return

        msg = f"📋 TASK CREATED: {task_name}\n"
        self._log_async(msg, "TASK")

    def _log_task_done(self, task_name: str, duration_ms: float, exception=None):
        """Log asyncio task completion."""
        if self.log_level >= LogLevel.SILENT or not self.trace_tasks:
            return

        status = "✓" if exception is None else "✗"
        msg = f"📋 TASK DONE: {task_name} {status}\n"
        msg += f"   Duration: {duration_ms:.4f} ms\n"
        if exception:
            msg += f"   Exception: {type(exception).__name__}: {exception}\n"

        self._log_async(msg, "TASK")

    def trace_async(self, coro_func: Callable) -> Callable:
        """
        Decorator to trace an async function.

        Example:
            tracer = AsyncTracer()

            @tracer.trace_async
            async def my_coroutine():
                await asyncio.sleep(0.1)
                return "done"
        """

        @functools.wraps(coro_func)
        async def wrapper(*args, **kwargs):
            # Ensure tracer is initialized
            if self._timer is None:
                self._initialize()
            coro = coro_func(*args, **kwargs)
            return await self._trace_coroutine(coro, coro_func.__name__)

        return wrapper

    async def _trace_coroutine(self, coro: Coroutine, name: str = None) -> Any:
        """Trace execution of a coroutine."""
        # Ensure tracer is initialized
        if self._timer is None:
            self._initialize()
            
        if name is None:
            name = getattr(coro, "__name__", str(coro))

        coro_info = CoroutineInfo(name, coro)
        self._coro_stack.append(coro_info)
        coro_id = id(coro)
        self._active_coroutines[coro_id] = coro_info

        self._log_coro_start(coro_info)

        try:
            result = await coro
            coro_info.complete(result=result)
            return result
        except Exception as e:
            coro_info.complete(exception=e)
            raise
        finally:
            self._log_coro_end(coro_info)
            self._active_coroutines.pop(coro_id, None)
            if self._coro_stack and self._coro_stack[-1] is coro_info:
                self._coro_stack.pop()

    def trace_await(self, awaitable: Any, expr: str = "") -> Any:
        """
        Wrapper to trace an await point explicitly.

        Example:
            tracer = AsyncTracer()

            async def my_func():
                # Instead of: result = await some_async_call()
                result = await tracer.trace_await(some_async_call(), "some_async_call()")
        """

        async def traced():
            # Get caller info
            frame = inspect.currentframe()
            caller_frame = frame.f_back.f_back if frame else None

            if caller_frame:
                filename = caller_frame.f_code.co_filename
                lineno = caller_frame.f_lineno
                coro_name = caller_frame.f_code.co_name
            else:
                filename = "<unknown>"
                lineno = 0
                coro_name = "<unknown>"

            await_info = AwaitPointInfo(coro_name, filename, lineno, expr)
            self._await_stack.append(await_info)

            # Add to current coroutine if available
            if self._coro_stack:
                self._coro_stack[-1].await_points.append(await_info)

            self._log_await_start(await_info)

            try:
                result = await awaitable
                await_info.complete(result=result)
                return result
            except Exception as e:
                await_info.complete(exception=e)
                raise
            finally:
                self._log_await_end(await_info)
                if self._await_stack and self._await_stack[-1] is await_info:
                    self._await_stack.pop()

        return traced()

    def wrap_task(self, coro: Coroutine, name: str = None) -> asyncio.Task:
        """
        Create a traced asyncio task.

        Example:
            tracer = AsyncTracer()
            task = tracer.wrap_task(my_coroutine(), "my_task")
        """
        if name is None:
            name = getattr(coro, "__name__", f"task_{id(coro)}")

        start_time = time.perf_counter()
        self._log_task_start(name)

        task = asyncio.create_task(self._trace_coroutine(coro, name))

        def on_done(t):
            duration_ms = (time.perf_counter() - start_time) * 1000
            exception = t.exception() if not t.cancelled() else None
            self._log_task_done(name, duration_ms, exception)

        task.add_done_callback(on_done)
        return task

    async def gather(self, *coros, return_exceptions: bool = False, **kwargs):
        """
        Traced version of asyncio.gather.

        Example:
            tracer = AsyncTracer()
            results = await tracer.gather(coro1(), coro2(), coro3())
        """
        traced_coros = []
        for i, coro in enumerate(coros):
            name = getattr(coro, "__name__", f"gather_task_{i}")
            traced_coros.append(self._trace_coroutine(coro, name))

        return await asyncio.gather(
            *traced_coros, return_exceptions=return_exceptions, **kwargs
        )

    def _run_tracer(self, frame, event, arg):
        """Extended tracer that also detects coroutine-related events."""
        # Handle standard line tracing
        if event == "line":
            try:
                self._log(frame)
            except Exception as e:
                print(e)
        elif event == "call":
            # Check if this is a coroutine function call
            code = frame.f_code
            if code.co_flags & inspect.CO_COROUTINE:
                # This is entering a coroutine
                if self.log_level <= LogLevel.DEBUG:
                    coro_info = CoroutineInfo(code.co_name, None)
                    self._coro_stack.append(coro_info)
                    self._log_coro_start(coro_info)
        elif event == "return":
            # Check if returning from a coroutine
            if self._coro_stack:
                code = frame.f_code
                if code.co_flags & inspect.CO_COROUTINE:
                    coro_info = self._coro_stack.pop()
                    coro_info.complete(result=arg)
                    self._log_coro_end(coro_info)

        self._timer = time.perf_counter()
        return self._run_tracer

    def _initialize(self):
        """Initialize async tracer state."""
        super()._initialize()
        self._async_step = 0
        self._active_coroutines = {}
        self._current_await = None
        self._await_stack = []
        self._coro_stack = []

    def trace(self, func: Callable) -> Callable:
        """
        Decorator for both sync and async functions.

        Automatically detects if the function is async and applies
        appropriate tracing.
        """
        if asyncio.iscoroutinefunction(func):
            return self.trace_async(func)
        else:
            return super().trace(func)

    async def run_async(self, coro: Coroutine) -> Any:
        """
        Run a coroutine with full tracing.

        This sets up the tracer and runs the coroutine.

        Example:
            tracer = AsyncTracer()
            result = await tracer.run_async(my_coroutine())
        """
        self._initialize()
        self._previous_trace = sys.gettrace()
        sys.settrace(self._run_tracer)

        try:
            return await self._trace_coroutine(coro)
        finally:
            sys.settrace(self._previous_trace)


class AsyncContextTracer:
    """
    Async context manager for tracing.

    Example:
        tracer = AsyncTracer()
        async with AsyncContextTracer(tracer):
            await my_coroutine()
    """

    def __init__(self, tracer: AsyncTracer):
        self.tracer = tracer

    async def __aenter__(self):
        self.tracer._initialize()
        self.tracer._previous_trace = sys.gettrace()
        sys.settrace(self.tracer._run_tracer)
        return self.tracer

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        sys.settrace(self.tracer._previous_trace)
        return False


def traced_sleep(tracer: AsyncTracer, seconds: float) -> Coroutine:
    """
    A traced version of asyncio.sleep.

    Example:
        tracer = AsyncTracer()
        await traced_sleep(tracer, 0.1)
    """
    return tracer.trace_await(asyncio.sleep(seconds), f"sleep({seconds})")
