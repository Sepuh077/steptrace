"""
Test script for variable logging mode options.
This tests different variable modes: ALL, CHANGED, NONE
"""

import os
import re
import shutil
import sys
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from steptrace import Tracer, VariableMode


def parse_log_steps_all_mode(content):
    """Parse log content for ALL variable mode."""
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
                "global_vars": {},
                "local_vars": {},
            }
            in_global_vars = False
            in_local_vars = False
        elif current_step:
            if "------> Global variables <------" in line:
                in_global_vars = True
                in_local_vars = False
            elif "------> Local variables <------" in line:
                in_global_vars = False
                in_local_vars = True
            elif "------>" in line:
                in_global_vars = False
                in_local_vars = False

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


def parse_log_steps_changed_mode(content):
    """Parse log content for CHANGED variable mode."""
    steps = []
    current_step = None
    in_global_changes = False
    in_local_changes = False

    for line in content.split("\n"):
        step_match = re.match(r"-+ Step (\d+) -+", line)
        if step_match:
            if current_step:
                steps.append(current_step)
            current_step = {
                "step_num": int(step_match.group(1)),
                "new_vars": [],
                "changed_vars": [],
                "deleted_vars": [],
            }
            in_global_changes = False
            in_local_changes = False
        elif current_step:
            if "------> Global variable changes <------" in line:
                in_global_changes = True
                in_local_changes = False
            elif "------> Local variable changes <------" in line:
                in_global_changes = False
                in_local_changes = True

            # Parse [NEW] variable
            new_match = re.match(r"^\[NEW\] (\w+): (\w+) :: (.+)$", line)
            if new_match:
                current_step["new_vars"].append(
                    {
                        "name": new_match.group(1),
                        "type": new_match.group(2),
                        "value": new_match.group(3),
                        "scope": "global" if in_global_changes else "local",
                    }
                )

            # Parse [CHANGED] variable
            changed_match = re.match(
                r"^\[CHANGED\] (\w+): (\w+) :: (.+) -> (.+)$", line
            )
            if changed_match:
                current_step["changed_vars"].append(
                    {
                        "name": changed_match.group(1),
                        "type": changed_match.group(2),
                        "old_value": changed_match.group(3),
                        "new_value": changed_match.group(4),
                        "scope": "global" if in_global_changes else "local",
                    }
                )

            # Parse [DELETED] variable
            deleted_match = re.match(r"^\[DELETED\] (\w+)$", line)
            if deleted_match:
                current_step["deleted_vars"].append(
                    {
                        "name": deleted_match.group(1),
                        "scope": "global" if in_global_changes else "local",
                    }
                )

    if current_step:
        steps.append(current_step)

    return steps


def sample_function():
    """A simple function with variable changes to trace."""
    x = 10
    y = 20
    x = 15  # Change x
    z = x + y
    return z


def sample_function_with_new_deleted():
    """A function that creates and modifies variables."""
    a = 1
    b = 2
    c = a + b  # New variable c
    a = 100  # Changed variable a
    d = c * 2  # New variable d
    return d


def test_variable_mode_all():
    """Test ALL variable mode - log all variables at each step with value verification."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_var_all_")
    try:
        with Tracer(variable_mode=VariableMode.ALL, log_dir=log_dir):
            result = sample_function()

        assert result == 35, f"Function should return 35, got {result}"

        log_file = os.path.join(log_dir, "tracer.log")
        assert os.path.exists(log_file), "Log file should exist"

        with open(log_file, "r") as f:
            content = f.read()

        steps = parse_log_steps_all_mode(content)

        # Should have multiple steps
        assert len(steps) >= 4, f"Should have at least 4 steps, got {len(steps)}"

        # Verify x is logged with correct initial value
        x_initial_found = False
        for step in steps:
            if "x" in step["local_vars"]:
                if step["local_vars"]["x"]["value"] == "10":
                    x_initial_found = True
                    assert step["local_vars"]["x"]["type"] == "int", "x should be int"
                    break
        assert x_initial_found, "Initial x=10 should be logged"

        # Verify x is logged with changed value (15)
        x_changed_found = False
        for step in steps:
            if "x" in step["local_vars"]:
                if step["local_vars"]["x"]["value"] == "15":
                    x_changed_found = True
                    break
        assert x_changed_found, "Changed x=15 should be logged"

        # Verify z is logged with correct value
        z_found = False
        for step in steps:
            if "z" in step["local_vars"]:
                z_found = True
                assert step["local_vars"]["z"]["type"] == "int", "z should be int"
                assert step["local_vars"]["z"]["value"] == "35", (
                    f"z should be 35, got {step['local_vars']['z']['value']}"
                )
        assert z_found, "Variable z=35 should be logged"

        # ALL mode should show "Local variables" header
        assert "Local variables" in content, (
            "ALL mode should show 'Local variables' header"
        )

        print("✓ test_variable_mode_all passed")
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


def test_variable_mode_changed():
    """Test CHANGED variable mode - log only new or changed variables."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_var_changed_")
    try:
        with Tracer(variable_mode=VariableMode.CHANGED, log_dir=log_dir):
            result = sample_function()

        assert result == 35, f"Function should return 35, got {result}"

        log_file = os.path.join(log_dir, "tracer.log")
        assert os.path.exists(log_file), "Log file should exist"

        with open(log_file, "r") as f:
            content = f.read()

        # CHANGED mode should show change markers
        assert "[NEW]" in content or "[CHANGED]" in content, (
            "CHANGED mode should have change markers"
        )

        # Should show "variable changes" header, not just "variables"
        assert "variable changes" in content.lower(), (
            "CHANGED mode should show 'variable changes' header"
        )

        print("✓ test_variable_mode_changed passed")
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


