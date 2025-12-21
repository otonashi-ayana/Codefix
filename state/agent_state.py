import json
from dataclasses import dataclass, field, replace
from typing import Optional, Any, List, Annotated
from state.workspace_state import WorkspaceState
from state.reflection_state import ReflectionState
from state.agent_logs import AgentLogs
from operator import add


@dataclass(frozen=True)
class AgentState:
    """Immutable agent state compatible with LangGraph-style updates.

    All "update" operations return a new AgentState instance.
    """
    phase: str = "initial"
    workspace_state: WorkspaceState = field(default_factory=WorkspaceState)
    logs: AgentLogs = field(default_factory=AgentLogs)
    thought: Optional[str] = None
    # edit_proposals: List[Any] = field(default_factory=list)
    reflection: ReflectionState = field(default_factory=ReflectionState)
    read_context: Annotated[list, add] = field(default_factory=list)
    edit_context: Optional[Any] = None
    command: Optional[str] = None
    output: Optional[Any] = None
    issue_desc: Optional[str] = "Issue not founded now, try to run the project to find potential issues."
    plan: Optional[Any] = None

    # -------- Immutable update helpers --------
    def with_phase(self, phase: str) -> "AgentState":
        return replace(self, phase=phase)

    def with_workspace(self, workspace_state: WorkspaceState) -> "AgentState":
        return replace(self, workspace_state=workspace_state)

    def with_logs(self, logs: AgentLogs) -> "AgentState":
        return replace(self, logs=logs)

    def append_log(self, type: str, entry: str) -> "AgentState":
        new_logs = self.logs.add_entry(type, entry)
        return replace(self, logs=new_logs)

    def with_thought(self, thought: Optional[str]) -> "AgentState":
        return replace(self, thought=thought)

    # def with_edit_proposals(self, proposals: List[Any]) -> "AgentState":
    #     return replace(self, edit_proposals=list(proposals))

    def with_reflection(self, reflection: ReflectionState) -> "AgentState":
        return replace(self, reflection=reflection)

    def append_reflection(self, entry: str) -> "AgentState":
        new_reflection = self.reflection.add_entry(entry)
        return replace(self, reflection=new_reflection)

    def with_read_context(self, ctx: Any) -> "AgentState":
        return replace(self, read_context=ctx)

    def with_edit_context(self, ctx: Any) -> "AgentState":
        return replace(self, edit_context=ctx)

    def with_output(self, output: Any) -> "AgentState":
        return replace(self, output=output)

    def with_issue_desc(self, issue: Optional[str]) -> "AgentState":
        return replace(self, issue_desc=issue)

    def with_plan(self, plan: Any) -> "AgentState":
        return replace(self, plan=plan)

    def with_command(self, command: Optional[str]) -> "AgentState":
        return replace(self, command=command)

    # -------- Serialization --------
    def to_dict(self):
        return {
            "phase": self.phase,
            "workspace_state": self.workspace_state.to_dict(),
            "logs": self.logs.to_list(),
            "plan": self.plan,
            "reflection": self.reflection.to_list(),
            "thought": self.thought,
            "output": self.output,
            "command": self.command,
            "issue_desc": self.issue_desc,
            "read_context": self.read_context,
            "edit_context": self.edit_context,
            # "edit_proposals": self.edit_proposals,
        }

    @staticmethod
    def from_dict(data: dict) -> "AgentState":
        return AgentState(
            phase=data.get("phase", "initial"),
            workspace_state=WorkspaceState().load(data.get("workspace_state", {})),
            logs=AgentLogs().load(data.get("logs", [])),
            plan=data.get("plan"),
            reflection=ReflectionState().load(data.get("reflection", [])),
            thought=data.get("thought"),
            output=data.get("output"),
            command=data.get("command"),
            issue_desc=data.get("issue_desc"),
            read_context=data.get("read_context"),
            edit_context=data.get("edit_context"),
            # edit_proposals=data.get("edit_proposals", []),
        )

    def save(self, path: str = "agent_state.json") -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=4)

    @staticmethod
    def load(path: str = "agent_state.json") -> "AgentState":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return AgentState.from_dict(data)






