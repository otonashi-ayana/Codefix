from dataclasses import dataclass, field
from llm.llm import model
from langgraph.types import Overwrite
from utils.tools import *


@dataclass
class ReflectionOutput:
    thought: str = field(metadata={"description": "Short thought process during reflection."})
    reflection: str = field(metadata={"description": "Short reflection on the previous actions taken about how to improve."})
    issue_desc: str = field(metadata={"description": "A very short refined description of the current issue after reflection."})
    output_format = """
{
  "thought": <string>,
  "reflection": <string>,
  "issue_desc": <string>
}
"""

def reflection_node(state):
    cprint("💡 [Reflection] Reflecting on previous actions to improve future performance","bright_black")
    action = state.plan
    agent_log = state.logs.to_context()
    workspace_structure = state.workspace_state.to_context()
    action_context = ""
    # action_thought = state.thought
    action_thought = ""
    clear_read_context = False
    if action == "execute":
        action_context = state.output
    elif action == "read":
        action_context = "READ Node has got complete codes below: \n" + format_read_context(state.read_context)
    elif action == "explore":
        action_context = None
    elif action == "edit":
        action_context = state.edit_context
        clear_read_context = True
        other_context = "Edit has been applied and we may need to run a new round of execution to verify the fix."
    # TODO after recovery node is added
    # elif action == "recover":
    #     action_context = state.recover_context
    # After RAG retrieve, reuse read_context to carry retrieved items
    elif action == "retrieve":
        action_context = format_read_context(state.read_context)
    prompt = f"""
You are the Reflection module of an autonomous bugfix agent. Your task is to reflect on the previous actions taken by the agent briefly to identify what went well, what didn't, and how to improve future performance. For Current issue description, refine it if necessary based on your reflection, or keep it unchanged. Use Chinese to generate natural parts of the responses.
[Previous Action]
- Action Phase: {action}
{f"- Action Context: \n{action_context}" if action_context else ""}
{f"- Action Thought: \n{action_thought}" if action_thought else ""}
[Agent Logs]
Here are relevant agent actions result about current issue and workspace:
{agent_log}
[Current Issue]
- Description: {state.issue_desc}
- Output since last execution: {state.output}
[Workspace Structure]
- {workspace_structure}
[Warning]
{other_context if 'other_context' in locals() else ""}
{describe_schema(ReflectionOutput)}
"""
    response = safe_invoke(model, ReflectionOutput, prompt)
    new_reflection = state.reflection.add_entry(entry=response['reflection'])
    new_logs = state.logs.add_entry(type="reflection", entry=f"Action: {action}, Reflection: {response['reflection']}")
    update_data = {
        "phase": "reflection",
        "thought": response['thought'],
        "reflection": new_reflection,
        "logs": new_logs,
        "issue_desc": response['issue_desc'],
    }
    if clear_read_context:
        update_data["read_context"] = Overwrite([])
    return update_data