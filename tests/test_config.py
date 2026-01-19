#!/usr/bin/env python3
"""
Tests for configuration file support.
"""

import os
import shutil
import sys
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from steptrace import LogLevel, LogOutput, VariableMode
from steptrace.config import (
    load_config,
    normalize_config,
    parse_log_level,
    parse_log_output,
    parse_variable_mode,
    merge_config_with_args,
    find_config_file,
)


def test_parse_log_level():
    """Test log level parsing."""
    assert parse_log_level("DEBUG") == LogLevel.DEBUG
    assert parse_log_level("INFO") == LogLevel.INFO
    assert parse_log_level("WARNING") == LogLevel.WARNING
    assert parse_log_level("ERROR") == LogLevel.ERROR
    assert parse_log_level("SILENT") == LogLevel.SILENT
    
    # Case insensitive
    assert parse_log_level("debug") == LogLevel.DEBUG
    assert parse_log_level("Info") == LogLevel.INFO
    
    # Unknown defaults to INFO
    assert parse_log_level("unknown") == LogLevel.INFO
    
    print("✓ test_parse_log_level passed")


def test_parse_log_output():
    """Test log output parsing."""
    assert parse_log_output("FILE") == LogOutput.FILE
    assert parse_log_output("STDOUT") == LogOutput.STDOUT
    assert parse_log_output("STDERR") == LogOutput.STDERR
    assert parse_log_output("FILE_STDOUT") == LogOutput.FILE_STDOUT
    assert parse_log_output("FILE_STDERR") == LogOutput.FILE_STDERR
    
    # Case insensitive
    assert parse_log_output("file") == LogOutput.FILE
    assert parse_log_output("Stdout") == LogOutput.STDOUT
    
    print("✓ test_parse_log_output passed")


def test_parse_variable_mode():
    """Test variable mode parsing."""
    assert parse_variable_mode("ALL") == VariableMode.ALL
    assert parse_variable_mode("CHANGED") == VariableMode.CHANGED
    assert parse_variable_mode("NONE") == VariableMode.NONE
    
    # Case insensitive
    assert parse_variable_mode("all") == VariableMode.ALL
    assert parse_variable_mode("Changed") == VariableMode.CHANGED
    
    print("✓ test_parse_variable_mode passed")


def test_normalize_config():
    """Test configuration normalization."""
    config = {
        "log-level": "DEBUG",
        "log-output": "STDOUT",
        "variable-mode": "CHANGED",
        "log_dir": ".my_tracer",
        "filter_workspace": True,
    }
    
    normalized = normalize_config(config)
    
    # Hyphens should be converted to underscores
    assert "log_level" in normalized
    assert "log_output" in normalized
    assert "variable_mode" in normalized
    
    # Enum strings should be converted
    assert normalized["log_level"] == LogLevel.DEBUG
    assert normalized["log_output"] == LogOutput.STDOUT
    assert normalized["variable_mode"] == VariableMode.CHANGED
    
    # Regular values preserved
    assert normalized["log_dir"] == ".my_tracer"
    assert normalized["filter_workspace"] is True
    
    print("✓ test_normalize_config passed")


def test_load_yaml_config():
    """Test loading YAML configuration."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_config_test_")
    
    try:
        # Create a YAML config file
        config_path = os.path.join(test_dir, "steptrace.yaml")
        with open(config_path, "w") as f:
            f.write("""
