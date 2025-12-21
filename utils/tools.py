
from runtime_env import *
from dataclasses import fields
import json

def format_read_context(read_context):
    """
    Format the read_context into a printable string.

    Accepted input shapes:
    - List[Dict[str, str]]: Typical output from READ node where each item is a mapping of filename -> content.
    - List[str]: Fallback format from Retrieve node where each item is a formatted text entry.
    - Dict[str, str]: Single mapping of filename -> content.
    - str: Already formatted text; returned as-is.
    - None or empty: returns empty string.
    """
    if not read_context:
        return ""

    # If it's already a string, just return it
    if isinstance(read_context, str):
        return read_context

    formatted_blocks = []

    # If it's a dict, format as a single block of filename -> content
    if isinstance(read_context, dict):
        block_lines = []
        for filename, content in read_context.items():
            block_lines.append(f"- {filename}:")
            pretty_content = str(content).strip()
            block_lines.append(f"{pretty_content}")
            block_lines.append("")
        formatted_blocks.append("\n".join(block_lines))
        return "\n".join(formatted_blocks)

    # If it's a list, check element types
    if isinstance(read_context, list):
        for item in read_context:
            # Item is a dict: filename -> content
            if isinstance(item, dict):
                block_lines = []
                for filename, content in item.items():
                    block_lines.append(f"- {filename}:")
                    pretty_content = str(content).strip()
                    block_lines.append(f"{pretty_content}")
                    block_lines.append("")
                formatted_blocks.append("\n".join(block_lines))
            # Item is a string: put directly
            elif isinstance(item, str):
                formatted_blocks.append(item.strip())
            # Fallback: convert to string
            else:
                formatted_blocks.append(str(item).strip())
        return "\n".join(formatted_blocks)

    # Unknown type: fallback to string conversion
    return str(read_context)

def register_node(graph, name: str, fn):
    graph.add_node(name, fn)
    if not hasattr(graph, "tool_descriptions"):
        graph.tool_descriptions = {}
    graph.tool_descriptions[name] = fn.__doc__ or "No description."

def get_node_descriptions(graph):
    descs = []
    for name, desc in graph.tool_descriptions.items():
        if desc:
            descs.append(f"- {name}: {desc.strip()}")
    return descs

def describe_schema(cls):
    lines = ["Your response **must** be a JSON object with the following format:"]
    for f in fields(cls):
        if f.name.startswith("template_"):
            continue
        desc = f.metadata.get("description", "")
        lines.append(f'- {f.name} ({f.type.__name__}): {desc}')
    if hasattr(cls, "output_format"):
        lines.append(f"Here is an example of the expected output format:{cls.output_format}")
    return "\n".join(lines)

def safe_invoke(model, cls, input: str, config: dict = None, stop: list = None, retries: int = 3, should_print=True) -> str:
    if DEV_MODE and should_print:
        cprint(f"[safe_invoke] prompt: {input}","bright_black")
    for attempt in range(1, retries + 1):
        try:
            response = model.invoke(input, config=config, stop=stop)
            data = json.loads(response.content)
            field_names = {f.name for f in fields(cls)}
            filtered_data = {k: v for k, v in data.items() if k in field_names}
            missing = field_names - filtered_data.keys()
            if missing:
                raise ValueError(f"Missing fields: {missing}")
            if DEV_MODE and should_print:
                cprint(f"[safe_invoke] response: {json.dumps(filtered_data, indent=2, ensure_ascii=False)}","bright_blue")
            # return cls(**filtered_data)
            return filtered_data
        except json.JSONDecodeError as e:
            print(f"[safe_invoke:{attempt}] JSON decode error: {str(e)}. Response content: {response.content}")
        except Exception as e:
            print(f"[safe_invoke:{attempt}] Error during LLM invocation: {str(e)}")
    # return cls(**{f.name: None for f in fields(cls)})
    return {f.name: None for f in fields(cls)}

def cprint(text: str, color: str = "white"):
    colors = {
        "red": "31",
        "green": "32",
        "yellow": "33",
        "blue": "34",
        "purple": "35",
        "cyan": "36",
        "bright_black": "90",
        "bright_blue": "94",
        "white": "37",
    }
    code = colors.get(color, "37")
    print(f"\033[{code}m{text}\033[0m")

