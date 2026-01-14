"""
Test script for log level/verbosity options.
This tests different log levels: DEBUG, INFO, WARNING, ERROR, SILENT
"""

import os
import re
import shutil
import sys
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from steptrace import LogLevel, Tracer


def parse_log_steps(content):
    """Parse log content into individual steps with their components."""
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
                "global_vars": {},
                "local_vars": {},
            }
            in_global_vars = False
            in_local_vars = False
        elif current_step:
            # Parse runtime
            runtime_match = re.match(r"Runtime: ([\d.]+) ms", line)
            if runtime_match:
                current_step["runtime"] = float(runtime_match.group(1))

            # Parse file path and function
            path_match = re.match(r"(.+)::(\w+) -- line (\d+)", line)
            if path_match:
                current_step["file_path"] = path_match.group(1)
                current_step["function"] = path_match.group(2)
                current_step["line_num"] = int(path_match.group(3))

            # Track which variable section we're in
            if "------> Global variables <------" in line:
                in_global_vars = True
                in_local_vars = False
            elif "------> Local variables <------" in line:
                in_global_vars = False
                in_local_vars = True

            # Parse variable (format: "name: type :: value")
            var_match = re.match(r"^(\w+): (\w+) :: (.+)$", line)
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
    z = x + y
    return z


def test_log_level_debug():
    """Test DEBUG log level - most verbose with full validation."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_debug_")
    try:
        with Tracer(log_level=LogLevel.DEBUG, log_dir=log_dir):
            result = sample_function()

        assert result == 30, f"Function should return 30, got {result}"

        log_file = os.path.join(log_dir, "tracer.log")
        assert os.path.exists(log_file), "Log file should exist"

        with open(log_file, "r") as f:
            content = f.read()

        steps = parse_log_steps(content)

        # Should have multiple steps (at least for x=10, y=20, z=x+y, return)
        assert len(steps) >= 3, f"DEBUG should log multiple steps, got {len(steps)}"

        # Verify step numbers are sequential
        for i, step in enumerate(steps, 1):
            assert step["step_num"] == i, (
                f"Step numbers should be sequential, expected {i}, got {step['step_num']}"
            )

        # Verify runtime is present and is a valid number
        for step in steps:
            assert step["runtime"] is not None, "DEBUG should include runtime"
            assert step["runtime"] >= 0, (
                f"Runtime should be non-negative, got {step['runtime']}"
            )

        # Verify file path contains this test file's name
        for step in steps:
            assert step["file_path"] is not None, "DEBUG should include file path"
            assert "test_log_level" in step["file_path"], (
                f"File path should reference test file, got {step['file_path']}"
            )

        # Verify function name
        for step in steps:
            assert step["function"] == "sample_function", (
                f"Function name should be 'sample_function', got {step['function']}"
            )

        # Verify line numbers are reasonable (positive integers)
        for step in steps:
            assert step["line_num"] is not None, "DEBUG should include line numbers"
            assert step["line_num"] > 0, (
                f"Line number should be positive, got {step['line_num']}"
            )

        # Check that variables are logged - find step where z is defined
        z_logged = False
        for step in steps:
            if "z" in step["local_vars"]:
                z_logged = True
                assert step["local_vars"]["z"]["type"] == "int", (
                    f"z should be int, got {step['local_vars']['z']['type']}"
                )
                assert step["local_vars"]["z"]["value"] == "30", (
                    f"z should be 30, got {step['local_vars']['z']['value']}"
                )

        assert z_logged, "Variable z should be logged in at least one step"

        print("✓ test_log_level_debug passed")
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


def test_log_level_info():
    """Test INFO log level - standard verbosity with content validation."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_info_")
    try:
        with Tracer(log_level=LogLevel.INFO, log_dir=log_dir):
            result = sample_function()

        assert result == 30, f"Function should return 30, got {result}"

        log_file = os.path.join(log_dir, "tracer.log")
        assert os.path.exists(log_file), "Log file should exist"

        with open(log_file, "r") as f:
            content = f.read()

        steps = parse_log_steps(content)

        # INFO should have steps
        assert len(steps) >= 3, f"INFO should log multiple steps, got {len(steps)}"

        # Verify runtime is included at INFO level
        for step in steps:
            assert step["runtime"] is not None, "INFO should include runtime"

        # Verify file/function info is included
        for step in steps:
            assert step["file_path"] is not None, "INFO should include file path"
            assert step["function"] is not None, "INFO should include function name"
            assert step["line_num"] is not None, "INFO should include line numbers"

        # Verify variable x is logged with correct value after first step
        x_found = False
        for step in steps:
            if "x" in step["local_vars"]:
                x_found = True
                assert step["local_vars"]["x"]["type"] == "int", "x should be int"
                # x could be 10 initially
                break

        assert x_found, "Variable x should be logged"

        print("✓ test_log_level_info passed")
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


