"""时间工具 - 获取当前时间"""

from typing import List, Dict, Any
from datetime import datetime

from hello_agents.tools import Tool, ToolParameter, ToolResponse, tool_action


class TimeTool(Tool):
    """时间获取工具

    获取当前系统时间
    """

    def __init__(self):
        """初始化时间工具"""
        super().__init__(
            name="time",
            description="获取当前系统时间",
            expandable=False
        )

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        """默认执行：获取当前时间"""
        return self._get_current_time()

    def get_parameters(self) -> List[ToolParameter]:
        return []

    def _get_current_time(self) -> ToolResponse:
        """获取当前时间"""
        now = datetime.now()
        formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")

        return ToolResponse.success(
            text=f"当前时间: {formatted_time}",
            data={
                "datetime": formatted_time,
                "year": now.year,
                "month": now.month,
                "day": now.day,
                "hour": now.hour,
                "minute": now.minute,
                "second": now.second,
                "weekday": now.strftime("%A"),
                "weekday_cn": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()],
            }
        )

    @tool_action("get_time", "获取当前时间")
    def _get_time(self) -> str:
        """获取当前时间

        Returns:
            当前时间的格式化字符串
        """
        now = datetime.now()
        weekday_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()]
        return f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')} ({weekday_cn})"