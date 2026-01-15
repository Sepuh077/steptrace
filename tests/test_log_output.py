"""
Test script for log output destination options.
This tests different output destinations: FILE, STDOUT, STDERR, FILE_STDOUT, FILE_STDERR
"""

import os
import re
import shutil
import sys
import tempfile
from io import StringIO

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from steptrace import LogOutput, Tracer


def parse_log_steps(content):
    """Parse log content into individual steps."""
    steps = []
    current_step = None

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
            }
        elif current_step:
            runtime_match = re.match(r"Runtime: ([\d.]+) ms", line)
            if runtime_match:
                current_step["runtime"] = float(runtime_match.group(1))

            path_match = re.match(r"(.+)::(\w+) -- line (\d+)", line)
            if path_match:
                current_step["file_path"] = path_match.group(1)
                current_step["function"] = path_match.group(2)

    if current_step:
        steps.append(current_step)

    return steps


def sample_function():
    """A simple function to trace."""
    x = 10
    y = 20
    z = x + y
    return z


def test_log_output_file():
    """Test FILE output - log to file only, nothing to stdout."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_file_")

    # Capture stdout to verify nothing is printed
    old_stdout = sys.stdout
    captured_stdout = StringIO()
    sys.stdout = captured_stdout

    try:
        with Tracer(log_output=LogOutput.FILE, log_dir=log_dir):
            result = sample_function()

        sys.stdout = old_stdout
        stdout_content = captured_stdout.getvalue()

        # Function should work correctly
        assert result == 30, f"Function should return 30, got {result}"

        # Log file should exist and have content
        log_file = os.path.join(log_dir, "tracer.log")
        assert os.path.exists(log_file), "Log file should exist for FILE output"

        with open(log_file, "r") as f:
            file_content = f.read()

        # Verify file has actual log content
        steps = parse_log_steps(file_content)
        assert len(steps) >= 3, f"File should contain multiple steps, got {len(steps)}"

        # Verify step structure in file
        for i, step in enumerate(steps, 1):
            assert step["step_num"] == i, f"Step {i} should have correct number"
            assert step["runtime"] is not None, f"Step {i} should have runtime"
            assert step["function"] == "sample_function", (
                f"Step {i} should have correct function"
            )

        # STDOUT should be completely empty
        assert stdout_content == "", (
            f"STDOUT should be empty for FILE output, got: {repr(stdout_content)}"
        )

        print("✓ test_log_output_file passed")
    finally:
        sys.stdout = old_stdout
        shutil.rmtree(log_dir, ignore_errors=True)


def test_log_output_stdout():
    """Test STDOUT output - log to stdout only, no file created."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_stdout_")

    # Capture stdout
    old_stdout = sys.stdout
    captured_stdout = StringIO()
    sys.stdout = captured_stdout

    try:
        with Tracer(log_output=LogOutput.STDOUT, log_dir=log_dir):
            result = sample_function()

        sys.stdout = old_stdout
        stdout_content = captured_stdout.getvalue()

        # Function should work correctly
        assert result == 30, f"Function should return 30, got {result}"

        # Verify stdout has actual log content
        steps = parse_log_steps(stdout_content)
        assert len(steps) >= 3, (
            f"STDOUT should contain multiple steps, got {len(steps)}"
        )

        # Verify step structure in stdout
        for i, step in enumerate(steps, 1):
            assert step["step_num"] == i, f"Step {i} should have correct number"
            assert step["runtime"] is not None, f"Step {i} should have runtime"
            assert step["function"] == "sample_function", (
                f"Step {i} should have correct function"
            )

        # Verify file path in output references this test file
        assert "test_log_output" in stdout_content, "Output should reference test file"

        # No log file should be created for STDOUT only
        log_file = os.path.join(log_dir, "tracer.log")
        assert not os.path.exists(log_file), (
            "No log file should be created for STDOUT only"
        )

        print("✓ test_log_output_stdout passed")
    finally:
        sys.stdout = old_stdout
        shutil.rmtree(log_dir, ignore_errors=True)