def test_log_level_warning():
    """Test WARNING log level - same as INFO (step info, runtime, variables)."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_warning_")
    try:
        with Tracer(log_level=LogLevel.WARNING, log_dir=log_dir):
            result = sample_function()

        assert result == 30, f"Function should return 30, got {result}"

        log_file = os.path.join(log_dir, "tracer.log")
        assert os.path.exists(log_file), "Log file should exist"

        with open(log_file, "r") as f:
            content = f.read()

        steps = parse_log_steps(content)

        # WARNING should have steps (same as INFO)
        assert len(steps) >= 3, f"WARNING should log multiple steps, got {len(steps)}"

        # Verify runtime is included (same as INFO)
        for step in steps:
            assert step["runtime"] is not None, "WARNING should include runtime"

        # Verify file/function info is included (same as INFO)
        for step in steps:
            assert step["file_path"] is not None, "WARNING should include file path"
            assert step["function"] is not None, "WARNING should include function name"
            assert step["line_num"] is not None, "WARNING should include line numbers"

        # Verify variable x is logged with correct value after first step (same as INFO)
        x_found = False
        for step in steps:
            if "x" in step["local_vars"]:
                x_found = True
                assert step["local_vars"]["x"]["type"] == "int", "x should be int"
                break

        assert x_found, "Variable x should be logged"

        print("✓ test_log_level_warning passed")
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


def test_log_level_silent():
    """Test SILENT log level - absolutely no output."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_silent_")
    try:
        with Tracer(log_level=LogLevel.SILENT, log_dir=log_dir):
            result = sample_function()

        # Function should still work correctly
        assert result == 30, (
            f"Function should return 30 even with SILENT logging, got {result}"
        )

        log_file = os.path.join(log_dir, "tracer.log")

        # File might exist but MUST be empty
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                content = f.read()
            assert content == "", (
                f"SILENT should produce empty file, got {len(content)} chars"
            )

        print("✓ test_log_level_silent passed")
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


