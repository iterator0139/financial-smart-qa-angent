import sys
from pathlib import Path
import logging
from typing import TypedDict, List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
import hashlib
from abc import ABC, abstractmethod

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from src.utils.logger import get_logger


@dataclass
class Memory:
    """记忆单元数据结构"""
    id: str
    content: str
    memory_type: str  # 'action', 'result', 'context', 'strategy'
    timestamp: datetime
    relevance_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'content': self.content,
            'memory_type': self.memory_type,
            'timestamp': self.timestamp.isoformat(),
            'relevance_score': self.relevance_score,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Memory':
        """从字典创建Memory对象"""
        return cls(
            id=data['id'],
            content=data['content'],
            memory_type=data['memory_type'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            relevance_score=data.get('relevance_score', 0.0),
            metadata=data.get('metadata', {})
        )


class MemoryStore(ABC):
    """记忆存储抽象基类"""
    
    @abstractmethod
    def store(self, memory: Memory) -> bool:
        """存储记忆"""
        pass
    
    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5, memory_type: Optional[str] = None) -> List[Memory]:
        """检索相关记忆"""
        pass
    
    @abstractmethod
    def get_recent_memories(self, limit: int = 10, memory_type: Optional[str] = None) -> List[Memory]:
        """获取最近的记忆"""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """清除所有记忆"""
        pass


