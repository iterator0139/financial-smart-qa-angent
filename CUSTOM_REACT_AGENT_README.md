# 自定义 ReAct Agent

## 概述

这是一个基于 LangGraph 构建的自定义 ReAct (Reasoning and Acting) Agent，相比框架原生的 `create_react_agent`，提供了更好的灵活性和控制能力。

## 主要特性

### 🎯 完全可控的推理流程
- **自定义状态管理**: 通过 `AgentState` 完全控制执行状态
- **步骤计数**: 精确跟踪推理步骤，可设置最大步骤限制
- **条件分支**: 灵活的条件边控制执行流程
- **错误处理**: 完善的错误捕获和处理机制

### 🛠️ 工具调用管理
- **工具映射**: 动态工具注册和管理
- **执行监控**: 详细的工具执行日志和性能统计
- **错误恢复**: 工具执行失败时的优雅处理

### 📊 详细的执行日志
- **推理过程**: 完整的 Thought-Action-Observation 记录
- **工具调用**: 详细的工具执行时间和结果
- **性能统计**: 执行摘要和性能分析

### 🔄 流式输出支持
- **实时输出**: 支持流式推理过程
- **状态同步**: 流式执行时的状态管理

## 架构设计

### 状态图结构

```
START → agent → should_continue → tools → agent → ... → END
```

- **agent节点**: 负责LLM推理和决策
- **tools节点**: 负责工具执行
- **should_continue**: 条件判断，决定下一步执行路径

### 状态定义

```python
class AgentState(TypedDict):
    messages: List[Dict[str, Any]]      # 消息历史
    current_step: int                   # 当前步骤
    max_steps: int                      # 最大步骤数
    scratchpad: str                     # 推理过程记录
    tool_results: List[Dict[str, Any]]  # 工具执行结果
    final_answer: Optional[str]         # 最终答案
    error: Optional[str]                # 错误信息
    is_finished: bool                   # 是否完成
```

## 使用方法

### 基本使用

```python
from src.planner.planner import create_default_custom_react_agent
from src.config.config_manager import ConfigManager

# 初始化配置
config = ConfigManager()
config.init(config_dir)

# 创建Agent
agent = create_default_custom_react_agent(
    model_name="qwen-turbo",
    config=config,
    max_steps=10
)

# 执行查询
result = agent.invoke("请帮我查询数据库信息")
print(f"最终答案: {result['final_answer']}")
```

### 高级配置

```python
# 自定义工具和prompt
custom_tools = [
    Tool(name="CustomTool", description="自定义工具", func=custom_function)
]

custom_prompt = """
自定义的ReAct prompt模板
{tools}
{input}
{agent_scratchpad}
"""

agent = create_default_custom_react_agent(
    model_name="qwen-turbo",
    custom_tools=custom_tools,
    custom_prompt=custom_prompt,
    max_steps=15,
    config=config
)
```

### 流式执行

```python
# 流式推理
for chunk in agent.stream("请帮我查询数据库信息"):
    print(f"流式输出: {chunk}")
```

### 动态工具管理

```python
# 添加工具
agent.add_tool(new_tool)

# 移除工具
agent.remove_tool("tool_name")

# 获取所有工具
tools = agent.get_tools()
```

## 与原生 ReAct Agent 的对比

| 特性 | 原生 create_react_agent | 自定义 ReAct Agent |
|------|------------------------|-------------------|
| 推理流程控制 | ❌ 黑箱，无法控制 | ✅ 完全可控 |
| 状态管理 | ❌ 框架内部管理 | ✅ 自定义状态 |
| 步骤限制 | ❌ 无限制 | ✅ 可设置最大步骤 |
| 错误处理 | ❌ 基础错误处理 | ✅ 完善的错误处理 |
| 执行日志 | ❌ 有限日志 | ✅ 详细执行日志 |
| 工具管理 | ❌ 静态工具列表 | ✅ 动态工具管理 |
| 性能监控 | ❌ 无 | ✅ 完整的性能统计 |
| 自定义prompt | ✅ 支持 | ✅ 支持 |
| 流式输出 | ✅ 支持 | ✅ 支持 |