def test_variable_mode_changed_shows_new():
    """Test CHANGED mode properly shows [NEW] for new variables with correct values."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_var_new_")
    try:
        with Tracer(variable_mode=VariableMode.CHANGED, log_dir=log_dir):
            result = sample_function_with_new_deleted()

        assert result == 6, f"Function should return 6, got {result}"

        log_file = os.path.join(log_dir, "tracer.log")
        with open(log_file, "r") as f:
            content = f.read()

        parsed_steps = parse_log_steps_changed_mode(content)

        # Collect all new variables across all steps
        all_new_vars = []
        for step in parsed_steps:
            all_new_vars.extend(step["new_vars"])

        # Should have [NEW] markers
        assert len(all_new_vars) > 0, "Should have some new variables"

        # Find specific new variables
        new_var_names = [v["name"] for v in all_new_vars]
        assert "a" in new_var_names, "Variable 'a' should be marked as NEW"
        assert "b" in new_var_names, "Variable 'b' should be marked as NEW"
        assert "c" in new_var_names, "Variable 'c' should be marked as NEW"

        # Verify values of new variables
        for var in all_new_vars:
            if var["name"] == "a":
                assert var["value"] == "1", f"Initial a should be 1, got {var['value']}"
                assert var["type"] == "int", f"a should be int, got {var['type']}"
            elif var["name"] == "b":
                assert var["value"] == "2", f"b should be 2, got {var['value']}"
            elif var["name"] == "c":
                assert var["value"] == "3", f"c should be 3, got {var['value']}"
            elif var["name"] == "d":
                assert var["value"] == "6", f"d should be 6, got {var['value']}"

        print("✓ test_variable_mode_changed_shows_new passed")
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


def test_variable_mode_changed_shows_modifications():
    """Test CHANGED mode properly shows [CHANGED] with old -> new values."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_var_mod_")
    try:
        with Tracer(variable_mode=VariableMode.CHANGED, log_dir=log_dir):
            result = sample_function_with_new_deleted()

        assert result == 6, f"Function should return 6, got {result}"

        log_file = os.path.join(log_dir, "tracer.log")
        with open(log_file, "r") as f:
            content = f.read()

        parsed_steps = parse_log_steps_changed_mode(content)

        # Collect all changed variables across all steps
        all_changed_vars = []
        for step in parsed_steps:
            all_changed_vars.extend(step["changed_vars"])

        # Should have [CHANGED] marker for 'a' (changes from 1 to 100)
        assert len(all_changed_vars) > 0, "Should have at least one changed variable"

        # Find the change for 'a'
        a_changes = [v for v in all_changed_vars if v["name"] == "a"]
        assert len(a_changes) > 0, "Variable 'a' should be marked as CHANGED"

        # Verify the old -> new values for 'a'
        a_change = a_changes[0]
        assert a_change["old_value"] == "1", (
            f"a's old value should be 1, got {a_change['old_value']}"
        )
        assert a_change["new_value"] == "100", (
            f"a's new value should be 100, got {a_change['new_value']}"
        )

        # Should show the old -> new format in raw content
        assert " -> " in content, "CHANGED mode should show 'old -> new' format"
        assert "1 -> 100" in content, "Should show '1 -> 100' for variable a"

        print("✓ test_variable_mode_changed_shows_modifications passed")
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


def test_variable_mode_none():
    """Test NONE variable mode - no variable logging at all."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_var_none_")
    try:
        with Tracer(variable_mode=VariableMode.NONE, log_dir=log_dir):
            result = sample_function()

        assert result == 35, f"Function should return 35, got {result}"

        log_file = os.path.join(log_dir, "tracer.log")
        assert os.path.exists(log_file), "Log file should exist"

        with open(log_file, "r") as f:
            content = f.read()

        # NONE mode should still have step info
        assert "Step 1" in content, "NONE mode should have step info"
        assert "Runtime:" in content, "NONE mode should have runtime"

        # NONE mode should NOT include any variable-related content
        assert "variables" not in content.lower(), (
            "NONE mode should NOT mention variables"
        )
        # Check for variable format "name: type ::" which is how variables are logged
        assert "x: int ::" not in content, "NONE mode should NOT show variable x"
        assert "y: int ::" not in content, "NONE mode should NOT show variable y"
        assert "z: int ::" not in content, "NONE mode should NOT show variable z"
        assert "[NEW]" not in content, "NONE mode should NOT show [NEW] markers"
        assert "[CHANGED]" not in content, "NONE mode should NOT show [CHANGED] markers"

        print("✓ test_variable_mode_none passed")
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


def test_variable_mode_using_int():
    """Test that variable mode can be specified using integers."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_var_int_")
    try:
        # Use integer value for CHANGED (2)
        with Tracer(variable_mode=2, log_dir=log_dir):
            result = sample_function()

        assert result == 35, f"Function should return 35, got {result}"

        log_file = os.path.join(log_dir, "tracer.log")
        with open(log_file, "r") as f:
            content = f.read()

        # Integer 2 = CHANGED, should show change markers
        assert "[NEW]" in content or "[CHANGED]" in content, (
            "Integer mode 2 should work like CHANGED"
        )

        print("✓ test_variable_mode_using_int passed")
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


