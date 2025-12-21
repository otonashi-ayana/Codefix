# nodes/planner_node.py
from dataclasses import dataclass, field
from utils.tools import *
from llm.llm import model

NODE_DESC = """
- edit: proposes and applies code edits to fix the issue, used when code changes are needed.
- execute: runs shell commands in the workspace to test or verify code changes, used when needing to execute code to see results.
- read: reads specific files from the workspace to gather information, used when more context is needed about the codebase.
- retrieve: retrieves external information from StackOverflow based on last output, used after `execute` to provide references for subsequent fixes.
- end: concludes the bugfix process when the issue is resolved."""
@dataclass
class PlannerOutput:
    thought: str = field(metadata={"description": "Your thought process for choosing the next action phase."})
    action: str = field(metadata={"description": "The next action phase to take. Must be one of these words: execute, edit, read, retrieve, end."})
    output_format = """
{
  "thought": <string>,
  "action": "<one of actions>"
}
"""

def planner_node(state):
    cprint("🧠 [Planner] Analyzing current state and generating plan","red")
    tool_info = NODE_DESC
    agent_log = state.logs.to_context()
    reflection = state.reflection.to_context()
    read_context = format_read_context(state.read_context)
    prompt = f"""
You are the Planner module of an autonomous bugfix agent. Your task is to decide the next action phase. Based on the current agent state, logs, and available tools, choose the most appropriate action phase to proceed with. Use Chinese to generate natural parts of the responses.
[Agent Logs]
Here are relevant agent actions result about current issue and workspace:
{agent_log}
[Read Context]
READ Node has got COMPLETE CODES below: \n
{read_context}
[Current Issue]
- Description: {state.issue_desc}
- Output since last execution: {state.output}
[Tool Descriptions]
Here are actions you can make now, and their corresponding Args Descriptions:{tool_info}
[Warning]
{describe_schema(PlannerOutput)}
"""
    if state.phase == "initial" or not state.workspace_state.workspace_map:
        thought = "Now it is the initial phase or workspace is unknown. I will choose 'explore' to gather information about the workspace. Then, find the way to run this project to find potential issues."
        plan = "explore"
    else:
        response = safe_invoke(model, PlannerOutput, prompt)
        thought = response['thought']
        plan = response['action']

    new_logs = state.logs.add_entry(type="planner", entry=f"Planned Action: {plan}")
    return {
        "phase": "planner",
        "thought": thought,
        "plan": plan,
        "logs": new_logs,
    }
