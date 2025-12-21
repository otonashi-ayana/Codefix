import copy
import datetime
from typing import Optional


class AgentLogs:
    def __init__(self, logs: Optional[list[dict]] = None):
        """Agent logs may contain various types of entries:
        (1) recent executions: command, output.
        (2) action records:tool calls, reflections, etc.
        (3) error logs: errors encountered during execution and handling.
        (4) edit histories: changes made to files in the workspace.
        TODO: Figure out necessary to log and how to use them.
        """
        self._logs = copy.deepcopy(logs) if logs else []  # List to store log entries

    def add_entry(self, type: str, entry: str):
        new_logs = copy.deepcopy(self._logs)
        new_logs.append({
            "type": type,
            "entry": entry,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        })
        return AgentLogs(new_logs)

    def to_list(self):
        return copy.deepcopy(self._logs)

    def to_context(self, types: Optional[list[str]] = None, limit: int = 6) -> str:
        """Convert recent logs to a string context for agent's reference.
        Args:
            limit (int): Number of recent logs to include.
        Returns:
            str: Formatted string of recent logs.
        """
        logs = self._logs
        if types:
            logs = [log for log in logs if log["type"] in types]
        recent_logs = logs[-limit:]
        lines = [f"{log['type'].upper()}: {log['entry']}" for log in recent_logs]
        return "\n".join(lines)

    def load(self, logs_list: list[dict]):
        return AgentLogs(logs_list)