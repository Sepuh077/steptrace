"""
Comprehensive test script that tests all options together.
Tests combinations of log levels, output destinations, and variable modes.
"""

import os
import re
import shutil
import sys
import tempfile
from io import StringIO

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from steptrace import LogLevel, LogOutput, Tracer, VariableMode


def parse_log_steps(content):
    """Parse log content into individual steps."""
    steps = []
    current_step = None
    in_global_vars = False
    in_local_vars = False

    for line in content.split("\n"):
        step_match = re.match(r"-+ Step (\d+) -+", line)
        if step_match:
            if current_step:
                steps.append(current_step)
            current_step = {
                "step_num": int(step_match.group(1)),
                "runtime": None,
                "file_path": None,
                "function": None,
                "line_num": None,
                "local_vars": {},
                "global_vars": {},
                "has_new_marker": False,
                "has_changed_marker": False,
            }
            in_global_vars = False
            in_local_vars = False
        elif current_step:
            runtime_match = re.match(r"Runtime: ([\d.]+) ms", line)
            if runtime_match:
                current_step["runtime"] = float(runtime_match.group(1))

            path_match = re.match(r"(.+)::(\w+) -- line (\d+)", line)
            if path_match:
                current_step["file_path"] = path_match.group(1)
                current_step["function"] = path_match.group(2)
                current_step["line_num"] = int(path_match.group(3))

            if (
                "------> Global variables <------" in line
                or "------> Global variable changes <------" in line
            ):
                in_global_vars = True
                in_local_vars = False
            elif (
                "------> Local variables <------" in line
                or "------> Local variable changes <------" in line
            ):
                in_global_vars = False
                in_local_vars = True

            if "[NEW]" in line:
                current_step["has_new_marker"] = True
            if "[CHANGED]" in line:
                current_step["has_changed_marker"] = True

            # Parse variable
            var_match = re.match(
                r"^(?:\[(?:NEW|CHANGED|DELETED)\] )?(\w+): (\w+) :: (.+)$", line
            )
            if var_match:
                var_name = var_match.group(1)
                var_type = var_match.group(2)
                var_value = var_match.group(3)
                if in_global_vars:
                    current_step["global_vars"][var_name] = {
                        "type": var_type,
                        "value": var_value,
                    }
                elif in_local_vars:
                    current_step["local_vars"][var_name] = {
                        "type": var_type,
                        "value": var_value,
                    }

    if current_step:
        steps.append(current_step)

    return steps


def sample_function():
    """A simple function to trace."""
    x = 10
    y = 20
    x = 15  # Change x
    z = x + y
    return z