def test_log_level_using_int():
    """Test that log levels can be specified using integers with validation."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_int_")
    try:
        # Use integer value for INFO (20)
        with Tracer(log_level=20, log_dir=log_dir):
            result = sample_function()

        assert result == 30, f"Function should return 30, got {result}"

        log_file = os.path.join(log_dir, "tracer.log")
        assert os.path.exists(log_file), "Log file should exist"

        with open(log_file, "r") as f:
            content = f.read()

        steps = parse_log_steps(content)

        # Integer 20 = INFO, should behave like INFO
        assert len(steps) >= 3, "Integer log level 20 should work like INFO"

        # Variables should be logged at level 20 (INFO)
        has_vars = any(step["local_vars"] or step["global_vars"] for step in steps)
        assert has_vars, "Integer level 20 (INFO) should log variables"

        print("✓ test_log_level_using_int passed")
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


def test_log_level_step_count_consistency():
    """Test that step counts are consistent across log levels."""
    log_dir_debug = tempfile.mkdtemp(prefix="tracer_test_count_debug_")
    log_dir_info = tempfile.mkdtemp(prefix="tracer_test_count_info_")
    log_dir_warning = tempfile.mkdtemp(prefix="tracer_test_count_warning_")

    try:
        with Tracer(log_level=LogLevel.DEBUG, log_dir=log_dir_debug):
            sample_function()

        with Tracer(log_level=LogLevel.INFO, log_dir=log_dir_info):
            sample_function()

        with Tracer(log_level=LogLevel.WARNING, log_dir=log_dir_warning):
            sample_function()

        with open(os.path.join(log_dir_debug, "tracer.log"), "r") as f:
            debug_steps = parse_log_steps(f.read())

        with open(os.path.join(log_dir_info, "tracer.log"), "r") as f:
            info_steps = parse_log_steps(f.read())

        with open(os.path.join(log_dir_warning, "tracer.log"), "r") as f:
            warning_steps = parse_log_steps(f.read())

        # All levels should trace the same number of steps
        assert len(debug_steps) == len(info_steps), (
            f"DEBUG and INFO should have same step count: {len(debug_steps)} vs {len(info_steps)}"
        )
        assert len(info_steps) == len(warning_steps), (
            f"INFO and WARNING should have same step count: {len(info_steps)} vs {len(warning_steps)}"
        )

        print("✓ test_log_level_step_count_consistency passed")
    finally:
        shutil.rmtree(log_dir_debug, ignore_errors=True)
        shutil.rmtree(log_dir_info, ignore_errors=True)
        shutil.rmtree(log_dir_warning, ignore_errors=True)


def test_log_level_runtime_format():
    """Test that runtime is properly formatted as milliseconds."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_runtime_")
    try:
        with Tracer(log_level=LogLevel.INFO, log_dir=log_dir):
            sample_function()

        log_file = os.path.join(log_dir, "tracer.log")
        with open(log_file, "r") as f:
            content = f.read()

        # Find all runtime entries
        runtime_pattern = r"Runtime: ([\d.]+) ms"
        runtimes = re.findall(runtime_pattern, content)

        assert len(runtimes) > 0, "Should have runtime entries"

        for runtime_str in runtimes:
            runtime = float(runtime_str)
            # Runtime should be a reasonable value (less than 1000ms for simple operations)
            assert 0 <= runtime < 1000, f"Runtime {runtime}ms seems unreasonable"
            # Check format has exactly 4 decimal places
            assert "." in runtime_str, "Runtime should have decimal point"
            decimal_places = len(runtime_str.split(".")[1])
            assert decimal_places == 4, (
                f"Runtime should have 4 decimal places, got {decimal_places}"
            )

        print("✓ test_log_level_runtime_format passed")
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


def test_log_level_line_numbers_increase():
    """Test that line numbers generally increase through execution."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_lines_")
    try:
        with Tracer(log_level=LogLevel.INFO, log_dir=log_dir):
            sample_function()

        log_file = os.path.join(log_dir, "tracer.log")
        with open(log_file, "r") as f:
            content = f.read()

        steps = parse_log_steps(content)

        # Get line numbers
        line_nums = [s["line_num"] for s in steps if s["line_num"] is not None]

        assert len(line_nums) >= 3, "Should have multiple line numbers"

        # Line numbers should generally increase (allow for some variation due to function calls)
        # At minimum, they should all be positive and within a reasonable range
        for ln in line_nums:
            assert 1 <= ln <= 500, f"Line number {ln} seems unreasonable"

        # First and last should show progression
        assert line_nums[-1] >= line_nums[0], "Line numbers should generally progress"

        print("✓ test_log_level_line_numbers_increase passed")
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


if __name__ == "__main__":
    print("Testing Log Level Options")
    print("=" * 50)
    test_log_level_debug()
    test_log_level_info()
    test_log_level_warning()
    test_log_level_silent()
    test_log_level_using_int()
    test_log_level_step_count_consistency()
    test_log_level_runtime_format()
    test_log_level_line_numbers_increase()
    print("=" * 50)
    print("All log level tests passed!")
