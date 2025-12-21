from dataclasses import dataclass, field
import os
from utils.tools import *
from llm.llm import model
import subprocess
from runtime_env import *
import shlex
import json

@dataclass
class ExecuteOutput:
    thought: str = field(metadata={"description": "Your thought process for choosing parameters for executing commands."})
    command: str = field(metadata={"description": "The shell command to execute in the workspace."})
    output_format = """
{
  "thought": <string>,
  "command": "<shell command>"
}
"""

def execute_node(state):
    cprint("▶️ [Execute] planning commands to run","blue")
    agent_log = state.logs.to_context()
    reflection = state.reflection.to_context()
    workspace_structure = state.workspace_state.to_context()
    prompt = f"""
You are the Execute module of an autonomous bugfix agent. Your task is to decide the shell command to execute based on the current agent state and plan. Use Chinese to generate natural parts of the responses.
 {"NOTE: The last edit has NOT been executed yet, so your task is to execute to verify the fix" if state.phase == "edit" else ""}
[Agent Logs]
Here are relevant agent actions result about current issue and workspace:
{agent_log}
[Current Issue]
- Description: {state.issue_desc}
- Output since last execution: {state.output}
[Workspace Structure]
- {workspace_structure}
[Warning]
{describe_schema(ExecuteOutput)}
"""
    response = safe_invoke(model, ExecuteOutput, prompt)
    cprint(f"▶️ [Execute] Running command: {response['command']}", "blue")
    result = execute_command(response['command'])
    sandbox_suffix = f" (sandbox: {SANDBOX_ENV_NAME})" if SANDBOX_CONDA_ENABLED else ""
    new_logs = state.logs.add_entry(type="execute", entry=f"Command: {response['command']}{sandbox_suffix}")
    return {
        "phase": "execute",
        "thought": response['thought'],
        "logs": new_logs,
        "output": result,
        "command": response['command'],
    }

def execute_command(command: str) -> str:
    """execute command and get output using given command.
    Args:
        command (str): The shell command to execute.
    Returns:
        command (str): The command that was executed.
        stdout (str): The standard output from the command execution.
        stderr (str): The standard error from the command execution.
        return_code (int): The return code from the command execution.
        function_error (str): The error message if function execution fails.
    """
    try:
        workspace_path = os.path.join(os.getcwd(), WORKSPACE_PATH)
        wrapped_cmd = command
        if SANDBOX_CONDA_ENABLED:
            # Use classic activate script to avoid conda.sh dependency
            activate_script = os.path.join(CONDA_ROOT, "bin/activate") if CONDA_ROOT else ""
            if not CONDA_ROOT or not os.path.isfile(activate_script):
                err = "CONDA_ROOT missing or bin/activate not found. Please export CONDA_ROOT (e.g., /Users/<you>/anaconda3)."
                cprint(f"⚠️ [Execute] {err}", "yellow")
                return {"command": command, "invoked_command": "", "stdout": "", "stderr": err, "return_code": 1}

            _ensure_sandbox_env()
            activate_and_run = f". \"{CONDA_ROOT}/bin/activate\" {shlex.quote(SANDBOX_ENV_NAME)}; {command}"
            wrapped_cmd = f"bash -lc {shlex.quote(activate_and_run)}"

        # Launch process
        process = subprocess.Popen(
            wrapped_cmd,
            cwd=workspace_path,
            shell=True,
            text=True,
            executable="/bin/bash",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1
        )

        agg_stdout: list[str] = []
        agg_stderr: list[str] = []

        # Open sandbox log if configured
        sandbox_log_fp = None
        try:
            os.makedirs(SANDBOX_LOG_DIR, exist_ok=True)
            sandbox_log_fp = open(SANDBOX_LOG_FILE, "a", encoding="utf-8")
            sandbox_log_fp.write(f"\n===== Sandbox session start ({SANDBOX_ENV_NAME}) =====\n")
            sandbox_log_fp.write(f"Command: {command}\n")
            sandbox_log_fp.write(f"Invoked: {wrapped_cmd}\n")
            sandbox_log_fp.flush()
        except Exception as e:
            cprint(f"⚠️ [Execute] Failed to open sandbox log file: {e}", "yellow")

        # Stream lines
        while True:
            out_line = process.stdout.readline() if process.stdout else ""
            err_line = process.stderr.readline() if process.stderr else ""

            if out_line:
                cprint(out_line.rstrip(),"red")
                if sandbox_log_fp:
                    sandbox_log_fp.write(out_line)
                    sandbox_log_fp.flush()
                agg_stdout.append(out_line)
            if err_line:
                cprint(err_line.rstrip(),"red")
                if sandbox_log_fp:
                    sandbox_log_fp.write(err_line)
                    sandbox_log_fp.flush()
                agg_stderr.append(err_line)

            if not out_line and not err_line and process.poll() is not None:
                break

        if sandbox_log_fp:
            try:
                sandbox_log_fp.write(f"===== Sandbox session end (exit={process.returncode}) =====\n")
                sandbox_log_fp.flush()
                sandbox_log_fp.close()
            except Exception:
                pass

        return {
            "command": command,
            "invoked_command": wrapped_cmd,
            "stdout": "".join(agg_stdout).strip(),
            "stderr": "".join(agg_stderr).strip(),
            "return_code": process.returncode
        }
    except subprocess.TimeoutExpired:
        return {"command": command, "stdout": "", "stderr": "Command timed out", "return_code": -1}
    except Exception as e:
        return {"command": command, "function_error": str(e)}