class InMemoryStore(MemoryStore):
    """内存中的记忆存储实现"""
    
    def __init__(self):
        self.memories: List[Memory] = []
        self.logger = get_logger(self.__class__.__name__)
    
    def store(self, memory: Memory) -> bool:
        """存储记忆到内存"""
        try:
            self.memories.append(memory)
            self.logger.debug(f"Stored memory: {memory.id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to store memory: {e}")
            return False
    
    def retrieve(self, query: str, top_k: int = 5, memory_type: Optional[str] = None) -> List[Memory]:
        """基于简单文本匹配检索相关记忆"""
        try:
            # 过滤记忆类型
            filtered_memories = self.memories
            if memory_type:
                filtered_memories = [m for m in self.memories if m.memory_type == memory_type]
            
            # 简单的文本相似度计算（基于关键词匹配）
            query_lower = query.lower()
            relevant_memories = []
            
            for memory in filtered_memories:
                content_lower = memory.content.lower()
                # 计算简单的相关性分数
                common_words = set(query_lower.split()) & set(content_lower.split())
                relevance_score = len(common_words) / max(len(query_lower.split()), 1)
                
                if relevance_score > 0:
                    memory.relevance_score = relevance_score
                    relevant_memories.append(memory)
            
            # 按相关性分数排序并返回top_k
            relevant_memories.sort(key=lambda x: x.relevance_score, reverse=True)
            return relevant_memories[:top_k]
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve memories: {e}")
            return []
    
    def get_recent_memories(self, limit: int = 10, memory_type: Optional[str] = None) -> List[Memory]:
        """获取最近的记忆"""
        try:
            filtered_memories = self.memories
            if memory_type:
                filtered_memories = [m for m in self.memories if m.memory_type == memory_type]
            
            # 按时间戳排序并返回最近的记忆
            sorted_memories = sorted(filtered_memories, key=lambda x: x.timestamp, reverse=True)
            return sorted_memories[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to get recent memories: {e}")
            return []
    
    def clear(self) -> bool:
        """清除所有记忆"""
        try:
            self.memories.clear()
            self.logger.info("All memories cleared")
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear memories: {e}")
            return False


class PlannerState(TypedDict):
    """Planner状态数据结构"""
    query: str
    current_step: int
    plan: List[Dict[str, Any]]
    executed_actions: List[Dict[str, Any]]
    context: Dict[str, Any]
    error: Optional[str]
    final_result: Optional[str]


@dataclass
class PlanStep:
    """规划步骤数据结构"""
    step_id: int
    action: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, executing, completed, failed
    result: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class PlannerAgent:
    """带记忆模块的规划代理"""
    
    def __init__(self, memory_store: Optional[MemoryStore] = None):
        self.memory_store = memory_store or InMemoryStore()
        self.logger = get_logger(self.__class__.__name__)
        self.available_actions = self._initialize_actions()
    
    def _initialize_actions(self) -> Dict[str, str]:
        """初始化可用的行动选项"""
        return {
            "query_understanding": "理解和解析用户查询",
            "information_retrieval": "检索相关信息",
            "sql_generation": "生成SQL查询",
            "data_analysis": "分析数据",
            "answer_generation": "生成最终答案",
            "validation": "验证结果",
            "error_handling": "处理错误"
        }
    
    def _generate_memory_id(self, content: str, memory_type: str) -> str:
        """生成记忆ID"""
        timestamp = datetime.now().isoformat()
        text = f"{content}_{memory_type}_{timestamp}"
        return hashlib.md5(text.encode()).hexdigest()[:12]
    
    def store_memory(self, content: str, memory_type: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """存储记忆"""
        memory_id = self._generate_memory_id(content, memory_type)
        memory = Memory(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        success = self.memory_store.store(memory)
        if success:
            self.logger.info(f"Memory stored: {memory_type} - {content[:50]}...")
        else:
            self.logger.error(f"Failed to store memory: {memory_type}")
        
        return memory_id
    
    def retrieve_relevant_memories(self, query: str, top_k: int = 5, memory_type: Optional[str] = None) -> List[Memory]:
        """检索相关记忆"""
        memories = self.memory_store.retrieve(query, top_k, memory_type)
        self.logger.debug(f"Retrieved {len(memories)} relevant memories for query: {query[:50]}...")
        return memories
    
    def create_plan(self, query: str, context: Optional[Dict[str, Any]] = None) -> List[PlanStep]:
        """基于查询和记忆创建执行计划"""
        # 检索相关的历史策略记忆
        strategy_memories = self.retrieve_relevant_memories(query, top_k=3, memory_type="strategy")
        context_memories = self.retrieve_relevant_memories(query, top_k=3, memory_type="context")
        
        # 记录规划开始
        self.store_memory(
            f"开始为查询创建计划: {query}",
            "action",
            {"context": context or {}}
        )
        
        # 基于查询类型和历史经验生成计划
        plan = self._generate_plan_steps(query, strategy_memories, context_memories, context)
        
        # 存储规划策略
        plan_summary = f"为查询'{query[:50]}...'生成了{len(plan)}步计划"
        self.store_memory(plan_summary, "strategy", {"plan_steps": len(plan)})
        
        return plan
    
    def _generate_plan_steps(self, query: str, strategy_memories: List[Memory], 
                           context_memories: List[Memory], context: Optional[Dict[str, Any]]) -> List[PlanStep]:
        """生成具体的规划步骤"""
        steps = []
        
        # 基本的金融问答流程
        base_steps = [
            ("query_understanding", "解析用户查询，提取关键信息"),
            ("information_retrieval", "检索相关的金融数据和信息"),
            ("data_analysis", "分析数据，执行必要的计算"),
            ("answer_generation", "基于分析结果生成答案"),
            ("validation", "验证答案的准确性和完整性")
        ]
        
        # 根据历史记忆调整计划
        if strategy_memories:
            self.logger.info(f"Found {len(strategy_memories)} relevant strategy memories")
            # 这里可以根据历史成功策略调整步骤
        
        # 如果查询包含SQL相关需求，添加SQL生成步骤
        if any(keyword in query.lower() for keyword in ['查询', '数据', '股票', '价格', '日期']):
            base_steps.insert(2, ("sql_generation", "生成SQL查询语句"))
        
        # 创建PlanStep对象
        for i, (action, description) in enumerate(base_steps):
            step = PlanStep(
                step_id=i + 1,
                action=action,
                description=description,
                parameters=self._get_step_parameters(action, query, context)
            )
            steps.append(step)
        
        return steps
    
    def _get_step_parameters(self, action: str, query: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """为特定行动生成参数"""
        base_params = {"query": query}
        
        if context:
            base_params.update(context)
        
        # 根据行动类型添加特定参数
        if action == "sql_generation":
            base_params.update({
                "database_schema": "financial_data",
                "table_hints": ["stock_data", "company_info", "market_data"]
            })
        elif action == "information_retrieval":
            base_params.update({
                "search_domains": ["financial", "market", "company"],
                "max_results": 10
            })
        
        return base_params
    
    def execute_plan(self, plan: List[PlanStep], state: PlannerState) -> PlannerState:
        """执行规划"""
        self.logger.info(f"开始执行包含{len(plan)}个步骤的计划")
        
        executed_actions = []
        current_step = 1
        
        for step in plan:
            try:
                self.logger.info(f"执行步骤 {step.step_id}: {step.description}")
                
                # 记录步骤开始
                step.start_time = datetime.now()
                step.status = "executing"
                
                # 存储执行记忆
                self.store_memory(
                    f"执行步骤 {step.step_id}: {step.action} - {step.description}",
                    "action",
                    {"step_id": step.step_id, "action": step.action}
                )
                
                # 模拟步骤执行（实际实现中这里会调用具体的执行逻辑）
                result = self._execute_step(step, state)
                
                # 更新步骤状态
                step.end_time = datetime.now()
                step.result = result
                step.status = "completed"
                
                # 存储执行结果
                self.store_memory(
                    f"步骤 {step.step_id} 执行完成: {result}",
                    "result",
                    {"step_id": step.step_id, "action": step.action, "execution_time": 
                     (step.end_time - step.start_time).total_seconds()}
                )
                
                executed_actions.append({
                    "step_id": step.step_id,
                    "action": step.action,
                    "status": step.status,
                    "result": result
                })
                
                current_step += 1
                
            except Exception as e:
                self.logger.error(f"步骤 {step.step_id} 执行失败: {e}")
                step.status = "failed"
                step.end_time = datetime.now()
                
                # 存储错误记忆
                error_msg = f"步骤 {step.step_id} 执行失败: {str(e)}"
                self.store_memory(error_msg, "result", {"step_id": step.step_id, "error": True})
                
                # 更新状态
                state["error"] = error_msg
                break
        
        # 更新最终状态
        state.update({
            "current_step": current_step,
            "executed_actions": executed_actions,
            "plan": [step.__dict__ for step in plan]
        })
        
        if not state.get("error"):
            final_result = self._generate_final_result(executed_actions, state)
            state["final_result"] = final_result
            
            # 存储最终结果记忆
            self.store_memory(
                f"计划执行完成，最终结果: {final_result}",
                "result",
                {"query": state["query"], "steps_completed": len(executed_actions)}
            )
        
        return state
    
    def _execute_step(self, step: PlanStep, state: PlannerState) -> str:
        """执行单个步骤（模拟实现）"""
        # 这里是模拟实现，实际项目中需要调用对应的模块
        action_results = {
            "query_understanding": f"解析查询: {state['query'][:50]}...",
            "information_retrieval": "检索到相关金融数据",
            "sql_generation": "生成SQL查询: SELECT * FROM stock_data WHERE...",
            "data_analysis": "完成数据分析，发现关键指标",
            "answer_generation": "基于分析结果生成详细答案",
            "validation": "验证答案准确性通过"
        }
        
        return action_results.get(step.action, f"执行了 {step.action}")
    
    def _generate_final_result(self, executed_actions: List[Dict[str, Any]], state: PlannerState) -> str:
        """基于执行的行动生成最终结果"""
        if not executed_actions:
            return "未能生成有效结果"
        
        # 提取所有步骤的结果
        results = [action.get("result", "") for action in executed_actions]
        
        # 组合生成最终答案
        final_result = f"基于{len(executed_actions)}个步骤的执行结果，为查询'{state['query']}'生成的答案：\n"
        final_result += "\n".join([f"- {result}" for result in results if result])
        
        return final_result
    
    def plan_and_execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> PlannerState:
        """完整的规划和执行流程"""
        self.logger.info(f"开始处理查询: {query}")
        
        # 初始化状态
        state: PlannerState = {
            "query": query,
            "current_step": 0,
            "plan": [],
            "executed_actions": [],
            "context": context or {},
            "error": None,
            "final_result": None
        }
        
        try:
            # 创建计划
            plan = self.create_plan(query, context)
            self.logger.info(f"创建了包含{len(plan)}个步骤的执行计划")
            
            # 执行计划
            final_state = self.execute_plan(plan, state)
            
            return final_state
            
        except Exception as e:
            error_msg = f"规划和执行过程中发生错误: {str(e)}"
            self.logger.error(error_msg)
            state["error"] = error_msg
            
            # 存储错误记忆
            self.store_memory(error_msg, "result", {"query": query, "fatal_error": True})
            
            return state
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """获取记忆库摘要信息"""
        recent_memories = self.memory_store.get_recent_memories(limit=20)
        
        # 按类型统计记忆
        memory_types = {}
        for memory in recent_memories:
            memory_types[memory.memory_type] = memory_types.get(memory.memory_type, 0) + 1
        
        return {
            "total_recent_memories": len(recent_memories),
            "memory_types": memory_types,
            "latest_memory": recent_memories[0].to_dict() if recent_memories else None
        }
