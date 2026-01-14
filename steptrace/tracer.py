import copy
import inspect
import os
import sys
import time
from enum import IntEnum
from typing import List, Union


class LogLevel(IntEnum):
    """Log levels for verbosity control."""

    DEBUG = 10  # Most verbose: all details including call stack
    INFO = 20  # Standard: step info, variables
    WARNING = 30  # Same as INFO (step info, variables)
    ERROR = 40  # Errors only
    SILENT = 50  # No output


class LogOutput(IntEnum):
    """Output destination options."""

    FILE = 1  # Log to file only
    STDOUT = 2  # Log to stdout only
    STDERR = 3  # Log to stderr only
    FILE_STDOUT = 4  # Log to both file and stdout
    FILE_STDERR = 5  # Log to both file and stderr


class VariableMode(IntEnum):
    """Variable logging modes."""

    ALL = 1  # Log all variables at each step
    CHANGED = 2  # Log only changed variables
    NONE = 3  # Don't log variables


class Tracer:
    def __init__(
        self,
        filter_workspace: bool = True,
        log_dir: str = ".tracer",
        tracable_functions: List[str] = None,
        log_level: Union[LogLevel, int] = LogLevel.INFO,
        log_output: Union[LogOutput, int] = LogOutput.FILE,
        variable_mode: Union[VariableMode, int] = VariableMode.ALL,
    ):
        """
        Initialize the Tracer.

        Args:
            filter_workspace: If True, only trace files in the workspace.
            log_dir: Directory for log files.
            tracable_functions: List of function names to trace (None = all).
            log_level: Verbosity level (DEBUG, INFO, WARNING, ERROR, SILENT).
            log_output: Output destination (FILE, STDOUT, STDERR, FILE_STDOUT, FILE_STDERR).
            variable_mode: Variable logging mode (ALL, CHANGED, NONE).
        """
        self.workspace = os.path.dirname(os.path.abspath(inspect.stack()[-1].filename))
        self.filter_workspace = filter_workspace
        self.tracable_functions = tracable_functions

        # New options
        self.log_level = LogLevel(log_level)
        self.log_output = LogOutput(log_output)
        self.variable_mode = VariableMode(variable_mode)

        # Setup log file path if needed
        self.log_path = None
        if self.log_output in (
            LogOutput.FILE,
            LogOutput.FILE_STDOUT,
            LogOutput.FILE_STDERR,
        ):
            self.log_path = os.path.join(log_dir, "tracer.log")
            if os.path.exists(self.log_path):
                counter = 1
                while os.path.exists(os.path.join(log_dir, f"tracer_{counter}.log")):
                    counter += 1
                self.log_path = os.path.join(log_dir, f"tracer_{counter}.log")
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

        self._timer = None
        self._previous_globals = {}
        self._previous_locals = {}

    def _is_tracable(self, filename):
        if filename.startswith("<") or filename == __file__:
            return False

        if self.filter_workspace:
            if "ipykernel" in filename and self._in_jupyter:
                return True

            if not filename.startswith(self.workspace):
                return False

            if "site-packages" in filename or filename == "built-in":
                return False

        return True

    def _is_tracable_var(self, var):
        if "builtin" in type(var).__name__:
            return False
        return True

    def _is_tracable_func(self, func):
        return self.tracable_functions is None or func in self.tracable_functions

    def _is_jupyter_notebook(self):
        try:
            shell = get_ipython().__class__.__name__
            if shell == "ZMQInteractiveShell":
                return True  # Jupyter notebook or qtconsole
            elif shell == "TerminalInteractiveShell":
                return False  # Terminal IPython
            else:
                return False  # Other type (unknown)
        except NameError:
            return False

    def _file(self, frame):
        files = []
        frame_co = frame
        while frame_co.f_back:
            frame_co = frame_co.f_back
            files.append(frame_co)
        files.reverse()

        text = ""
        for file in files[2:]:
            text += f"{file.f_code.co_filename}::{file.f_code.co_name} -- line {file.f_lineno}\n"

        text += f"{frame.f_code.co_filename}::{frame.f_code.co_name} -- line {frame.f_lineno}\n"
        return text

    def _safe_copy(self, value):
        """Safely create a copy of a value for comparison."""
        try:
            return copy.deepcopy(value)
        except Exception:
            try:
                return copy.copy(value)
            except Exception:
                return repr(value)

    def _safe_repr(self, value):
        """Safely get a string representation of a value."""
        try:
            return repr(value)
        except Exception:
            return "<unrepresentable>"

    def _values_equal(self, val1, val2):
        """Safely compare two values."""
        try:
            return val1 == val2
        except Exception:
            return self._safe_repr(val1) == self._safe_repr(val2)

    def _get_filtered_variables(self, variables):
        """Get a filtered dictionary of traceable variables."""
        filtered = {}
        for key, value in variables.items():
            if key.startswith("__") and key.endswith("__"):
                continue
            if isinstance(value, (Tracer, type)) or not self._is_tracable_var(value):
                continue
            if hasattr(value, "__spec__") and not self._is_tracable(
                value.__spec__.origin
            ):
                continue
            filtered[key] = value
        return filtered

    def _variables(self, variables):
        text = ""
        for key, value in variables.items():
            if key.startswith("__") and key.endswith("__"):
                continue
            if isinstance(value, (Tracer, type)) or not self._is_tracable_var(value):
                continue
            if hasattr(value, "__spec__") and not self._is_tracable(
                value.__spec__.origin
            ):
                continue

            text += f"{key}: {type(value).__name__} :: {value}\n"
        return text

    def _changed_variables(self, current_vars, previous_vars):
        """Get only the variables that have changed since last step."""
        text = ""
        current_filtered = self._get_filtered_variables(current_vars)

        for key, value in current_filtered.items():
            if key not in previous_vars:
                # New variable
                text += f"[NEW] {key}: {type(value).__name__} :: {value}\n"
            else:
                # Check if value changed
                prev_value = previous_vars.get(key)
                if not self._values_equal(value, prev_value):
                    text += f"[CHANGED] {key}: {type(value).__name__} :: {prev_value} -> {value}\n"

        # Check for deleted variables
        for key in previous_vars:
            if key not in current_filtered:
                text += f"[DELETED] {key}\n"

        return text

    def _all_variables(self, frame):
        text = ""

        if self.variable_mode == VariableMode.NONE:
            return text

        if self.variable_mode == VariableMode.CHANGED:
            # Get changed variables only
            global_changes = self._changed_variables(
                frame.f_globals, self._previous_globals
            )
            local_changes = self._changed_variables(
                frame.f_locals, self._previous_locals
            )

            if global_changes:
                text += (
                    "------> Global variable changes <------\n" + global_changes + "\n"
                )
            if local_changes:
                text += (
                    "------> Local variable changes <------\n" + local_changes + "\n"
                )

            # Update previous state
            self._previous_globals = {
                k: self._safe_copy(v)
                for k, v in self._get_filtered_variables(frame.f_globals).items()
            }
            self._previous_locals = {
                k: self._safe_copy(v)
                for k, v in self._get_filtered_variables(frame.f_locals).items()
            }
        else:
            # Log all variables (original behavior)
            global_vars = self._variables(frame.f_globals)
            local_vars = self._variables(frame.f_locals)
            if global_vars:
                text += "------> Global variables <------\n" + global_vars + "\n"
            if local_vars:
                text += "------> Local variables <------\n" + local_vars + "\n"

        return text

    def _write_output(self, text):
        """Write output to the configured destination(s)."""
        if self.log_level >= LogLevel.SILENT:
            return

        # Write to file if configured
        if self.log_output in (
            LogOutput.FILE,
            LogOutput.FILE_STDOUT,
            LogOutput.FILE_STDERR,
        ):
            with open(self.log_path, "a") as f:
                f.write(text)

        # Write to stdout if configured
        if self.log_output in (LogOutput.STDOUT, LogOutput.FILE_STDOUT):
            sys.stdout.write(text)
            sys.stdout.flush()

        # Write to stderr if configured
        if self.log_output in (LogOutput.STDERR, LogOutput.FILE_STDERR):
            sys.stderr.write(text)
            sys.stderr.flush()

    def _log(self, frame):
        if not self._is_tracable(
            frame.f_code.co_filename
        ) or not self._is_tracable_func(frame.f_code.co_name):
            return

        if self.log_level >= LogLevel.SILENT:
            return

        self._step += 1

        # Build log message based on log level
        text = f"--------------------- Step {self._step} ---------------------\n"

        if self.log_level <= LogLevel.WARNING:
            # Include runtime info (only when we also show file/line info)
            text += f"Runtime: {(time.perf_counter() - self._timer) * 1000:.4f} ms\n"
            # Include file/function info
            text += self._file(frame) + "\n"
            # Include variables
            text += self._all_variables(frame)

        self._write_output(text)

    def _run_tracer(self, frame, event, arg):
        if event == "line":
            try:
                self._log(frame)
            except Exception as e:
                print(e)
        self._timer = time.perf_counter()
        return self._run_tracer

    def __enter__(self):
        self._initialize()
        self._previous_trace = sys.gettrace()
        sys.settrace(self._run_tracer)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.settrace(self._previous_trace)
        return False

    def _initialize(self):
        self._step = 0
        self._timer = time.perf_counter()
        self._in_jupyter = self._is_jupyter_notebook()
        self._previous_globals = {}
        self._previous_locals = {}

    def trace(self, func):
        def wrap(*args, **kwargs):
            self._initialize()
            sys.settrace(self._run_tracer)
            try:
                result = func(*args, **kwargs)
            finally:
                sys.settrace(None)
            return result

        return wrap