def test_log_output_stderr():
    """Test STDERR output - log to stderr only, no file created."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_stderr_")

    # Capture stderr
    old_stderr = sys.stderr
    captured_stderr = StringIO()
    sys.stderr = captured_stderr

    try:
        with Tracer(log_output=LogOutput.STDERR, log_dir=log_dir):
            result = sample_function()

        sys.stderr = old_stderr
        stderr_content = captured_stderr.getvalue()

        # Function should work correctly
        assert result == 30, f"Function should return 30, got {result}"

        # Verify stderr has actual log content
        steps = parse_log_steps(stderr_content)
        assert len(steps) >= 3, (
            f"STDERR should contain multiple steps, got {len(steps)}"
        )

        # Verify step structure in stderr
        for i, step in enumerate(steps, 1):
            assert step["step_num"] == i, f"Step {i} should have correct number"
            assert step["runtime"] is not None, f"Step {i} should have runtime"

        # No log file should be created for STDERR only
        log_file = os.path.join(log_dir, "tracer.log")
        assert not os.path.exists(log_file), (
            "No log file should be created for STDERR only"
        )

        print("✓ test_log_output_stderr passed")
    finally:
        sys.stderr = old_stderr
        shutil.rmtree(log_dir, ignore_errors=True)


def test_log_output_file_stdout():
    """Test FILE_STDOUT output - log to both file and stdout with identical content."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_file_stdout_")

    # Capture stdout
    old_stdout = sys.stdout
    captured_stdout = StringIO()
    sys.stdout = captured_stdout

    try:
        with Tracer(log_output=LogOutput.FILE_STDOUT, log_dir=log_dir):
            result = sample_function()

        sys.stdout = old_stdout
        stdout_content = captured_stdout.getvalue()

        # Function should work correctly
        assert result == 30, f"Function should return 30, got {result}"

        # Log file should exist
        log_file = os.path.join(log_dir, "tracer.log")
        assert os.path.exists(log_file), "Log file should exist for FILE_STDOUT"

        with open(log_file, "r") as f:
            file_content = f.read()

        # Both outputs should have content
        file_steps = parse_log_steps(file_content)
        stdout_steps = parse_log_steps(stdout_content)

        assert len(file_steps) >= 3, (
            f"File should have multiple steps, got {len(file_steps)}"
        )
        assert len(stdout_steps) >= 3, (
            f"STDOUT should have multiple steps, got {len(stdout_steps)}"
        )

        # Both should have the SAME number of steps
        assert len(file_steps) == len(stdout_steps), (
            f"File and STDOUT should have same step count: {len(file_steps)} vs {len(stdout_steps)}"
        )

        # Content should be identical
        assert file_content == stdout_content, (
            "File and STDOUT content should be identical"
        )

        # Verify structure matches
        for i, (file_step, stdout_step) in enumerate(zip(file_steps, stdout_steps)):
            assert file_step["step_num"] == stdout_step["step_num"], (
                f"Step numbers should match at position {i}"
            )
            assert file_step["function"] == stdout_step["function"], (
                f"Function names should match at position {i}"
            )

        print("✓ test_log_output_file_stdout passed")
    finally:
        sys.stdout = old_stdout
        shutil.rmtree(log_dir, ignore_errors=True)


def test_log_output_file_stderr():
    """Test FILE_STDERR output - log to both file and stderr with identical content."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_file_stderr_")

    # Capture stderr
    old_stderr = sys.stderr
    captured_stderr = StringIO()
    sys.stderr = captured_stderr

    try:
        with Tracer(log_output=LogOutput.FILE_STDERR, log_dir=log_dir):
            result = sample_function()

        sys.stderr = old_stderr
        stderr_content = captured_stderr.getvalue()

        # Function should work correctly
        assert result == 30, f"Function should return 30, got {result}"

        # Log file should exist
        log_file = os.path.join(log_dir, "tracer.log")
        assert os.path.exists(log_file), "Log file should exist for FILE_STDERR"

        with open(log_file, "r") as f:
            file_content = f.read()

        # Both outputs should have content
        file_steps = parse_log_steps(file_content)
        stderr_steps = parse_log_steps(stderr_content)

        assert len(file_steps) >= 3, "File should have multiple steps"
        assert len(stderr_steps) >= 3, "STDERR should have multiple steps"

        # Both should have the SAME number of steps
        assert len(file_steps) == len(stderr_steps), (
            f"File and STDERR should have same step count: {len(file_steps)} vs {len(stderr_steps)}"
        )

        # Content should be identical
        assert file_content == stderr_content, (
            "File and STDERR content should be identical"
        )

        print("✓ test_log_output_file_stderr passed")
    finally:
        sys.stderr = old_stderr
        shutil.rmtree(log_dir, ignore_errors=True)


def test_log_output_using_int():
    """Test that log output can be specified using integers."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_int_output_")

    old_stdout = sys.stdout
    captured_stdout = StringIO()
    sys.stdout = captured_stdout

    try:
        # Use integer value for STDOUT (2)
        with Tracer(log_output=2, log_dir=log_dir):
            result = sample_function()

        sys.stdout = old_stdout
        stdout_content = captured_stdout.getvalue()

        assert result == 30, f"Function should return 30, got {result}"

        # Should work like STDOUT
        steps = parse_log_steps(stdout_content)
        assert len(steps) >= 3, "Integer output value 2 should work like STDOUT"

        # Verify actual step content
        assert steps[0]["step_num"] == 1, "First step should be 1"

        print("✓ test_log_output_using_int passed")
    finally:
        sys.stdout = old_stdout
        shutil.rmtree(log_dir, ignore_errors=True)


