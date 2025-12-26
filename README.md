# Steptrace

A lightweight Python execution tracer that records **line-by-line execution**, **call stack**, **runtime per step**, and **local/global variables** — all filtered to your workspace for clean, readable logs.

Designed for debugging, learning, and understanding program flow.

---

## Features

- 🔍 Line-by-line execution tracing
- 🧵 Call stack reconstruction
- ⏱ Runtime per step (milliseconds)
- 📦 Local and global variable inspection
- 🚫 Automatically ignores:
  - Built-in modules
  - `site-packages`
  - Non-workspace files
- 🗂 Auto-incrementing log files (no overwrites)
- 🧼 Safe cleanup of `sys.settrace`
- 🧩 Supports **context manager** and **decorator** usage

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

@Tracer().tracer
def main():
    a = 1
    b = 2
    print(a + b)

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

### Example Log Entry

```
--------------------- Step 3 ---------------------
Runtime: 0.0841 ms
/path/to/file.py::main -- line 8

------> Global variables <------
x: int :: 5

------> Local variables <------
y: int :: 10
```

---

## How It Works

The tracer uses Python’s `sys.settrace` to intercept execution **on every line** and logs:

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

## License

MIT License — free to use, modify, and distribute.
