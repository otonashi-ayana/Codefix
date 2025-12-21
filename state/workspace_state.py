import json
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass(frozen=True)
class WorkspaceState:
    """
    workspace_map: {
        "type": "directory",
        "name": "root",
        "path": "",
        "children": [
            {
                "type": "file",
                "name": "file1.py",
                "path": "file1.py",
                "summary": "This file contains...",
                "dependencies": ["file2.py", "lib/utils.py"],
                "last_modified": "2024-10-01T12:34:56Z"
            },
            {
                "type": "directory",
                "name": "src",
                "path": "src",
                "children": [
                    ...
                ],
                "summary": "This directory contains source files...",
                "last_modified": "2024-10-01T12:00:00Z"
            }
        ]
    }"""
    workspace_map: Dict[str, Any] = field(default_factory=dict)

    def update_workspace_map(self, new_map: dict) -> 'WorkspaceState':
        """Return a new WorkspaceState with replaced workspace_map."""
        return WorkspaceState(workspace_map=new_map)

    def get_to_dir(self, path: str) -> dict:
        """Return the directory node dict for the given path.

        For a path like "dir_1/dir_2/file_1", this returns the dict for "dir_2".
        """
        path_list = path.split("/")
        current_map = self.workspace_map
        for name in path_list[:-1]:  # traverse directories only
            current_map = next(
                (
                    curr
                    for curr in current_map.get('children', [])
                    if curr.get('name') == name and curr.get('type') == 'directory'
                ),
                None,
            )
            if current_map is None:
                raise KeyError(f"Directory '{name}' not found in path '{path}'")
        return current_map

    def check_for_init_directory_info(self, path: str) -> bool:
        """Check if it's time to initialize directory info based on children completeness."""
        parent_dir = self.get_to_dir(path)
        if parent_dir.get('summary'):
            return False  # already initialized
        children = parent_dir.get('children', [])
        if not children:
            return False
        completed_counts = sum(1 for child in children if child.get('summary'))
        children_completed = completed_counts / len(children) > 0.5
        return children_completed
    
    
    def update_directory_info(self, path: str, summary) -> 'WorkspaceState':
        """Update a directory node's info.summary and return a new WorkspaceState."""
        # Deep copy via JSON to avoid mutating original
        temp_map = json.loads(json.dumps(self.workspace_map,ensure_ascii=False))

        if path == "":
            if temp_map.get("type") == "directory" and temp_map.get("name") == "":
                temp_map["summary"] = summary
            return WorkspaceState(temp_map)
        
        path_list = [p for p in path.split("/") if p != ""]
        
        current = temp_map
        for name in path_list:
            next_dir = next(
                (
                    child
                    for child in current.get("children", [])
                    if child.get("type") == "directory" and child.get("name") == name
                ),
                None,
            )
            if next_dir is None:
                return WorkspaceState(temp_map)
            current = next_dir

        current["summary"] = summary

        return WorkspaceState(temp_map)

    def update_file_info(self, path: str, summary) -> 'WorkspaceState':
        """Update a file node's info.summary and return a new WorkspaceState."""
        # Deep copy via JSON to avoid mutating original
        temp_map = json.loads(json.dumps(self.workspace_map,ensure_ascii=False))

        # Traverse in the copied map
        path_list = path.split("/")
        current_map = temp_map
        for name in path_list[:-1]:
            current_map = next(
                (
                    curr
                    for curr in current_map.get('children', [])
                    if curr.get('name') == name and curr.get('type') == 'directory'
                ),
                None,
            )
            if current_map is None:
                break
        if current_map is None:
            return WorkspaceState(temp_map)

        filename = path_list[-1]
        for child in current_map.get('children', []):
            if child.get('name') == filename and child.get('type') == 'file':
                child['summary'] = summary
                break

        return WorkspaceState(temp_map)

    def to_dict(self):
        return self.workspace_map
    
    def to_context(self, path: str = "", max_length: int = 2000) -> str:
        """Convert the workspace map or a subdirectory to a string context for the agent."""
        current_map = self.workspace_map if not path else self.get_to_dir(path)
        cleaned_map = self.strip_fields(
            current_map,
            remove_keys={"dependencies", "last_modified"}
        )
        context_str = json.dumps(cleaned_map, indent=2, ensure_ascii=False)
        if len(context_str) > max_length:
            context_str = context_str[:max_length] + "\n... (truncated)"
        return context_str
    
    def strip_fields(self, obj, remove_keys: set):
        if isinstance(obj, dict):
            return {
                k: self.strip_fields(v, remove_keys)
                for k, v in obj.items()
                if k not in remove_keys
            }
        elif isinstance(obj, list):
            return [self.strip_fields(item, remove_keys) for item in obj]
        else:
            return obj
        
    @staticmethod
    def load(data: dict) -> 'WorkspaceState':
        """Return a new WorkspaceState loaded from dict."""
        return WorkspaceState(workspace_map=data)
    
    @staticmethod
    def get_parent_directory_path(file_path: str) -> str:
        parts = file_path.strip("/").split("/")
        if len(parts) <= 1:
            return ""
        return "/".join(parts[:-1])
    @staticmethod
    def get_children_summaries(state, parent_dir_path: str) -> dict[str, str]:
        parent_dir = state.get_to_dir(parent_dir_path)
        children = parent_dir.get('children', [])
        summaries = {}
        for child in children:
            child_path = child.get('path')
            child_summary = child.get('summary', '')
            summaries[child_path] = child_summary
        return summaries
    