def _ensure_sandbox_env():
    """Ensure the Conda sandbox env exists; create if missing using CONDA_EXE."""
    try:
        activate_script = os.path.join(CONDA_ROOT, "bin/activate") if CONDA_ROOT else ""
        if not CONDA_ROOT or not os.path.isfile(activate_script):
            cprint("⚠️ [Execute] CONDA_ROOT is not set or bin/activate not found. Skip sandbox ensure.", "yellow")
            return

        probe_cmd = f". \"{CONDA_ROOT}/bin/activate\" {shlex.quote(SANDBOX_ENV_NAME)}; python -c 'import sys; print(sys.version)'"
        probe = subprocess.run(["bash", "-lc", probe_cmd], capture_output=True, text=True)
        if probe.returncode == 0:
            return

        if not SANDBOX_CREATE_IF_MISSING:
            return

        create = subprocess.run([CONDA_EXE, "create", "-y", "-n", SANDBOX_ENV_NAME, f"python={SANDBOX_PYTHON_VERSION}"], capture_output=True, text=True)
        if create.returncode != 0:
            cprint(f"⚠️ [Execute] Failed to create sandbox env '{SANDBOX_ENV_NAME}': {create.stderr}", "yellow")
    except Exception as e:
        cprint(f"⚠️ [Execute] Sandbox env check error: {e}. Continuing without sandbox.", "yellow")

def reset_sandbox_env():
    """Reset the sandbox Conda environment at agent startup.
    To ensure clean state, delete the env if present and recreate with base Python only.
    """
    if not SANDBOX_CONDA_ENABLED:
        return
    try:
        # Remove environment if exists; ignore errors if it doesn't
        subprocess.run([CONDA_EXE, "env", "remove", "-y", "-n", SANDBOX_ENV_NAME], capture_output=True, text=True)
        # Recreate environment with specified python version
        create = subprocess.run([CONDA_EXE, "create", "-y", "-n", SANDBOX_ENV_NAME, f"python={SANDBOX_PYTHON_VERSION}"], capture_output=True, text=True)
        if create.returncode != 0:
            cprint(f"⚠️ [Execute] Failed to recreate sandbox env '{SANDBOX_ENV_NAME}': {create.stderr}", "yellow")
        else:
            cprint(f"✅ [Execute] Sandbox env '{SANDBOX_ENV_NAME}' reset with Python {SANDBOX_PYTHON_VERSION}.", "green")
    except Exception as e:
        cprint(f"⚠️ [Execute] Sandbox reset error: {e}. Proceeding without reset.", "yellow")