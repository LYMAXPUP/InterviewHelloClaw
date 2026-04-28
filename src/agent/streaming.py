"""流式事件类型和事件类

本模块定义流式响应的事件类型和事件数据结构。
由于 hello_agents 0.2.9 版本没有 streaming 模块，这里提供本地实现。
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


class StreamEventType(Enum):
    """流式事件类型"""
    AGENT_START = "agent_start"
    AGENT_FINISH = "agent_finish"
    STEP_START = "step_start"
    STEP_FINISH = "step_finish"
    LLM_CHUNK = "llm_chunk"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_FINISH = "tool_call_finish"
    ERROR = "error"
    MAX_ITERATIONS = "max_iterations"  # 达到最大迭代次数


@dataclass
class StreamEvent:
    """流式事件数据结构"""
    type: StreamEventType
    agent_name: str
    data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        event_type: StreamEventType,
        agent_name: str,
        **kwargs
    ) -> "StreamEvent":
        """创建流式事件的便捷方法

        Args:
            event_type: 事件类型
            agent_name: Agent 名称
            **kwargs: 事件数据

        Returns:
            StreamEvent 实例
        """
        return cls(
            type=event_type,
            agent_name=agent_name,
            data=kwargs
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于 JSON 序列化）

        Returns:
            包含 type, agent_name, data 的字典
        """
        return {
            "type": self.type.value,
            "agent_name": self.agent_name,
            "data": self.data
        }

    def __repr__(self) -> str:
        return f"StreamEvent(type={self.type.value}, agent={self.agent_name}, data={self.data})"