def test_combined_debug_stdout_all():
    """Test DEBUG level + STDOUT output + ALL variables with full validation."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_combo1_")
    old_stdout = sys.stdout
    captured_stdout = StringIO()
    sys.stdout = captured_stdout

    try:
        with Tracer(
            log_level=LogLevel.DEBUG,
            log_output=LogOutput.STDOUT,
            variable_mode=VariableMode.ALL,
            log_dir=log_dir,
        ):
            result = sample_function()

        sys.stdout = old_stdout
        stdout_content = captured_stdout.getvalue()

        assert result == 35, f"Function should return 35, got {result}"

        steps = parse_log_steps(stdout_content)

        # DEBUG + STDOUT should have all info
        assert len(steps) >= 4, f"Should have at least 4 steps, got {len(steps)}"

        for step in steps:
            # DEBUG should have all components
            assert step["runtime"] is not None, (
                f"DEBUG should include runtime in step {step['step_num']}"
            )
            assert step["file_path"] is not None, (
                f"DEBUG should include file path in step {step['step_num']}"
            )
            assert step["function"] is not None, (
                f"DEBUG should include function in step {step['step_num']}"
            )

        # ALL variable mode should show variables
        has_vars = any(step["local_vars"] for step in steps)
        assert has_vars, "ALL variable mode should log local variables"

        # Verify z value
        z_found = False
        for step in steps:
            if "z" in step["local_vars"]:
                z_found = True
                assert step["local_vars"]["z"]["value"] == "35", f"z should be 35"
        assert z_found, "Variable z should be logged"

        # No file should be created (STDOUT only)
        log_file = os.path.join(log_dir, "tracer.log")
        assert not os.path.exists(log_file), (
            "No log file should be created for STDOUT only"
        )

        print("✓ test_combined_debug_stdout_all passed")
    finally:
        sys.stdout = old_stdout
        shutil.rmtree(log_dir, ignore_errors=True)


def test_combined_info_file_changed():
    """Test INFO level + FILE output + CHANGED variables with value tracking."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_combo2_")

    try:
        with Tracer(
            log_level=LogLevel.INFO,
            log_output=LogOutput.FILE,
            variable_mode=VariableMode.CHANGED,
            log_dir=log_dir,
        ):
            result = sample_function()

        assert result == 35, f"Function should return 35, got {result}"

        log_file = os.path.join(log_dir, "tracer.log")
        assert os.path.exists(log_file), "Log file should exist"

        with open(log_file, "r") as f:
            content = f.read()

        steps = parse_log_steps(content)

        # INFO level should include file/function
        for step in steps:
            assert step["runtime"] is not None, "INFO should include runtime"
            assert step["file_path"] is not None, "INFO should include file path"

        # CHANGED mode should have markers
        has_markers = any(
            step["has_new_marker"] or step["has_changed_marker"] for step in steps
        )
        assert has_markers, "CHANGED mode should have [NEW] or [CHANGED] markers"

        # Verify x change from 10 to 15 is logged
        assert "[CHANGED] x: int :: 10 -> 15" in content, (
            "Should log x changing from 10 to 15"
        )

        print("✓ test_combined_info_file_changed passed")
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


def test_combined_warning_stderr_none():
    """Test WARNING level + STDERR output + NONE variables."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_combo3_")
    old_stderr = sys.stderr
    captured_stderr = StringIO()
    sys.stderr = captured_stderr

    try:
        with Tracer(
            log_level=LogLevel.WARNING,
            log_output=LogOutput.STDERR,
            variable_mode=VariableMode.NONE,
            log_dir=log_dir,
        ):
            result = sample_function()

        sys.stderr = old_stderr
        stderr_content = captured_stderr.getvalue()

        assert result == 35, f"Function should return 35, got {result}"

        steps = parse_log_steps(stderr_content)

        # WARNING level should have steps (same as INFO)
        assert len(steps) >= 4, "Should have steps"

        for step in steps:
            # WARNING is same as INFO - includes runtime, file path, and function
            assert step["runtime"] is not None, "WARNING should include runtime"
            assert step["file_path"] is not None, "WARNING should include file path"
            assert step["function"] is not None, "WARNING should include function"

        # NONE variable mode should have no variables
        for step in steps:
            assert len(step["local_vars"]) == 0, (
                "NONE mode should not log local variables"
            )
            assert len(step["global_vars"]) == 0, (
                "NONE mode should not log global variables"
            )

        # No file should be created (STDERR only)
        log_file = os.path.join(log_dir, "tracer.log")
        assert not os.path.exists(log_file), (
            "No log file should be created for STDERR only"
        )

        print("✓ test_combined_warning_stderr_none passed")
    finally:
        sys.stderr = old_stderr
        shutil.rmtree(log_dir, ignore_errors=True)


def test_combined_info_file_stdout_all():
    """Test INFO level + FILE_STDOUT output + ALL variables - verify identical content."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_combo4_")
    old_stdout = sys.stdout
    captured_stdout = StringIO()
    sys.stdout = captured_stdout

    try:
        with Tracer(
            log_level=LogLevel.INFO,
            log_output=LogOutput.FILE_STDOUT,
            variable_mode=VariableMode.ALL,
            log_dir=log_dir,
        ):
            result = sample_function()

        sys.stdout = old_stdout
        stdout_content = captured_stdout.getvalue()

        assert result == 35, f"Function should return 35, got {result}"

        log_file = os.path.join(log_dir, "tracer.log")
        assert os.path.exists(log_file), "Log file should exist"

        with open(log_file, "r") as f:
            file_content = f.read()

        # Both outputs should be identical
        assert file_content == stdout_content, (
            "FILE and STDOUT content should be identical"
        )

        # Parse and verify content
        steps = parse_log_steps(file_content)
        assert len(steps) >= 4, "Should have steps"

        # Verify variable values
        for step in steps:
            if "z" in step["local_vars"]:
                assert step["local_vars"]["z"]["value"] == "35", "z should be 35"

        print("✓ test_combined_info_file_stdout_all passed")
    finally:
        sys.stdout = old_stdout
        shutil.rmtree(log_dir, ignore_errors=True)


