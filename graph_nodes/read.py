from dataclasses import dataclass, field
from langgraph.types import Overwrite
from copy import deepcopy
from utils.tools import *
from llm.llm import model
from runtime_env import *

@dataclass
class ReadOutput:
    thought: str = field(metadata={"description": "Your thought process for choosing which file to read."})
    targets: list[str] = field(metadata={"description": "The exact list of target file paths from the workspace structure to read."})
    output_format = """
{
  "thought": <string>,
  "targets": [
    "path/to/file1.py",
    "path/to/file2.js",
    "path/to/file3.py"
   ]
}
"""

@dataclass
class FileSummaryOutput:
    thought: str = field(metadata={"description": "Your thought process for summarizing the file content."})
    summary: str = field(metadata={"description": "A one-sentence summary of the file content."})
    output_format = """
{
  "thought": <string>,
  "summary": <string>
}
"""

@dataclass
class DirSummaryOutput:
    thought: str = field(metadata={"description": "Your thought process for summarizing the directory content."})
    summary: str = field(metadata={"description": "A one-sentence summary of the directory content."})
    output_format = """
{
  "thought": <string>,
  "summary": <string>
}
"""

def read_node(state):
    cprint("📖 [Read] Reading files to gather information","purple")
    # step 1: decide which files to read
    choose_thought, read_context, new_logs = choose_files_to_read(state)
    # step 2: update workspace map with read file summaries
    new_ws_state = state.workspace_state
    new_log_state = state.logs
    for file_path, file_content in read_context.items():
        #TODO: Implement with async calls
        file_summary_thought, new_ws_state, new_log_state = generate_file_info(new_ws_state, new_log_state, file_path, file_content)
        if new_ws_state.check_for_init_directory_info(file_path):
            parent_dir_path = new_ws_state.get_parent_directory_path(file_path)
            children_summaries = new_ws_state.get_children_summaries(new_ws_state, parent_dir_path)
            dir_summary_thought, new_ws_state, new_log_state = generate_dir_info(new_ws_state, new_log_state, parent_dir_path, children_summaries)
            
    return {
        "phase": "read",
        "logs": new_log_state,
        "workspace_state": new_ws_state,
        "thought": choose_thought,
        # 细粒度合并策略（保持原有格式：列表，元素为单键字典 {file_path: content}）：
        # 基于 state.read_context 深拷贝，先移除所有将要更新的 file_path，再把新项以原格式追加，最后整体覆盖。
        "read_context": (lambda old_list, new_rc: (
            (lambda merged_list: Overwrite(merged_list))(
                (lambda filtered_old: (
                    filtered_old + [
                        {fp: content} for fp, content in new_rc.items()
                    ]
                ))(
                    [
                        elem for elem in (old_list or [])
                        if not any(fp in elem for fp in new_rc.keys())
                    ]
                )
            )
        ))(deepcopy(getattr(state, "read_context", [])), read_context),
    }

def choose_files_to_read(state) -> list[str]:
    cprint("📖 [Read] Deciding which files to read","purple")
    prompt = f"""
You are the Read module of an autonomous bugfix agent. Your task is to decide which files' content to read based on the current agent state and plan. Use Chinese to generate natural parts of the responses.
[Agent Logs]
Here are relevant agent actions result about current issue and workspace:
{state.logs.to_context()}
[Current Issue]
- Description: {state.issue_desc}
- Output since last execution: {state.output}
[Workspace Structure]
- {state.workspace_state.to_context()}
[Warning]
{describe_schema(ReadOutput)}
"""
    response = safe_invoke(model, ReadOutput, prompt)
    thought = response['thought']
    targets = [target.strip() for target in response['targets']]  # TODO Need Value Format Check!
    new_logs = state.logs.add_entry(type="read", entry=f"Targets: {targets}")
    read_context = read(targets)
    return thought, read_context, new_logs

def generate_dir_info(ws_state, log_state, target: str, children_summaries:dict[str, str]):
    cprint(f"🗂️ [Read] Generating summary for directory: {target}","purple")
    prompt = f"""
Summarize the content of the directory at {target} one very short sentence based on its children files.
[Workspace Structure]
- {ws_state.to_context()}
[Children Summarization Content]
{"\n".join([f"- {path}: {summary}" for path, summary in children_summaries.items()])}
[Warning]
{describe_schema(DirSummaryOutput)}
"""
    response = safe_invoke(model, DirSummaryOutput, prompt, should_print=False)
    thought = response['thought']
    new_workspace_state = ws_state.update_directory_info(target, response['summary'])
    new_logs = log_state.add_entry(type="read", entry=f"Updated workspace dir info for {target}: {response['summary']}")
    return thought, new_workspace_state, new_logs

def generate_file_info(ws_state, log_state, target: str, file_content: str):
    cprint(f"🗂️ [Read] Generating summary for file: {target}","purple")
    prompt = f"""
Summarize the content of the file at {target} with one very short sentence.
[Workspace Structure]
- {ws_state.to_context()}
[File Content]
{file_content}
[Warning]
{describe_schema(FileSummaryOutput)}
"""
    response = safe_invoke(model, FileSummaryOutput, prompt, should_print=False)
    thought = response['thought']
    new_workspace_state = ws_state.update_file_info(target, response['summary'])
    new_logs = log_state.add_entry(type="read", entry=f"Updated workspace info for {target}: {response['summary']}")
    return thought, new_workspace_state, new_logs


def read(targets: list[str]) -> dict[str, str]:
    """Read the content of the specified files in the workspace.
    Args:
        targets (list[str]): List of file paths to read.
    Returns:
        dict[str, str]: A dictionary mapping file paths to their content.
    """
    contents = {}
    workspace_path = os.path.join(os.getcwd(), WORKSPACE_PATH)
    for target in targets:
        file_path = os.path.join(workspace_path, target)
        try:
            with open(file_path, 'r') as file:
                contents[target] = file.read()
                if file_path.endswith(('.csv','.xlsx')) and len(contents[target]) > 200:
                    contents[target] = contents[target][:200] + "\n...[truncated]"
        except Exception as e:
             print(f"[Read] Error reading file: {str(e)}")
    return contents