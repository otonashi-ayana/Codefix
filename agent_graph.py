from langgraph.graph import StateGraph
from utils.tee import setup_run_log
from utils.tools import *
from state.agent_state import AgentState
from graph_nodes.planner import planner_node
from graph_nodes.edit import edit_node
from graph_nodes.explore import explore_node
# from graph_nodes.recover import recover_node
from graph_nodes.reflection import reflection_node
from graph_nodes.execute import execute_node
from graph_nodes.execute import reset_sandbox_env
from graph_nodes.read import read_node
from graph_nodes.retrieve import retrieve_node
from graph_nodes.end import end_node

# Duplicate console output to file early in process startup
_log_path, _close_log = setup_run_log(directory="logs", prefix="output", use_uuid=False)
# Reset sandbox env on process start to ensure clean execution environment
try:
  reset_sandbox_env()
except Exception as e:
  cprint(f"⚠️ [Startup] Sandbox reset failed: {e}", "yellow")

graph = StateGraph(AgentState)

register_node(graph, "planner", planner_node)
register_node(graph, "explore", explore_node)
register_node(graph, "edit", edit_node)
# register_node(graph, "recover", recover_node)
register_node(graph, "reflection", reflection_node)
register_node(graph, "execute", execute_node)
register_node(graph, "read", read_node)
register_node(graph, "retrieve", retrieve_node)
register_node(graph, "end", end_node)

# NODE_DESC = get_node_descriptions(graph)

graph.set_entry_point("planner")

# Agent take Actions based on Planner
graph.add_conditional_edges(
  "planner",
  lambda state: state.plan
)
# Actions -> Reflection
graph.add_edge("explore","reflection")
graph.add_edge("execute","reflection")
graph.add_edge("edit","execute")
# graph.add_edge("recover","reflection")
graph.add_edge("read","reflection")
graph.add_edge("retrieve","reflection")

# Reflection -> Planner
graph.add_edge("reflection","planner")

agent = graph.compile()
state = AgentState()
for _ in agent.stream(state, config={"recursion_limit": 100}):
  pass

# Optional: ensure log file is closed on normal exit
try:
  _close_log()
except Exception:
  pass