def test_silent_produces_no_output():
    """Test SILENT level produces no output with any combination."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_silent_combo_")
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    captured_stdout = StringIO()
    captured_stderr = StringIO()
    sys.stdout = captured_stdout
    sys.stderr = captured_stderr

    try:
        with Tracer(
            log_level=LogLevel.SILENT,
            log_output=LogOutput.FILE_STDOUT,
            variable_mode=VariableMode.ALL,
            log_dir=log_dir,
        ):
            result = sample_function()

        sys.stdout = old_stdout
        sys.stderr = old_stderr

        # Function should still work
        assert result == 35, f"Function should return 35, got {result}"

        # No output to stdout
        assert captured_stdout.getvalue() == "", (
            "SILENT should produce no stdout output"
        )

        # No output to stderr (nothing should use it)
        # (Note: errors during tracing might still go to stderr)

        # File should be empty if exists
        log_file = os.path.join(log_dir, "tracer.log")
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                file_content = f.read()
            assert file_content == "", "SILENT should produce no file output"

        print("✓ test_silent_produces_no_output passed")
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        shutil.rmtree(log_dir, ignore_errors=True)


def test_decorator_with_options():
    """Test that options work correctly with decorator usage."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_decorator_")

    try:
        tracer = Tracer(
            log_level=LogLevel.INFO,
            log_output=LogOutput.FILE,
            variable_mode=VariableMode.CHANGED,
            log_dir=log_dir,
        )

        @tracer.trace
        def decorated_function():
            a = 1
            b = 2
            a = 10  # Change a
            c = a + b
            return c

        result = decorated_function()

        assert result == 12, f"Decorated function should return 12, got {result}"

        log_file = os.path.join(log_dir, "tracer.log")
        assert os.path.exists(log_file), "Log file should exist"

        with open(log_file, "r") as f:
            content = f.read()

        steps = parse_log_steps(content)
        assert len(steps) >= 3, "Should have multiple steps"

        # CHANGED mode should show change markers
        assert "[NEW]" in content, "Should have [NEW] markers"
        assert "[CHANGED]" in content, "Should have [CHANGED] markers for a"

        # Verify the change from 1 to 10
        assert "1 -> 10" in content, "Should show a changing from 1 to 10"

        print("✓ test_decorator_with_options passed")
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


