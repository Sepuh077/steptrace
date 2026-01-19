"""
Configuration file support for steptrace.

Supports loading configuration from YAML and TOML files.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .tracer import LogLevel, LogOutput, VariableMode


def load_yaml(filepath: str) -> Optional[Dict[str, Any]]:
    """Load configuration from a YAML file."""
    try:
        import yaml
    except ImportError:
        print(
            "Error: PyYAML is required to load YAML config files. "
            "Install it with: pip install pyyaml",
            file=sys.stderr,
        )
        return None

    try:
        with open(filepath, "r") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file {filepath}: {e}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print(f"Error: Config file not found: {filepath}", file=sys.stderr)
        return None


def load_toml(filepath: str) -> Optional[Dict[str, Any]]:
    """Load configuration from a TOML file."""
    # Python 3.11+ has built-in tomllib
    try:
        import tomllib
    except ImportError:
        # Fall back to tomli for Python < 3.11
        try:
            import tomli as tomllib
        except ImportError:
            print(
                "Error: tomli is required to load TOML config files on Python < 3.11. "
                "Install it with: pip install tomli",
                file=sys.stderr,
            )
            return None

    try:
        with open(filepath, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        print(f"Error parsing TOML file {filepath}: {e}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print(f"Error: Config file not found: {filepath}", file=sys.stderr)
        return None


def load_config(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Load configuration from a file.

    Supports YAML (.yaml, .yml) and TOML (.toml) files.
    Also supports reading the [tool.steptrace] section from pyproject.toml.

    Args:
        filepath: Path to the configuration file.

    Returns:
        Dictionary with configuration options, or None on error.
    """
    filepath = os.path.abspath(filepath)
    ext = Path(filepath).suffix.lower()

    if ext in (".yaml", ".yml"):
        config = load_yaml(filepath)
    elif ext == ".toml":
        config = load_toml(filepath)
        # If it's a pyproject.toml, look for [tool.steptrace]
        if config and os.path.basename(filepath) == "pyproject.toml":
            config = config.get("tool", {}).get("steptrace", {})
    else:
        print(
            f"Error: Unsupported config file format: {ext}. "
            "Use .yaml, .yml, or .toml",
            file=sys.stderr,
        )
        return None

    if config is not None:
        # Normalize configuration keys (convert hyphens to underscores)
        config = normalize_config(config)

    return config


def normalize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize configuration dictionary.

    - Converts hyphens to underscores in keys
    - Converts string values to appropriate types
    """
    normalized = {}

    for key, value in config.items():
        # Convert hyphens to underscores
        key = key.replace("-", "_")

        # Handle nested dictionaries
        if isinstance(value, dict):
            value = normalize_config(value)
        # Convert enum string values
        elif key == "log_level" and isinstance(value, str):
            value = parse_log_level(value)
        elif key == "log_output" and isinstance(value, str):
            value = parse_log_output(value)
        elif key == "variable_mode" and isinstance(value, str):
            value = parse_variable_mode(value)

        normalized[key] = value

    return normalized


def parse_log_level(value: str) -> LogLevel:
    """Parse log level from string."""
    mapping = {
        "DEBUG": LogLevel.DEBUG,
        "INFO": LogLevel.INFO,
        "WARNING": LogLevel.WARNING,
        "ERROR": LogLevel.ERROR,
        "SILENT": LogLevel.SILENT,
    }
    return mapping.get(value.upper(), LogLevel.INFO)


def parse_log_output(value: str) -> LogOutput:
    """Parse log output from string."""
    mapping = {
        "FILE": LogOutput.FILE,
        "STDOUT": LogOutput.STDOUT,
        "STDERR": LogOutput.STDERR,
        "FILE_STDOUT": LogOutput.FILE_STDOUT,
        "FILE_STDERR": LogOutput.FILE_STDERR,
    }
    return mapping.get(value.upper(), LogOutput.FILE)


def parse_variable_mode(value: str) -> VariableMode:
    """Parse variable mode from string."""
    mapping = {
        "ALL": VariableMode.ALL,
        "CHANGED": VariableMode.CHANGED,
        "NONE": VariableMode.NONE,
    }
    return mapping.get(value.upper(), VariableMode.ALL)


def merge_config_with_args(config: Dict[str, Any], args) -> Dict[str, Any]:
    """
    Merge configuration from file with CLI arguments.

    CLI arguments take precedence over config file values.

    Args:
        config: Configuration dictionary from file.
        args: Parsed command-line arguments.

    Returns:
        Merged configuration for Tracer initialization.
    """
    # Start with config file values
    result = {}

    # Map config keys to tracer kwargs
    if "log_level" in config:
        result["log_level"] = config["log_level"]
    if "log_output" in config:
        result["log_output"] = config["log_output"]
    if "variable_mode" in config:
        result["variable_mode"] = config["variable_mode"]
    if "log_dir" in config:
        result["log_dir"] = config["log_dir"]
    if "filter_workspace" in config:
        result["filter_workspace"] = config["filter_workspace"]
    if "traceable_functions" in config:
        result["tracable_functions"] = config["traceable_functions"]
    if "trace_async" in config:
        result["trace_async"] = config["trace_async"]
    if "async_threshold_ms" in config:
        result["async_threshold_ms"] = config["async_threshold_ms"]

    # Override with CLI arguments
    if hasattr(args, "log_level") and args.log_level:
        result["log_level"] = parse_log_level(args.log_level)
    if hasattr(args, "log_output") and args.log_output:
        result["log_output"] = parse_log_output(args.log_output)
    if hasattr(args, "variable_mode") and args.variable_mode:
        result["variable_mode"] = parse_variable_mode(args.variable_mode)
    if hasattr(args, "log_dir") and args.log_dir:
        result["log_dir"] = args.log_dir
    if hasattr(args, "no_filter_workspace") and args.no_filter_workspace:
        result["filter_workspace"] = False
    if hasattr(args, "traceable_functions") and args.traceable_functions:
        result["tracable_functions"] = args.traceable_functions
    if hasattr(args, "trace_async") and args.trace_async:
        result["trace_async"] = True
    if hasattr(args, "async_threshold_ms") and args.async_threshold_ms > 0:
        result["async_threshold_ms"] = args.async_threshold_ms

    return result


def find_config_file(start_dir: str = None) -> Optional[str]:
    """
    Find a steptrace configuration file by searching upward.

    Looks for:
    - steptrace.yaml
    - steptrace.yml
    - steptrace.toml
    - pyproject.toml (with [tool.steptrace] section)

    Args:
        start_dir: Directory to start searching from. Defaults to current directory.

    Returns:
        Path to config file if found, None otherwise.
    """
    if start_dir is None:
        start_dir = os.getcwd()

    current = Path(start_dir).resolve()

    for _ in range(20):  # Limit search depth
        # Check for steptrace-specific config files
        for name in ("steptrace.yaml", "steptrace.yml", "steptrace.toml"):
            config_path = current / name
            if config_path.exists():
                return str(config_path)

        # Check for pyproject.toml
        pyproject_path = current / "pyproject.toml"
        if pyproject_path.exists():
            # Check if it has [tool.steptrace]
            config = load_toml(str(pyproject_path))
            if config and "tool" in config and "steptrace" in config["tool"]:
                return str(pyproject_path)

        # Move up
        parent = current.parent
        if parent == current:
            break
        current = parent

    return None