def test_variable_mode_all_shows_all_vars_every_step():
    """Test that ALL mode shows all existing variables at every step."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_all_every_")
    try:
        with Tracer(variable_mode=VariableMode.ALL, log_dir=log_dir):
            sample_function()

        log_file = os.path.join(log_dir, "tracer.log")
        with open(log_file, "r") as f:
            content = f.read()

        steps = parse_log_steps_all_mode(content)

        # After x and y are defined, both should appear in subsequent steps
        x_defined = False
        y_defined = False

        for step in steps:
            if "x" in step["local_vars"]:
                x_defined = True
            if "y" in step["local_vars"]:
                y_defined = True

            # Once both are defined, they should both appear together
            if x_defined and y_defined:
                assert "x" in step["local_vars"], (
                    f"x should appear after being defined (step {step['step_num']})"
                )
                assert "y" in step["local_vars"], (
                    f"y should appear after being defined (step {step['step_num']})"
                )

        print("✓ test_variable_mode_all_shows_all_vars_every_step passed")
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


def test_variable_mode_changed_is_more_compact():
    """Test that CHANGED mode produces less output than ALL mode for unchanged vars."""
    log_dir_all = tempfile.mkdtemp(prefix="tracer_test_compare_all_")
    log_dir_changed = tempfile.mkdtemp(prefix="tracer_test_compare_changed_")

    try:
        with Tracer(variable_mode=VariableMode.ALL, log_dir=log_dir_all):
            sample_function()

        with Tracer(variable_mode=VariableMode.CHANGED, log_dir=log_dir_changed):
            sample_function()

        with open(os.path.join(log_dir_all, "tracer.log"), "r") as f:
            all_content = f.read()

        with open(os.path.join(log_dir_changed, "tracer.log"), "r") as f:
            changed_content = f.read()

        # Count occurrences of variable names
        # In ALL mode, x should appear many times (once per step)
        # In CHANGED mode, x should appear fewer times (only when it changes)
        all_x_count = all_content.count("x: int")
        changed_x_count = changed_content.count("[NEW] x: int") + changed_content.count(
            "[CHANGED] x: int"
        )

        assert all_x_count > changed_x_count, (
            f"ALL mode should mention x more times than CHANGED mode: {all_x_count} vs {changed_x_count}"
        )

        print("✓ test_variable_mode_changed_is_more_compact passed")
    finally:
        shutil.rmtree(log_dir_all, ignore_errors=True)
        shutil.rmtree(log_dir_changed, ignore_errors=True)


def test_variable_type_preservation():
    """Test that variable types are correctly identified."""
    log_dir = tempfile.mkdtemp(prefix="tracer_test_types_")

    def function_with_types():
        my_int = 42
        my_float = 3.14
        my_str = "hello"
        my_list = [1, 2, 3]
        my_dict = {"a": 1}
        return my_int

    try:
        with Tracer(variable_mode=VariableMode.ALL, log_dir=log_dir):
            function_with_types()

        log_file = os.path.join(log_dir, "tracer.log")
        with open(log_file, "r") as f:
            content = f.read()

        # Verify types are correctly identified
        assert "my_int: int" in content, "int type should be correctly identified"
        assert "my_float: float" in content, "float type should be correctly identified"
        assert "my_str: str" in content, "str type should be correctly identified"
        assert "my_list: list" in content, "list type should be correctly identified"
        assert "my_dict: dict" in content, "dict type should be correctly identified"

        # Verify values
        assert ":: 42" in content, "int value should be 42"
        assert ":: 3.14" in content, "float value should be 3.14"
        assert ":: hello" in content or ":: 'hello'" in content, (
            "str value should be hello"
        )
        assert ":: [1, 2, 3]" in content, "list value should be [1, 2, 3]"

        print("✓ test_variable_type_preservation passed")
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


if __name__ == "__main__":
    print("Testing Variable Mode Options")
    print("=" * 50)
    test_variable_mode_all()
    test_variable_mode_changed()
    test_variable_mode_changed_shows_new()
    test_variable_mode_changed_shows_modifications()
    test_variable_mode_none()
    test_variable_mode_using_int()
    test_variable_mode_all_shows_all_vars_every_step()
    test_variable_mode_changed_is_more_compact()
    test_variable_type_preservation()
    print("=" * 50)
    print("All variable mode tests passed!")