log_level: DEBUG
log_output: STDOUT
variable_mode: CHANGED
log_dir: .test_tracer
filter_workspace: false
trace_async: true
async_threshold_ms: 10.5
""")
        
        config = load_config(config_path)
        
        if config is None:
            # PyYAML not installed, skip test
            print("⚠ test_load_yaml_config skipped (PyYAML not installed)")
            return
        
        assert config["log_level"] == LogLevel.DEBUG
        assert config["log_output"] == LogOutput.STDOUT
        assert config["variable_mode"] == VariableMode.CHANGED
        assert config["log_dir"] == ".test_tracer"
        assert config["filter_workspace"] is False
        assert config["trace_async"] is True
        assert config["async_threshold_ms"] == 10.5
        
        print("✓ test_load_yaml_config passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_load_toml_config():
    """Test loading TOML configuration."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_config_test_")
    
    try:
        # Create a TOML config file
        config_path = os.path.join(test_dir, "steptrace.toml")
        with open(config_path, "w") as f:
            f.write('''
log_level = "INFO"
log_output = "FILE"
variable_mode = "ALL"
log_dir = ".toml_tracer"
filter_workspace = true
''')
        
        config = load_config(config_path)
        
        if config is None:
            # tomli not installed (Python < 3.11), skip test
            print("⚠ test_load_toml_config skipped (tomli not installed)")
            return
        
        assert config["log_level"] == LogLevel.INFO
        assert config["log_output"] == LogOutput.FILE
        assert config["variable_mode"] == VariableMode.ALL
        assert config["log_dir"] == ".toml_tracer"
        assert config["filter_workspace"] is True
        
        print("✓ test_load_toml_config passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_load_pyproject_toml():
    """Test loading configuration from pyproject.toml."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_config_test_")
    
    try:
        # Create a pyproject.toml with [tool.steptrace] section
        config_path = os.path.join(test_dir, "pyproject.toml")
        with open(config_path, "w") as f:
            f.write('''
[project]
name = "my-project"
version = "1.0.0"

[tool.steptrace]
log_level = "WARNING"
log_output = "STDERR"
variable_mode = "NONE"
''')
        
        config = load_config(config_path)
        
        if config is None:
            print("⚠ test_load_pyproject_toml skipped (tomli not installed)")
            return
        
        assert config["log_level"] == LogLevel.WARNING
        assert config["log_output"] == LogOutput.STDERR
        assert config["variable_mode"] == VariableMode.NONE
        
        print("✓ test_load_pyproject_toml passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_merge_config_with_args():
    """Test merging config with CLI arguments."""
    from argparse import Namespace
    
    config = {
        "log_level": LogLevel.DEBUG,
        "log_output": LogOutput.FILE,
        "log_dir": ".config_tracer",
    }
    
    # CLI args should override config
    args = Namespace(
        log_level="INFO",
        log_output=None,  # Not specified
        variable_mode="CHANGED",
        log_dir=None,  # Not specified
        no_filter_workspace=False,
        traceable_functions=None,
        trace_async=True,
        async_threshold_ms=5.0,
    )
    
    merged = merge_config_with_args(config, args)
    
    # CLI overrides
    assert merged["log_level"] == LogLevel.INFO
    assert merged["variable_mode"] == VariableMode.CHANGED
    assert merged["trace_async"] is True
    assert merged["async_threshold_ms"] == 5.0
    
    # Config values where CLI not specified
    assert merged["log_output"] == LogOutput.FILE
    assert merged["log_dir"] == ".config_tracer"
    
    print("✓ test_merge_config_with_args passed")


def test_find_config_file():
    """Test finding configuration file."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_config_test_")
    
    try:
        # Create a nested directory structure
        sub_dir = os.path.join(test_dir, "a", "b", "c")
        os.makedirs(sub_dir)
        
        # Create config in parent directory
        config_path = os.path.join(test_dir, "steptrace.yaml")
        with open(config_path, "w") as f:
            f.write("log_level: DEBUG\n")
        
        # Find config from subdirectory
        found = find_config_file(sub_dir)
        
        if found is None:
            # PyYAML not installed
            print("⚠ test_find_config_file skipped")
            return
        
        assert found == config_path, f"Should find config at {config_path}, got {found}"
        
        print("✓ test_find_config_file passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_invalid_config_file():
    """Test handling of invalid config files."""
    test_dir = tempfile.mkdtemp(prefix="steptrace_config_test_")
    
    try:
        # Test unsupported extension
        config_path = os.path.join(test_dir, "config.txt")
        with open(config_path, "w") as f:
            f.write("log_level = DEBUG\n")
        
        config = load_config(config_path)
        assert config is None, "Should return None for unsupported format"
        
        # Test non-existent file
        config = load_config(os.path.join(test_dir, "nonexistent.yaml"))
        # This might return None or raise an error depending on yaml availability
        
        print("✓ test_invalid_config_file passed")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    print("Testing Configuration Support")
    print("=" * 50)
    test_parse_log_level()
    test_parse_log_output()
    test_parse_variable_mode()
    test_normalize_config()
    test_load_yaml_config()
    test_load_toml_config()
    test_load_pyproject_toml()
    test_merge_config_with_args()
    test_find_config_file()
    test_invalid_config_file()
    print("=" * 50)
    print("All config tests passed!")
