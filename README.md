# Steptrace

A lightweight Python execution tracer that records **line-by-line execution**, **call stack**, **runtime per step**, and **local/global variables** - all filtered to your workspace for clean, readable logs.

Designed for debugging, learning, and understanding program flow.

---

## Features

- Line-by-line execution tracing
- Call stack reconstruction
- Runtime per step (milliseconds)
- Local and global variable inspection
- **Configurable log levels** (DEBUG, INFO, WARNING, ERROR, SILENT)
- **Flexible output destinations** (FILE, STDOUT, STDERR, or combinations)
- **Variable tracking modes** (ALL, CHANGED, NONE)
- Automatically ignores:
  - Built-in modules
  - `site-packages`
  - Non-workspace files
- Auto-incrementing log files (no overwrites)
- Safe cleanup of `sys.settrace`
- Supports **context manager** and **decorator** usage

---

## Installation

```bash
pip install python-steptrace
```

---

## Quick Start

### Context Manager (Recommended)

```python
from steptrace import Tracer

def main():
    a = 1
    b = 2
    print(a + b)

with Tracer():
    main()
```

---

### Decorator Usage

```python
from steptrace import Tracer

@Tracer().trace
def main():
    a = 1
    b = 2
    print(a + b)

main()
```

---

## Configuration Options

### Log Level (Verbosity)

Control how much detail is logged:

```python
from steptrace import Tracer, LogLevel

# DEBUG - Most verbose: all details including call stack
with Tracer(log_level=LogLevel.DEBUG):
    main()

# INFO - Standard: step info, runtime, variables (default)
with Tracer(log_level=LogLevel.INFO):
    main()

# WARNING - Same as INFO (step info, runtime, variables)
with Tracer(log_level=LogLevel.WARNING):
    main()

# SILENT - No output at all
with Tracer(log_level=LogLevel.SILENT):
    main()
```

---

### Log Output Destination

Choose where to send log output:

```python
from steptrace import Tracer, LogOutput

# FILE - Log to file only (default)
with Tracer(log_output=LogOutput.FILE):
    main()

# STDOUT - Log to stdout only
with Tracer(log_output=LogOutput.STDOUT):
    main()

# STDERR - Log to stderr only
with Tracer(log_output=LogOutput.STDERR):
    main()

# FILE_STDOUT - Log to both file and stdout
with Tracer(log_output=LogOutput.FILE_STDOUT):
    main()

# FILE_STDERR - Log to both file and stderr
with Tracer(log_output=LogOutput.FILE_STDERR):
    main()
```

---

### Variable Logging Mode

Control how variables are logged:

```python
from steptrace import Tracer, VariableMode

# ALL - Log all variables at each step (default)
with Tracer(variable_mode=VariableMode.ALL):
    main()

# CHANGED - Log only new or changed variables
with Tracer(variable_mode=VariableMode.CHANGED):
    main()

# NONE - Don't log any variables
with Tracer(variable_mode=VariableMode.NONE):
    main()
```

---

### Combined Configuration

Mix and match options:

```python
from steptrace import Tracer, LogLevel, LogOutput, VariableMode

# Debug to console with only changed variables
with Tracer(
    log_level=LogLevel.DEBUG,
    log_output=LogOutput.STDOUT,
    variable_mode=VariableMode.CHANGED
):
    main()

# WARNING level (same as INFO) to file and stderr, no variables
with Tracer(
    log_level=LogLevel.WARNING,
    log_output=LogOutput.FILE_STDERR,
    variable_mode=VariableMode.NONE
):
    main()
```

---

## Log Output

Logs are written to:

```
.tracer/tracer.log
```

or, if a log already exists:

```
.tracer/tracer_1.log
.tracer/tracer_2.log
...
```

### Example Log Entry (ALL variables mode)

```
--------------------- Step 3 ---------------------
Runtime: 0.0841 ms
/path/to/file.py::main -- line 8

------> Global variables <------
x: int :: 5

------> Local variables <------
y: int :: 10
```

### Example Log Entry (CHANGED variables mode)

```
--------------------- Step 3 ---------------------
Runtime: 0.0841 ms
/path/to/file.py::main -- line 8

------> Local variable changes <------
[NEW] x: int :: 5
[CHANGED] y: int :: 5 -> 10
```

---

## How It Works

The tracer uses Python's `sys.settrace` to intercept execution **on every line** and logs:

- File name
- Function name
- Line number
- Execution time since last step
- Call stack
- Local and global variables

Only files inside your project workspace are traced to keep output relevant.

---

## Context Manager Behavior

Using the tracer as a context manager ensures:

- Previous trace functions are restored
- Exceptions are **not suppressed**

```python
with Tracer():
    risky_code()
```

---

## When to Use

- Debugging complex logic
- Understanding unfamiliar codebases
- Teaching / learning Python execution flow
- Inspecting variable evolution over time

---

## Limitations

- Tracing every line may generate large log files
- Not intended for production use
- Performance overhead for long-running programs

---

## Testing

Run the test suite:

```bash
python tests/run_all_tests.py
```

Or run individual test files:

```bash
python tests/test_log_level.py
python tests/test_log_output.py
python tests/test_variable_mode.py
python tests/test_all_options.py
```

---

## License

MIT License - free to use, modify, and distribute.
