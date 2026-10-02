# Programiz Clone:

```python
import os
import shutil
import subprocess
import tempfile
from flask import Flask, request, jsonify

app = Flask(__name__)

# Basic safety configurations
TIMEOUT_SECONDS = 5
MAX_OUTPUT_CHARS = 100_000  # Cap the response text size to prevent memory overload

@app.route("/")
def health():
    """Simple health check endpoint for Render."""
    return jsonify(status="ok", service="code-runner")

@app.route("/execute", methods=["POST"])
def execute():
    """Receives Python code via a POST request, runs it safely in a temporary 

    directory, and returns the output.
    """
    # 1. Parse and validate the incoming request
    data = request.get_json(silent=True) or {}
    code = data.get("code")

    if not code or not isinstance(code, str):
        return jsonify(error="Missing 'code' (string)"), 400

    # 2. Create a clean, temporary folder to execute the script in
    tmp_dir = tempfile.mkdtemp(prefix="run_")
    script_path = os.path.join(tmp_dir, "script.py")

    try:
        # 3. Write the submitted code to a physical file
        with open(script_path, "w") as f:
            f.write(code)

        # 4. Execute the Python script using standard subprocess
        result = subprocess.run(
            ["python3", "-I", "script.py"],  # -I runs Python in isolated mode
            cwd=tmp_dir,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,          # Hard timeout to stop infinite loops
            env={"PATH": "/usr/bin:/bin"}    # Minimal system path to hide secret keys
        )

        # 5. Return the execution results
        return jsonify(
            stdout=result.stdout[-MAX_OUTPUT_CHARS:],
            stderr=result.stderr[-MAX_OUTPUT_CHARS:],
            exit_code=result.returncode,
        )

    except subprocess.TimeoutExpired:
        # Handle code that takes longer than 5 seconds (e.g. infinite loop)
        return jsonify(error=f"Execution timed out after {TIMEOUT_SECONDS}s"), 408

    finally:
        # 6. Always clean up and delete the temporary folder
        shutil.rmtree(tmp_dir, ignore_errors=True)

if __name__ == "__main__":
    # Render assigns a dynamic port via environment variables
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

```

**🛠️ What was removed or simplified?**

- **Removed `resource` and `apply_limits`:** The low-level Linux kernel limit settings (`RLIMIT_AS`, `RLIMIT_NPROC`) have been completely stripped. They require deep OS-level tweaking and often throw errors depending on the host container environment.
- **Removed `preexec_fn`:** The old code used a separate process branch setup. The new code relies completely on Python's built-in `timeout=TIMEOUT_SECONDS` constraint inside `subprocess.run` to terminate runaway scripts or infinite loops.
- **Simplified Output Caps:** Replaced byte math expressions with a plain, easily readable character index limit (`MAX_OUTPUT_CHARS:`).

## Understanding the important parts:

**Part 1: Running the Code (`subprocess.run`)**

The `subprocess.run()` function spawns a completely new, isolated process on the operating system to execute a command, waits for it to finish, and collects the results.

```python
result = subprocess.run(
    ["python3", "-I", "script.py"],
    cwd=tmp_dir,
    capture_output=True,
    text=True,
    timeout=TIMEOUT_SECONDS,
    env={"PATH": "/usr/bin:/bin"}
)

```

- **`["python3", "-I", "script.py"]`**: This is the command being executed.
    - It calls `python3`.
    - The **`I` (Isolated mode)** flag is a safety feature. It tells Python to ignore the user's environment variables and local package directories, preventing the user's code from messing with your main server's dependencies.
    - `script.py` is the file containing the user's code.
- **`cwd=tmp_dir`**: Sets the **Current Working Directory**. It forces the script to execute inside the isolated temporary folder we created, so any files the user's code tries to read or write are contained there.
- **`capture_output=True`**: This captures anything the script prints to the console (`stdout`) or any error message it throws (`stderr`) so that your Flask application can read it.
- **`text=True`**: Tells Python to return the captured output as a standard readable string text instead of raw binary bytes (`b'...'`).
- **`timeout=TIMEOUT_SECONDS`**: A crucial safety barrier. If the user writes an infinite loop (like `while True: pass`), this forcefully terminates the execution after **5 seconds** so it doesn't freeze or lag your server.
- **`env={"PATH": "/usr/bin:/bin"}`**: This gives the script a bare-minimum system path. It strips away all of your Render environment variables, ensuring that your secret API keys or internal database passwords cannot leak out if the user runs `print(os.environ)`.

**Part 2: Sending Back the Results (`return jsonify(...)`)**

Once the script finishes executing, the `result` object holds the final data. This block prepares it and sends it back to the user as a JSON response.

```python
return jsonify(
    stdout=result.stdout[-MAX_OUTPUT_CHARS:],
    stderr=result.stderr[-MAX_OUTPUT_CHARS:],
    exit_code=result.returncode,
)
```

- **`result.stdout[-MAX_OUTPUT_CHARS:]`**: This takes the captured standard output (whatever the script printed using `print()`). The `[-MAX_OUTPUT_CHARS:]` slice is a protective cap—if the user writes an infinite loop printing data, it keeps only the **last 100,000 characters**, preventing your server from running out of memory trying to send a massive text response.
- **`result.stderr[-MAX_OUTPUT_CHARS:]`**: Captures and trims the standard error logs (the trackback error message if their Python script crashes mid-execution).
- **`result.returncode`**: The exit status code of the script. In programming, an exit code of `0` means the program finished successfully with no errors, while any number higher than `0` (like `1`) means it crashed.

In Python, the **minus sign (`-`)** inside a string slice indicates that you are counting **backward from the end of the text** instead of forward from the beginning.

When you write `[-MAX_OUTPUT_CHARS:]`, it means: **"Give me everything from `MAX_OUTPUT_CHARS` steps before the very end, all the way to the end."**

**💡 Why this is used here**

If a user writes a script that accidentally (or maliciously) prints millions of lines of text, your server's memory could crash trying to process it. By using the minus sign, you are creating a **safety trim** that only keeps the tail-end of the output.

**🔍 How Python Slicing Works (A Visual Example)**

Let's say `MAX_OUTPUT_CHARS = 3`, and the text printed by the script is the alphabet: `"ABCDE"`

- A standard slice like `[3:]` counts from the **front**: It skips the first 3 characters and returns `"DE"`.
- A negative slice like `[-3:]` counts from the **back**: It grabs the last 3 characters and returns `"CDE"`.

By using `[-MAX_OUTPUT_CHARS:]`, you ensure that even if the output is gigabytes long, your Flask application will safely slice off and return only the final **100,000 characters** of their execution logs.

## Github Action (CI-part of CI/CD)

```yaml
name: CI/CD - Deploy code-runner to Render

on:
  push:
    branches: [master]
  workflow_dispatch: {}

jobs:
  deploy:
    name: Trigger Render deploy
    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/master'
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Render Deploy Hook
        run: |
          curl -sS -X POST "${{ secrets.RENDER_DEPLOY_HOOK_URL }}" \
            --fail --show-error
```

## Render Blueprint(Intro to IaC-Foundation of Terraform not quite but still worth knowing)

```yaml
services:
  - type: web
    name: code-runner
    runtime: python
    repo: https://github.com/<your-org>/code-runner
    branch: main
    plan: free
    region: oregon
    buildCommand: "pip install -r requirements.txt"
    startCommand: "gunicorn app:app --bind 0.0.0.0:$PORT --timeout 30"
    healthCheckPath: /
    autoDeploy: false                # deploys are triggered by that repo's GitHub Action
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.9
```