def test_log_output_stdout_no_stderr():
    """Test that STDOUT output doesn't leak to STDERR."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_no_leak_")

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    captured_stdout = StringIO()
    captured_stderr = StringIO()
    sys.stdout = captured_stdout
    sys.stderr = captured_stderr

    try:
        with Tracer(log_output=LogOutput.STDOUT, log_dir=log_dir):
            sample_function()

        sys.stdout = old_stdout
        sys.stderr = old_stderr

        stdout_content = captured_stdout.getvalue()
        stderr_content = captured_stderr.getvalue()

        # STDOUT should have content
        assert len(stdout_content) > 0, "STDOUT should have content"
        assert "Step" in stdout_content, "STDOUT should have step info"

        # STDERR should be empty
        assert stderr_content == "", (
            f"STDERR should be empty for STDOUT output, got: {repr(stderr_content)}"
        )

        print("✓ test_log_output_stdout_no_stderr passed")
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        shutil.rmtree(log_dir, ignore_errors=True)


def test_log_output_stderr_no_stdout():
    """Test that STDERR output doesn't leak to STDOUT."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_no_leak2_")

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    captured_stdout = StringIO()
    captured_stderr = StringIO()
    sys.stdout = captured_stdout
    sys.stderr = captured_stderr

    try:
        with Tracer(log_output=LogOutput.STDERR, log_dir=log_dir):
            sample_function()

        sys.stdout = old_stdout
        sys.stderr = old_stderr

        stdout_content = captured_stdout.getvalue()
        stderr_content = captured_stderr.getvalue()

        # STDERR should have content
        assert len(stderr_content) > 0, "STDERR should have content"
        assert "Step" in stderr_content, "STDERR should have step info"

        # STDOUT should be empty
        assert stdout_content == "", (
            f"STDOUT should be empty for STDERR output, got: {repr(stdout_content)}"
        )

        print("✓ test_log_output_stderr_no_stdout passed")
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        shutil.rmtree(log_dir, ignore_errors=True)


def test_log_output_file_path_format():
    """Test that file paths in output are absolute and valid."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_paths_")

    old_stdout = sys.stdout
    captured_stdout = StringIO()
    sys.stdout = captured_stdout

    try:
        with Tracer(log_output=LogOutput.STDOUT, log_dir=log_dir):
            sample_function()

        sys.stdout = old_stdout
        stdout_content = captured_stdout.getvalue()

        steps = parse_log_steps(stdout_content)

        for step in steps:
            file_path = step["file_path"]
            assert file_path is not None, "File path should not be None"

            # Path should be absolute (starts with /)
            assert file_path.startswith("/") or file_path[1:3] == ":\\", (
                f"File path should be absolute, got: {file_path}"
            )

            # Path should end with .py
            assert file_path.endswith(".py"), (
                f"File path should end with .py, got: {file_path}"
            )

            # Path should actually exist
            assert os.path.exists(file_path), f"File path should exist: {file_path}"

        print("✓ test_log_output_file_path_format passed")
    finally:
        sys.stdout = old_stdout
        shutil.rmtree(log_dir, ignore_errors=True)


if __name__ == "__main__":
    print("Testing Log Output Options")
    print("=" * 50)
    test_log_output_file()
    test_log_output_stdout()
    test_log_output_stderr()
    test_log_output_file_stdout()
    test_log_output_file_stderr()
    test_log_output_using_int()
    test_log_output_stdout_no_stderr()
    test_log_output_stderr_no_stdout()
    test_log_output_file_path_format()
    print("=" * 50)
    print("All log output tests passed!")
