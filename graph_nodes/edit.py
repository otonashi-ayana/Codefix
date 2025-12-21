from dataclasses import dataclass, field
import os
from copy import deepcopy
from langgraph.types import Overwrite
from llm.llm import model
from runtime_env import WORKSPACE_PATH
from utils.tools import *

@dataclass
class ProposalOutput:
    thought: str = field(metadata={"description": "Your thought process for proposing code edits."})
    proposal: list[list[str, str]] = field(metadata={"description": "A list of specific code edit proposal including file paths and brief description of every edit step.",})
    output_format = """
{
  "thought": <string>,
  "proposal": [
    ["<desc of step01>", "path/to/file1.py, path/to/file2.py"],
    ["<desc of step02>", "path/to/file3.py"]
  ]
}"""

@dataclass
class EditOutput:
    thought: str = field(metadata={"description": "Your thought process for generating code edits."})
    edits: dict[str, str] = field(metadata={"description": "A dictionary mapping file paths to their complete content after applying the edits."})
    output_format = """
{
  "thought": <string>,
  "edits": {
    "path/to/file1.py": "<full content of file1.py after edits>",
    "path/to/file2.py": "<full content of file2.py after edits>"
}
"""

def edit_node(state):
    cprint("✏️ [Edit] Proposing edits needed to fix the issue", "yellow")
    thought, proposals, log_after_proposal = form_proposal(state)
    proposal_length = len(proposals)
    cprint("✏️ [Edit] Applying edits to the workspace", "yellow")
    logs = log_after_proposal
    # 使用最新的 read_context 作为逐步编辑的上下文快照，并在每一步编辑后刷新
    current_read_ctx = deepcopy(getattr(state, "read_context", []))
    for idx, proposal in enumerate(proposals):
        logs, current_read_ctx = apply_edit(state, logs, current_read_ctx, proposals, proposal, idx + 1, proposal_length)
    # 返回覆盖后的 read_context，确保下一个节点拿到最新内容，避免死循环
    # TODO ws_map info of the edited files are expected to be updated in the next read node
    return {
        "phase": "edit",
        "logs": logs,
        "thought": thought,
        "edit_proposals": proposals,
        "read_context": Overwrite(current_read_ctx),
    }

def form_proposal(state):
    agent_log = state.logs.to_context()
    read_context = format_read_context(state.read_context)
    prompt = f"""
You are the Edit module of an autonomous bugfix agent. Your task is to decompose the current issue into necessary steps to fix it based on the agent's state and context (ONLY contains steps that needs text editing). Use Chinese to generate natural parts of the responses.
[Agent Logs]
Here are relevant agent actions result about current issue and workspace:
{agent_log}
[Current Issue]
- Description: {state.issue_desc}
- Output since last execution: {state.output}
[Read Context]
{read_context}
[Current Thought]
- {state.thought}
[Warning]
If you see absolute path like {WORKSPACE_PATH}/ from execute outputs, remember your response path must strictly start after it, DO NOT include any root project path. The returned path must be project-relative (e.g. src/file.py).
{describe_schema(ProposalOutput)}
"""
    response = safe_invoke(model, ProposalOutput, prompt)
    # TODO NO thought logged, remember to build dev log
    new_logs = state.logs.add_entry(type="edit", entry=f"Proposed Edits: {response['proposal']}")
    return response['thought'], response['proposal'], new_logs

def write_edit_to_file(file_path, content):
    workspace_path = os.path.join(os.getcwd(), WORKSPACE_PATH)
    full_path = os.path.join(workspace_path, file_path)
    try:
        with open(full_path, 'w') as file:
            file.write(content)
        print(f"[Edit] Successfully wrote edits to {file_path}")
    except Exception as e:
        # TODO fallback to this node and input the exception message
        print(f"[Edit] Error writing to file {file_path}: {str(e)}")


def apply_edit(state, logs, current_read_ctx, proposals, proposal, step, length):
    print(f"  - [{step}/{length}] Applying edit: {proposal}")
    # 使用本地最新的 read_context 快照，而不是 state.read_context（避免不及时刷新导致上下文过期）
    read_context = format_read_context(current_read_ctx)
    prompt = f"""
You are the Edit module of an autonomous bugfix agent. Your task is to generate the specific code edits needed to fix the current issue based on the agent's state and context.
[Current Issue]
- Description: {state.issue_desc}
- Output since last execution: {state.output}
[Read Context]
{read_context}
[Edit Proposal]
- {proposals}
[Your Current Task]
- {proposal}
[Warning]
{describe_schema(EditOutput)}
"""
    response = safe_invoke(model, EditOutput, prompt)
    # TODO: Achieve git and diff in the future
    for file_path, content in response['edits'].items():
        write_edit_to_file(file_path, content)
    # 将已编辑的文件内容同步到 current_read_ctx（覆盖旧条目，必要时追加新条目）
    if isinstance(current_read_ctx, list):
        edited_paths = set(response['edits'].keys())
        # 移除将要更新的旧条目
        filtered_old = [
            elem for elem in (current_read_ctx or [])
            if not any(fp in elem for fp in edited_paths)
        ]
        # 追加最新内容
        current_read_ctx = filtered_old + [{fp: cnt} for fp, cnt in response['edits'].items()]
    logs = logs.add_entry(type="edit", entry=f"Applied edits [{step}/{length}]: {proposal}")
    logs = logs.add_entry(type="edit", entry=f"Edits made to files: {list(response['edits'].keys())}")
    return logs, current_read_ctx