def test_default_values():
    """Test that default values work correctly."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_default_")

    try:
        # Use all defaults except log_dir
        with Tracer(log_dir=log_dir):
            result = sample_function()

        assert result == 35, f"Function should return 35, got {result}"

        log_file = os.path.join(log_dir, "tracer.log")
        assert os.path.exists(log_file), "Log file should exist with defaults"

        with open(log_file, "r") as f:
            content = f.read()

        # Default should be INFO level (has file path, function, runtime)
        steps = parse_log_steps(content)
        for step in steps:
            assert step["runtime"] is not None, "Default INFO should have runtime"
            assert step["file_path"] is not None, "Default INFO should have file path"
            assert step["function"] is not None, "Default INFO should have function"

        # Default should be FILE output (file exists, which we checked)

        # Default should be ALL variable mode (shows all vars each step)
        assert "Local variables" in content, (
            "Default ALL mode should show 'Local variables'"
        )

        # Should NOT have change markers (that's CHANGED mode)
        assert "[NEW]" not in content, "Default ALL mode should not use [NEW] markers"
        assert "[CHANGED]" not in content, (
            "Default ALL mode should not use [CHANGED] markers"
        )

        print("✓ test_default_values passed")
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


def test_incremental_log_files():
    """Test that log files are properly incremented."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_increment_")

    try:
        # Create first log
        with Tracer(log_dir=log_dir):
            sample_function()

        # Create second log
        with Tracer(log_dir=log_dir):
            sample_function()

        # Create third log
        with Tracer(log_dir=log_dir):
            sample_function()

        # Verify files exist
        assert os.path.exists(os.path.join(log_dir, "tracer.log")), (
            "First log should exist"
        )
        assert os.path.exists(os.path.join(log_dir, "tracer_1.log")), (
            "Second log should exist"
        )
        assert os.path.exists(os.path.join(log_dir, "tracer_2.log")), (
            "Third log should exist"
        )

        # Verify each file has content and is independent
        for log_name in ["tracer.log", "tracer_1.log", "tracer_2.log"]:
            log_path = os.path.join(log_dir, log_name)
            with open(log_path, "r") as f:
                content = f.read()

            steps = parse_log_steps(content)
            assert len(steps) >= 3, f"{log_name} should have steps"

            # Each file should start fresh with Step 1
            assert steps[0]["step_num"] == 1, f"{log_name} should start with Step 1"

        print("✓ test_incremental_log_files passed")
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


def test_function_execution_not_affected():
    """Test that tracing doesn't affect function return values or behavior."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_exec_")

    def complex_function():
        result = []
        for i in range(5):
            result.append(i * 2)
        total = sum(result)
        return total, result

    try:
        # Run without tracing
        expected_total, expected_result = complex_function()

        # Run with various tracing options
        with Tracer(log_level=LogLevel.DEBUG, log_dir=log_dir):
            debug_total, debug_result = complex_function()

        with Tracer(
            log_level=LogLevel.INFO, variable_mode=VariableMode.CHANGED, log_dir=log_dir
        ):
            info_total, info_result = complex_function()

        with Tracer(log_level=LogLevel.SILENT, log_dir=log_dir):
            silent_total, silent_result = complex_function()

        # All should produce identical results
        assert debug_total == expected_total, (
            f"DEBUG tracing shouldn't affect result: {debug_total} vs {expected_total}"
        )
        assert debug_result == expected_result, "DEBUG tracing shouldn't affect list"

        assert info_total == expected_total, "INFO tracing shouldn't affect result"
        assert info_result == expected_result, "INFO tracing shouldn't affect list"

        assert silent_total == expected_total, "SILENT tracing shouldn't affect result"
        assert silent_result == expected_result, "SILENT tracing shouldn't affect list"

        print("✓ test_function_execution_not_affected passed")
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


def test_nested_function_calls():
    """Test tracing with nested function calls."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_nested_")

    def inner_func(n):
        result = n * 2
        return result

    def outer_func():
        a = 5
        b = inner_func(a)
        c = b + 10
        return c

    try:
        with Tracer(log_level=LogLevel.INFO, log_dir=log_dir):
            result = outer_func()

        assert result == 20, f"Nested functions should work: expected 20, got {result}"

        log_file = os.path.join(log_dir, "tracer.log")
        with open(log_file, "r") as f:
            content = f.read()

        # Should see both functions in output
        assert "outer_func" in content, "Should trace outer_func"
        assert "inner_func" in content, "Should trace inner_func"

        # Verify correct values in inner function
        assert "result: int :: 10" in content, "inner_func should have result=10"

        print("✓ test_nested_function_calls passed")
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


if __name__ == "__main__":
    print("Testing All Options Combined")
    print("=" * 50)
    test_combined_debug_stdout_all()
    test_combined_info_file_changed()
    test_combined_warning_stderr_none()
    test_combined_info_file_stdout_all()
    test_silent_produces_no_output()
    test_decorator_with_options()
    test_default_values()
    test_incremental_log_files()
    test_function_execution_not_affected()
    test_nested_function_calls()
    print("=" * 50)
    print("All combined tests passed!")