## 执行流程详解

### 1. 初始化阶段
```python
# 创建状态图
workflow = StateGraph(AgentState)
workflow.add_node("agent", self._agent_node)
workflow.add_node("tools", self._tools_node)
workflow.set_entry_point("agent")
```

### 2. 推理阶段 (agent节点)
```python
def _agent_node(self, state: AgentState) -> AgentState:
    # 1. 增加步骤计数
    state["current_step"] += 1
    
    # 2. 构建prompt
    full_prompt = self._build_prompt(state)
    
    # 3. 调用LLM
    response = self.llm.invoke(full_prompt)
    
    # 4. 解析响应
    parsed_response = self._parse_agent_response(response)
    
    # 5. 更新状态
    if parsed_response["action_type"] == "finish":
        state["final_answer"] = parsed_response["action_input"]
        state["is_finished"] = True
    else:
        state["next_tool"] = {
            "name": parsed_response["action_input"],
            "input": parsed_response.get("tool_input", "")
        }
    
    return state
```

### 3. 工具执行阶段 (tools节点)
```python
def _tools_node(self, state: AgentState) -> AgentState:
    # 1. 获取工具信息
    tool_info = state.get("next_tool")
    
    # 2. 查找并执行工具
    tool = self.tool_map[tool_name]
    tool_result = tool.func(tool_input)
    
    # 3. 记录结果
    state["tool_results"].append({
        "tool": tool_name,
        "input": tool_input,
        "output": tool_result,
        "step": state["current_step"]
    })
    
    # 4. 更新scratchpad
    state["scratchpad"] += f"\nObservation: {tool_result}"
    
    return state
```

### 4. 条件判断阶段
```python
def _should_continue(self, state: AgentState) -> str:
    # 检查是否完成
    if state.get("is_finished", False):
        return "end"
    
    # 检查步骤数限制
    if state["current_step"] >= state["max_steps"]:
        state["error"] = f"Maximum steps ({state['max_steps']}) reached"
        state["is_finished"] = True
        return "end"
    
    # 检查是否有工具需要执行
    if "next_tool" in state:
        return "tools"
    
    # 继续推理
    return "end"
```

## 性能优化建议

### 1. 步骤数优化
- 根据任务复杂度设置合适的 `max_steps`
- 监控平均执行步骤数，优化prompt

### 2. 工具调用优化
- 优先使用高效的工具
- 避免重复的工具调用
- 合理设计工具接口

### 3. 错误处理优化
- 设置合理的重试机制
- 提供有意义的错误信息
- 实现优雅的降级策略

## 扩展开发

### 添加新的节点类型
```python
def custom_node(self, state: AgentState) -> AgentState:
    # 自定义节点逻辑
    return state

# 在图中添加节点
workflow.add_node("custom", self.custom_node)
```

### 自定义条件判断
```python
def custom_condition(self, state: AgentState) -> str:
    # 自定义条件逻辑
    return "next_node"
```

### 扩展状态类型
```python
class ExtendedAgentState(AgentState):
    custom_field: str
    additional_data: Dict[str, Any]
```

## 故障排除

### 常见问题

1. **步骤数超限**
   - 检查 `max_steps` 设置
   - 优化prompt减少推理步骤
   - 检查是否有无限循环

2. **工具执行失败**
   - 检查工具是否正确注册
   - 验证工具输入格式
   - 查看详细错误日志

3. **推理结果不准确**
   - 检查prompt模板
   - 验证工具输出格式
   - 调整模型参数

### 调试技巧

1. **启用详细日志**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **检查执行状态**
   ```python
   result = agent.invoke(query)
   print(f"推理过程: {result['scratchpad']}")
   print(f"工具调用: {result['tool_results']}")
   ```

3. **监控性能**
   ```python
   summary = agent.get_execution_summary()
   print(f"工具执行摘要: {summary}")
   ```

## 总结

自定义 ReAct Agent 提供了比原生实现更好的控制能力和灵活性，特别适合需要精确控制推理流程的复杂应用场景。通过合理的配置和优化，可以实现高效、可靠的智能问答系统。 