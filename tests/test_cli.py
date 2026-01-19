#!/usr/bin/env python3
"""
Comprehensive tests for the CLI functionality.
Tests all CLI parameters including config file support (YAML/TOML).
"""

import os
import shutil
import subprocess
import sys
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_test_script(directory: str, name: str = "test_script.py") -> str:
    """Create a simple test script."""
    script_path = os.path.join(directory, name)
    with open(script_path, "w") as f:
        f.write('''#!/usr/bin/env python3
def calculate(a, b):
    return a + b

def main():
    x = 10
    y = 20
    z = calculate(x, y)
    print(f"Result: {z}")
    return 0

if __name__ == "__main__":
    main()
''')
    return script_path


def create_async_test_script(directory: str, name: str = "async_script.py") -> str:
    """Create an async test script."""
    script_path = os.path.join(directory, name)
    with open(script_path, "w") as f:
        f.write('''#!/usr/bin/env python3
import asyncio

async def fetch_data():
    await asyncio.sleep(0.01)
    return "data"

async def main():
    result = await fetch_data()
    print(f"Async Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
''')
    return script_path


def create_yaml_config(directory: str, config: dict, name: str = "steptrace.yaml") -> str:
    """Create a YAML config file."""
    config_path = os.path.join(directory, name)
    with open(config_path, "w") as f:
        for key, value in config.items():
            if isinstance(value, bool):
                f.write(f"{key}: {'true' if value else 'false'}\n")
            elif isinstance(value, (int, float)):
                f.write(f"{key}: {value}\n")
            elif isinstance(value, list):
                f.write(f"{key}:\n")
                for item in value:
                    f.write(f"  - {item}\n")
            else:
                f.write(f"{key}: {value}\n")
    return config_path


def create_toml_config(directory: str, config: dict, name: str = "steptrace.toml") -> str:
    """Create a TOML config file."""
    config_path = os.path.join(directory, name)
    with open(config_path, "w") as f:
        for key, value in config.items():
            if isinstance(value, bool):
                f.write(f'{key} = {"true" if value else "false"}\n')
            elif isinstance(value, str):
                f.write(f'{key} = "{value}"\n')
            elif isinstance(value, (int, float)):
                f.write(f"{key} = {value}\n")
            elif isinstance(value, list):
                items = ", ".join(f'"{item}"' for item in value)
                f.write(f"{key} = [{items}]\n")
    return config_path


def create_pyproject_toml(directory: str, config: dict) -> str:
    """Create a pyproject.toml with [tool.steptrace] section."""
    config_path = os.path.join(directory, "pyproject.toml")
    with open(config_path, "w") as f:
        f.write('[project]\nname = "test"\nversion = "1.0.0"\n\n')
        f.write("[tool.steptrace]\n")
        for key, value in config.items():
            if isinstance(value, bool):
                f.write(f'{key} = {"true" if value else "false"}\n')
            elif isinstance(value, str):
                f.write(f'{key} = "{value}"\n')
            elif isinstance(value, (int, float)):
                f.write(f"{key} = {value}\n")
            elif isinstance(value, list):
                items = ", ".join(f'"{item}"' for item in value)
                f.write(f"{key} = [{items}]\n")
    return config_path


