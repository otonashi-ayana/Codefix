# Codefix

一个基于 **LangGraph** 的代码修复/代码助手实验项目：通过“规划 → 探索 → 编辑 → 执行 → 反思”的循环式工作流，在本地工作区中读取代码、检索信息、修改文件并在隔离的 Sandbox 环境里执行验证。

> 主要语言：Python  
> 默认分支：`master`

---

## 功能概览

该项目使用 LangGraph 将多个节点（node）编排成一个可循环的 Agent 图（graph），核心流程大致如下：

- **planner**：生成下一步计划（决定接下来走哪个动作节点）
- **explore**：探索项目结构/定位问题
- **read**：读取文件内容
- **retrieve**：检索相关信息/上下文
- **edit**：对代码进行修改
- **execute**：执行命令/运行测试（可在 Conda Sandbox 中运行）
- **reflection**：对执行结果进行反思与总结，返回 planner 继续迭代
- **end**：结束流程

入口脚本会在启动时：
1. 将控制台输出同时写入 `logs/`（便于回放）
2. 尝试重置 Sandbox，确保执行环境干净
3. 编译并运行 LangGraph 的流式执行（`recursion_limit=100`）

---

## 项目结构

仓库根目录（`master`）包含以下关键内容：

- `agent_graph.py`：主入口，构建并运行 LangGraph 的 StateGraph
- `graph_nodes/`：各个工作流节点实现（planner/edit/explore/execute/read/retrieve/reflection/end 等）
- `llm/llm.py`：LLM 初始化（ChatOpenAI）
- `state/`：Agent 状态定义与日志/工作区状态管理
- `utils/`：工具函数与日志 tee 等
- `runtime_env.template`：运行时环境配置模板（模型、Key、Sandbox 等）
- `user_workspace/`：用户工作区（默认配置指向其子目录）
- `.gitignore`

---

## 环境与配置

### 1) 安装依赖

本项目依赖 LangGraph / LangChain OpenAI（以及其他间接依赖）。建议使用虚拟环境：

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -U pip
# 按需安装：langgraph、langchain-openai 等
```

> 说明：仓库当前未提供 `requirements.txt` / `pyproject.toml`，你可以后续补充依赖清单以便一键安装。

### 2) 配置 runtime_env

将 `runtime_env.template` 复制为 `runtime_env.py`（或按你的加载方式命名为 `runtime_env.py`），并填写关键参数：

- `MODEL`
- `API_KEY`
- `BASE_URL`（如果你使用兼容 OpenAI 的自建网关/第三方网关）
- `WORKSPACE_PATH`（默认：`user_workspace/llm_train`）

Sandbox（Conda）相关参数也在该文件中提供：
- `SANDBOX_CONDA_ENABLED`
- `SANDBOX_ENV_NAME`
- `SANDBOX_PYTHON_VERSION`
- `SANDBOX_CREATE_IF_MISSING`
- `CONDA_EXE` / `CONDA_ROOT`
- `SANDBOX_LOG_DIR` / `SANDBOX_LOG_FILE`

---

## 运行方式

在完成 `runtime_env.py` 配置后，运行入口脚本：

```bash
python agent_graph.py
```

运行日志：
- 主输出日志会写入 `logs/`（启动时由 tee 逻辑创建）
- Sandbox 的执行输出可写入 `logs/sandbox-output.log`（取决于配置/实现）
