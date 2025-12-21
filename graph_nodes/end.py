from utils.tools import *


def end_node(state):
    cprint("🏁 [End] Finalizing agent operations and saving state","green")
    final_logs = state.logs.add_entry("system", "Agent operations have concluded.")
    # Persist current state snapshot immutably
    state.with_logs(final_logs).save()
    return {"phase": "end", "logs": final_logs}