def get_project_root():
    """Get the project root directory."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ==================== Basic CLI Tests ====================

def test_cli_basic_run():
    """Test basic CLI script execution."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = create_test_script(test_dir)
        
        result = subprocess.run(
            [sys.executable, "-m", "steptrace", "run", script_path],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        assert "Result: 30" in result.stdout, f"Script should output result. Got: {result.stdout}"
        assert result.returncode == 0, f"Should return 0. Got: {result.returncode}"
        
        print("✓ test_cli_basic_run passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_cli_help():
    """Test CLI help output."""
    result = subprocess.run(
        [sys.executable, "-m", "steptrace", "--help"],
        capture_output=True,
        text=True,
        cwd=get_project_root(),
    )
    
    assert result.returncode == 0, "Help should succeed"
    assert "steptrace" in result.stdout.lower(), "Help should mention steptrace"
    
    # Check run subcommand help
    result = subprocess.run(
        [sys.executable, "-m", "steptrace", "run", "--help"],
        capture_output=True,
        text=True,
        cwd=get_project_root(),
    )
    
    assert result.returncode == 0, "Run help should succeed"
    assert "--log-level" in result.stdout, "Should show --log-level option"
    assert "--log-output" in result.stdout, "Should show --log-output option"
    assert "--variable-mode" in result.stdout, "Should show --variable-mode option"
    assert "--trace-async" in result.stdout, "Should show --trace-async option"
    assert "--config" in result.stdout, "Should show --config option"
    
    print("✓ test_cli_help passed")


def test_cli_missing_script():
    """Test CLI handles missing script gracefully."""
    result = subprocess.run(
        [sys.executable, "-m", "steptrace", "run", "/nonexistent/script.py"],
        capture_output=True,
        text=True,
        cwd=get_project_root(),
    )
    
    assert result.returncode != 0, "Should return non-zero for missing script"
    assert "not found" in result.stderr.lower() or "error" in result.stderr.lower(), \
        f"Should show error message. Got: {result.stderr}"
    
    print("✓ test_cli_missing_script passed")


# ==================== Log Output Tests ====================

def test_cli_log_output_stdout():
    """Test CLI with --log-output STDOUT."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = create_test_script(test_dir)
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--log-output", "STDOUT", "--no-filter-workspace"
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        assert "Step" in result.stdout, f"Should have step output in stdout. Got: {result.stdout[:500]}"
        assert "Result: 30" in result.stdout, "Script output should be present"
        
        # STDOUT mode should not create log file
        log_dir = os.path.join(test_dir, ".tracer")
        assert not os.path.exists(log_dir), "STDOUT mode should not create log directory"
        
        print("✓ test_cli_log_output_stdout passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_cli_log_output_stderr():
    """Test CLI with --log-output STDERR."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = create_test_script(test_dir)
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--log-output", "STDERR", "--no-filter-workspace"
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        assert "Step" in result.stderr, f"Should have step output in stderr. Got: {result.stderr[:500]}"
        assert "Result: 30" in result.stdout, "Script output should be in stdout"
        
        print("✓ test_cli_log_output_stderr passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_cli_log_output_file():
    """Test CLI with --log-output FILE (default)."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    log_dir = os.path.join(test_dir, ".tracer")
    
    try:
        script_path = create_test_script(test_dir)
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--log-output", "FILE", "--log-dir", log_dir, "--no-filter-workspace"
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        assert result.returncode == 0, f"Should succeed. Stderr: {result.stderr}"
        
        # Check log file was created
        log_file = os.path.join(log_dir, "tracer.log")
        assert os.path.exists(log_file), "Log file should be created"
        
        with open(log_file) as f:
            content = f.read()
        assert "Step" in content, "Log file should contain step output"
        
        print("✓ test_cli_log_output_file passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_cli_log_output_file_stdout():
    """Test CLI with --log-output FILE_STDOUT."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    log_dir = os.path.join(test_dir, ".tracer")
    
    try:
        script_path = create_test_script(test_dir)
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--log-output", "FILE_STDOUT", "--log-dir", log_dir, "--no-filter-workspace"
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        # Should have output in both stdout and file
        assert "Step" in result.stdout, "Should have step output in stdout"
        
        log_file = os.path.join(log_dir, "tracer.log")
        assert os.path.exists(log_file), "Log file should be created"
        
        with open(log_file) as f:
            content = f.read()
        assert "Step" in content, "Log file should contain step output"
        
        print("✓ test_cli_log_output_file_stdout passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


# ==================== Log Level Tests ====================

def test_cli_log_level_silent():
    """Test CLI with --log-level SILENT."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = create_test_script(test_dir)
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--log-level", "SILENT", "--log-output", "STDOUT"
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        assert "Result: 30" in result.stdout, "Script output should be present"
        lines = [l for l in result.stdout.split('\n') if 'Step' in l]
        assert len(lines) == 0, f"SILENT mode should not have Step output. Got: {lines}"
        
        print("✓ test_cli_log_level_silent passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_cli_log_level_debug():
    """Test CLI with --log-level DEBUG."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = create_test_script(test_dir)
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--log-level", "DEBUG", "--log-output", "STDOUT", "--no-filter-workspace"
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        assert "Step" in result.stdout, "DEBUG should have step output"
        assert "Runtime:" in result.stdout, "DEBUG should include runtime"
        
        print("✓ test_cli_log_level_debug passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_cli_log_level_info():
    """Test CLI with --log-level INFO."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = create_test_script(test_dir)
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--log-level", "INFO", "--log-output", "STDOUT", "--no-filter-workspace"
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        assert "Step" in result.stdout, "INFO should have step output"
        assert "Runtime:" in result.stdout, "INFO should include runtime"
        
        print("✓ test_cli_log_level_info passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


# ==================== Variable Mode Tests ====================

def test_cli_variable_mode_all():
    """Test CLI with --variable-mode ALL."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = create_test_script(test_dir)
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--variable-mode", "ALL", "--log-output", "STDOUT", "--no-filter-workspace"
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        # ALL mode shows variables without markers
        assert "Local variables" in result.stdout or "Global variables" in result.stdout, \
            f"ALL mode should show variable sections. Got: {result.stdout[:1000]}"
        assert "[NEW]" not in result.stdout, "ALL mode should not have [NEW] markers"
        
        print("✓ test_cli_variable_mode_all passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_cli_variable_mode_changed():
    """Test CLI with --variable-mode CHANGED."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = create_test_script(test_dir)
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--variable-mode", "CHANGED", "--log-output", "STDOUT", "--no-filter-workspace"
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        # CHANGED mode should show [NEW] or [CHANGED] markers
        has_markers = "[NEW]" in result.stdout or "[CHANGED]" in result.stdout
        has_changes_section = "variable changes" in result.stdout
        assert has_markers or has_changes_section, \
            f"CHANGED mode should have change markers. Got: {result.stdout[:1000]}"
        
        print("✓ test_cli_variable_mode_changed passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_cli_variable_mode_none():
    """Test CLI with --variable-mode NONE."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = create_test_script(test_dir)
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--variable-mode", "NONE", "--log-output", "STDOUT", "--no-filter-workspace"
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        # NONE mode should not show any variables
        assert "Local variables" not in result.stdout, "NONE mode should not show Local variables"
        assert "Global variables" not in result.stdout, "NONE mode should not show Global variables"
        assert "[NEW]" not in result.stdout, "NONE mode should not have [NEW] markers"
        # But should still have steps
        assert "Step" in result.stdout, "NONE mode should still show steps"
        
        print("✓ test_cli_variable_mode_none passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


# ==================== Script Arguments Tests ====================

def test_cli_with_script_args():
    """Test CLI passes arguments to script using -- separator."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = os.path.join(test_dir, "args_script.py")
        with open(script_path, "w") as f:
            f.write('''#!/usr/bin/env python3
import sys
print(f"Args: {sys.argv[1:]}")
''')
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--log-level", "SILENT", "--", "arg1", "arg2", "arg3"
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        assert "Args: ['arg1', 'arg2', 'arg3']" in result.stdout, \
            f"Script should receive args. Got: {result.stdout}"
        
        print("✓ test_cli_with_script_args passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_cli_options_after_script():
    """Test CLI options can come after script name."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = create_test_script(test_dir)
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--log-output", "STDOUT", "--variable-mode", "NONE", "--no-filter-workspace"
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        assert "Step" in result.stdout, "Should have step output"
        assert "Local variables" not in result.stdout, "NONE mode should not show variables"
        assert "Result: 30" in result.stdout, "Script should run correctly"
        
        print("✓ test_cli_options_after_script passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_cli_options_before_script():
    """Test CLI options can come before script name."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = create_test_script(test_dir)
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run",
                "--log-output", "STDOUT", "--variable-mode", "NONE", "--no-filter-workspace",
                script_path
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        assert "Step" in result.stdout, "Should have step output"
        assert "Local variables" not in result.stdout, "NONE mode should not show variables"
        assert "Result: 30" in result.stdout, "Script should run correctly"
        
        print("✓ test_cli_options_before_script passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


# ==================== Log Directory Tests ====================

def test_cli_log_dir():
    """Test CLI with --log-dir option."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    custom_log_dir = os.path.join(test_dir, "custom_logs")
    
    try:
        script_path = create_test_script(test_dir)
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--log-dir", custom_log_dir, "--no-filter-workspace"
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        assert result.returncode == 0, f"Should succeed. Stderr: {result.stderr}"
        
        log_file = os.path.join(custom_log_dir, "tracer.log")
        assert os.path.exists(log_file), f"Log file should be created at {log_file}"
        
        print("✓ test_cli_log_dir passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


# ==================== Filter Workspace Tests ====================

def test_cli_no_filter_workspace():
    """Test CLI with --no-filter-workspace option."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = create_test_script(test_dir)
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--log-output", "STDOUT", "--no-filter-workspace"
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        # With --no-filter-workspace, script should be traced regardless of location
        assert "Step" in result.stdout, "Should have step output with --no-filter-workspace"
        
        print("✓ test_cli_no_filter_workspace passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


# ==================== Async Tracing Tests ====================

def test_cli_trace_async():
    """Test CLI with --trace-async option."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = create_async_test_script(test_dir)
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--trace-async", "--log-output", "STDOUT", "--variable-mode", "NONE",
                "--no-filter-workspace"
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        assert "Async Result: data" in result.stdout, "Async script should run correctly"
        assert result.returncode == 0, f"Should succeed. Stderr: {result.stderr}"
        
        print("✓ test_cli_trace_async passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_cli_async_threshold():
    """Test CLI with --async-threshold-ms option."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = create_async_test_script(test_dir)
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--trace-async", "--async-threshold-ms", "100",
                "--log-output", "STDOUT", "--variable-mode", "NONE",
                "--no-filter-workspace"
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        assert "Async Result: data" in result.stdout, "Async script should run correctly"
        assert result.returncode == 0, f"Should succeed. Stderr: {result.stderr}"
        
        print("✓ test_cli_async_threshold passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


# ==================== YAML Config Tests ====================

def test_cli_yaml_config_basic():
    """Test CLI with basic YAML config file."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = create_test_script(test_dir)
        config_path = create_yaml_config(test_dir, {
            "log_output": "STDOUT",
            "variable_mode": "NONE",
            "filter_workspace": False,
        })
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--config", config_path
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        if "PyYAML is required" in result.stderr:
            print("⚠ test_cli_yaml_config_basic skipped (PyYAML not installed)")
            return
        
        assert "Step" in result.stdout, "Should have step output from YAML config"
        assert "Local variables" not in result.stdout, "NONE mode from config should work"
        
        print("✓ test_cli_yaml_config_basic passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_cli_yaml_config_all_options():
    """Test CLI with YAML config file containing all options."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    log_dir = os.path.join(test_dir, "yaml_logs")
    
    try:
        script_path = create_test_script(test_dir)
        config_path = create_yaml_config(test_dir, {
            "log_level": "INFO",
            "log_output": "FILE_STDOUT",
            "variable_mode": "CHANGED",
            "log_dir": log_dir,
            "filter_workspace": False,
        })
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--config", config_path
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        if "PyYAML is required" in result.stderr:
            print("⚠ test_cli_yaml_config_all_options skipped (PyYAML not installed)")
            return
        
        # FILE_STDOUT should output to both
        assert "Step" in result.stdout, "Should have step output in stdout"
        
        log_file = os.path.join(log_dir, "tracer.log")
        assert os.path.exists(log_file), "Log file should be created"
        
        with open(log_file) as f:
            content = f.read()
        assert "Step" in content, "Log file should have step output"
        
        print("✓ test_cli_yaml_config_all_options passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_cli_yaml_config_override():
    """Test CLI options override YAML config."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = create_test_script(test_dir)
        config_path = create_yaml_config(test_dir, {
            "log_level": "INFO",
            "variable_mode": "ALL",
            "filter_workspace": False,
        })
        
        # Override variable_mode with CLI option
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--config", config_path,
                "--variable-mode", "NONE", "--log-output", "STDOUT"
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        if "PyYAML is required" in result.stderr:
            print("⚠ test_cli_yaml_config_override skipped (PyYAML not installed)")
            return
        
        # CLI should override config
        assert "Local variables" not in result.stdout, "CLI override should take precedence"
        assert "Step" in result.stdout, "Should still have step output"
        
        print("✓ test_cli_yaml_config_override passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


# ==================== TOML Config Tests ====================

def test_cli_toml_config_basic():
    """Test CLI with basic TOML config file."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = create_test_script(test_dir)
        config_path = create_toml_config(test_dir, {
            "log_output": "STDOUT",
            "variable_mode": "NONE",
            "filter_workspace": False,
        })
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--config", config_path
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        assert "Step" in result.stdout, f"Should have step output from TOML config. Got: {result.stdout[:500]}"
        assert "Local variables" not in result.stdout, "NONE mode from config should work"
        
        print("✓ test_cli_toml_config_basic passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_cli_toml_config_all_options():
    """Test CLI with TOML config file containing all options."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    log_dir = os.path.join(test_dir, "toml_logs")
    
    try:
        script_path = create_test_script(test_dir)
        config_path = create_toml_config(test_dir, {
            "log_level": "DEBUG",
            "log_output": "FILE",
            "variable_mode": "CHANGED",
            "log_dir": log_dir,
            "filter_workspace": False,
        })
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--config", config_path
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        log_file = os.path.join(log_dir, "tracer.log")
        assert os.path.exists(log_file), f"Log file should be created. Stderr: {result.stderr}"
        
        with open(log_file) as f:
            content = f.read()
        assert "Step" in content, "Log file should have step output"
        assert "[NEW]" in content or "variable changes" in content, "CHANGED mode should have markers"
        
        print("✓ test_cli_toml_config_all_options passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_cli_toml_config_override():
    """Test CLI options override TOML config."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = create_test_script(test_dir)
        config_path = create_toml_config(test_dir, {
            "log_level": "SILENT",
            "variable_mode": "ALL",
            "filter_workspace": False,
        })
        
        # Override log_level with CLI option
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--config", config_path,
                "--log-level", "INFO", "--log-output", "STDOUT"
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        # CLI should override SILENT to INFO
        assert "Step" in result.stdout, "CLI override should enable step output"
        
        print("✓ test_cli_toml_config_override passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


# ==================== pyproject.toml Config Tests ====================

def test_cli_pyproject_toml_config():
    """Test CLI with pyproject.toml [tool.steptrace] config."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = create_test_script(test_dir)
        config_path = create_pyproject_toml(test_dir, {
            "log_output": "STDOUT",
            "variable_mode": "NONE",
            "filter_workspace": False,
        })
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--config", config_path
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        assert "Step" in result.stdout, f"Should have step output from pyproject.toml. Got: {result.stdout[:500]}"
        assert "Local variables" not in result.stdout, "NONE mode from config should work"
        
        print("✓ test_cli_pyproject_toml_config passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


# ==================== Traceable Functions Tests ====================

def test_cli_traceable_functions():
    """Test CLI with --traceable-functions option."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = os.path.join(test_dir, "multi_func.py")
        with open(script_path, "w") as f:
            f.write('''#!/usr/bin/env python3
def func_a():
    x = 1
    return x

def func_b():
    y = 2
    return y

def main():
    a = func_a()
    b = func_b()
    print(f"Result: {a + b}")

main()
''')
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--log-output", "STDOUT", "--variable-mode", "NONE",
                "--traceable-functions", "func_a", "--no-filter-workspace"
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        # Should only trace func_a, not func_b or main
        assert "func_a" in result.stdout, "Should trace func_a"
        
        print("✓ test_cli_traceable_functions passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


# ==================== Error Handling Tests ====================

def test_cli_invalid_config_file():
    """Test CLI with invalid config file path."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = create_test_script(test_dir)
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--config", "/nonexistent/config.yaml"
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        assert result.returncode != 0, "Should fail with invalid config"
        assert "not found" in result.stderr.lower() or "error" in result.stderr.lower(), \
            f"Should show error. Got: {result.stderr}"
        
        print("✓ test_cli_invalid_config_file passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_cli_unsupported_config_format():
    """Test CLI with unsupported config file format."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = create_test_script(test_dir)
        config_path = os.path.join(test_dir, "config.txt")
        with open(config_path, "w") as f:
            f.write("log_level = DEBUG\n")
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--config", config_path
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        assert result.returncode != 0, "Should fail with unsupported format"
        assert "unsupported" in result.stderr.lower() or "error" in result.stderr.lower(), \
            f"Should show error. Stderr: {result.stderr}"
        
        print("✓ test_cli_unsupported_config_format passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_cli_script_exception():
    """Test CLI handles script exceptions properly."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    
    try:
        script_path = os.path.join(test_dir, "error_script.py")
        with open(script_path, "w") as f:
            f.write('raise ValueError("test error")\n')
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--log-level", "SILENT"
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        assert result.returncode != 0, "Should return non-zero for script with error"
        assert "ValueError" in result.stderr or "test error" in result.stderr, \
            f"Should show error. Stderr: {result.stderr}"
        
        print("✓ test_cli_script_exception passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


# ==================== Combined Options Tests ====================

def test_cli_combined_options():
    """Test CLI with multiple options combined."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_cli_test_")
    log_dir = os.path.join(test_dir, "combined_logs")
    
    try:
        script_path = create_test_script(test_dir)
        
        result = subprocess.run(
            [
                sys.executable, "-m", "steptrace", "run", script_path,
                "--log-level", "DEBUG",
                "--log-output", "FILE_STDOUT",
                "--variable-mode", "CHANGED",
                "--log-dir", log_dir,
                "--no-filter-workspace"
            ],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        
        assert result.returncode == 0, f"Should succeed. Stderr: {result.stderr}"
        assert "Step" in result.stdout, "Should have step output in stdout"
        
        log_file = os.path.join(log_dir, "tracer.log")
        assert os.path.exists(log_file), "Log file should be created"
        
        with open(log_file) as f:
            content = f.read()
        # Content should match stdout
        assert "Step" in content, "Log file should have step output"
        
        print("✓ test_cli_combined_options passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    print("Testing CLI Functionality")
    print("=" * 60)
    
    # Basic tests
    test_cli_basic_run()
    test_cli_help()
    test_cli_missing_script()
    
    # Log output tests
    test_cli_log_output_stdout()
    test_cli_log_output_stderr()
    test_cli_log_output_file()
    test_cli_log_output_file_stdout()
    
    # Log level tests
    test_cli_log_level_silent()
    test_cli_log_level_debug()
    test_cli_log_level_info()
    
    # Variable mode tests
    test_cli_variable_mode_all()
    test_cli_variable_mode_changed()
    test_cli_variable_mode_none()
    
    # Script arguments tests
    test_cli_with_script_args()
    test_cli_options_after_script()
    test_cli_options_before_script()
    
    # Log directory tests
    test_cli_log_dir()
    
    # Filter workspace tests
    test_cli_no_filter_workspace()
    
    # Async tracing tests
    test_cli_trace_async()
    test_cli_async_threshold()
    
    # YAML config tests
    test_cli_yaml_config_basic()
    test_cli_yaml_config_all_options()
    test_cli_yaml_config_override()
    
    # TOML config tests
    test_cli_toml_config_basic()
    test_cli_toml_config_all_options()
    test_cli_toml_config_override()
    
    # pyproject.toml config tests
    test_cli_pyproject_toml_config()
    
    # Traceable functions tests
    test_cli_traceable_functions()
    
    # Error handling tests
    test_cli_invalid_config_file()
    test_cli_unsupported_config_format()
    test_cli_script_exception()
    
    # Combined options tests
    test_cli_combined_options()
    
    print("=" * 60)
    print("All CLI tests passed!")
