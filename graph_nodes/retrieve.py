from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from utils.tools import *
from llm.llm import model
import requests


@dataclass
class RetrieveOutput:
    thought: str = field(metadata={"description": "Your thought process for generating the RAG query."})
    query: str = field(metadata={"description": "the RAG query string you generated"})
    output_format = """
{
  "thought": <string>,
  "query": <string>
}
"""


def _build_default_query(state) -> str:
    parts: List[str] = []
    if state.issue_desc:
        parts.append(str(state.issue_desc))
    # 将最近一次执行输出中较为关键的信息拼接到查询
    try:
        if isinstance(state.output, dict):
            err = state.output.get("stderr") or ""
            out = state.output.get("stdout") or ""
            cmd = state.output.get("command") or ""
            if cmd:
                parts.append(f"Command: {cmd}")
            if err:
                parts.append(err[-800:])  # 取尾部以保留最近错误
            elif out:
                parts.append(out[-800:])
        elif isinstance(state.output, str):
            parts.append(state.output[-800:])
    except Exception:
        pass
    return " \n".join([p for p in parts if p])


def _call_rag_api(query_id: str, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """调用本地 RAG 检索服务，返回结果列表。
    期望本地服务在 http://localhost:8000 提供 /rag/query 接口。
    """
    payload = {
        "query_id": query_id,
        "error_message": query_text,
        "top_k": top_k,
    }
    try:
        resp = requests.post("http://localhost:8000/rag/query", json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])
    except Exception as e:
        return [{
            "result_id": -1,
            "question_title": "Retrieval Error",
            "answer_excerpt": f"{e}",
            "code_example": "",
            "relevance_score": 0.0,
            "url": ""
        }]


def _format_results_for_context(results: List[Dict[str, Any]]) -> List[str]:
    """将 RAG 检索结果格式化为简明的上下文条目，复用 read_context。"""
    formatted: List[str] = []
    for r in results:
        title = r.get("question_title", "")
        excerpt = r.get("answer_excerpt", "")
        code = r.get("code_example", "") or ""
        score = r.get("relevance_score", 0.0)
        url = r.get("url", "")
        entry = (
            f"[RAG] {title} (score={score})\n"
            f"URL: {url}\n"
            f"Answer: {excerpt}\n"
            f"Code: {code}"
        ).strip()
        formatted.append(entry)
    return formatted


def truncate_str(s: str, max_len: int) -> str:
    try:
        if len(s) <= max_len:
            return s
        return s[:max_len] + "..."
    except Exception:
        return s


def retrieve_node(state):
    cprint("📚 [Retrieve] retrieving information based on last output","red")

    # 构造查询（可由 LLM 规划，也提供默认回退）
    agent_log = state.logs.to_context()
    reflection = state.reflection.to_context()
    prompt = f"""
You are the Retrieve module. Based on the current issue description, the last output, and existing reflections, generate a query string for RAG.
[Agent Logs]\n{agent_log}
[Current Issue]\n- Description: {state.issue_desc}\n- Output since last execution: {state.output}
[Warning]\n{describe_schema(RetrieveOutput)}
"""

    try:
        response = safe_invoke(model, RetrieveOutput, prompt)
        thought = response.get("thought")
        query_text = response.get("query") or _build_default_query(state)
    except Exception:
        thought = "Failed to generate query via LLM, using default query."
        query_text = _build_default_query(state)

    # 调用本地 RAG 服务
    results = _call_rag_api(query_id="agent-query", query_text=query_text, top_k=5)
    formatted_ctx = _format_results_for_context(results)

    # 将检索结果写入日志，并复用 read_context 以便后续 reflection
    new_logs = state.logs.add_entry(type="retrieve", entry=f"Query: {truncate_str(query_text, 200)}")

    return {
        "phase": "retrieve",
        "thought": thought,
        "logs": new_logs,
        "read_context": formatted_ctx,
        "output": {
            "query": query_text,
            "results": results
        }
    }