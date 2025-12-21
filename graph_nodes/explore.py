from datetime import datetime
import os
from utils.tools import *
from runtime_env import *
    
def explore_node(state):
    cprint("🔍 [Explore] Exploring the workspace to gather information", "cyan")
    # TODO: Currently we explore the whole workspace just once after init, in future it may be expanded.
    new_map = explore_workspace()
    new_workspace_state = state.workspace_state.update_workspace_map(new_map)
    new_logs = state.logs.add_entry(type="explore", entry="Explored workspace structure.")
    return {
        "phase": "explore",
        "workspace_state": new_workspace_state,
        "logs": new_logs,
    }

def explore_workspace(target: str="", max_depth: int=8) -> str:
    """Explore the user workspace and list files and directories.
    Args:
        target (str): The target path within the workspace to explore. 
        max_depth (int): Maximum depth to explore in the directory structure.
    Returns:
        str: A structured representation of the workspace contents.
    """
    workspace_path = os.path.join(os.getcwd(), WORKSPACE_PATH)
    target_path = os.path.join(workspace_path, target)
    excluded_paths = {"node_modules", ".git", "__pycache__", ".vscode",".condarc","environment.yml"}

    if not os.path.exists(target_path):
        return {"error": f"Path not existed: {target_path}"}

    def explore(path, depth):
        if depth > max_depth:
            return {"note": "Exceeded maximum depth, stopping recursion."}

        rel_path = os.path.relpath(path, workspace_path)

        # -------------------------
        # File node
        # -------------------------
        if os.path.isfile(path):
            return {
                "type": "file",
                "name": os.path.basename(path),
                "path": rel_path,
                "summary": "",
                "dependencies": [],
                "last_modified": get_last_modified(path)
            }
        # -------------------------
        # Directory node
        # -------------------------
        children = []
        try:
            for entry in os.listdir(path):
                if entry in excluded_paths:
                    continue
                entry_path = os.path.join(path, entry)
                children.append(explore(entry_path, depth + 1))
        except PermissionError:
            return {
                "type": "directory",
                "name": os.path.basename(path),
                "path": rel_path,
                "children": [],
                "summary": "",
                "last_modified": "unknown"
            }

        return {
            "type": "directory",
            "name": os.path.basename(path),
            "path": rel_path,
            "children": children,
            "summary": "",
            "last_modified": get_last_modified(path)
        }

    # ---------------- top-level wrapper ----------------
    result = explore(target_path, 0)

    return result

def get_last_modified(path):
    """Return ISO formatted last modified time."""
    try:
        ts = os.path.getmtime(path)
        return datetime.utcfromtimestamp(ts).isoformat() + "Z"
    except:
        return "unknown"