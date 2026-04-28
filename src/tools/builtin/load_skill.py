"""Skill 加载工具 - 用于渐进式披露加载完整 Skill 内容"""

from typing import List, Dict, Any, Optional

from hello_agents.tools import Tool, ToolParameter, ToolResponse


class LoadSkillTool(Tool):
    """Skill 加载工具

    用于渐进式披露：当 Agent 需要使用某个 Skill 时，
    使用此工具加载该 Skill 的完整内容（包括详细指令和脚本信息）。
    """

    def __init__(self, skill_manager):
        """初始化 Skill 加载工具

        Args:
            skill_manager: SkillManager 实例
        """
        super().__init__(
            name="load_skill",
            description="加载指定 Skill 的完整内容。当你判断用户请求匹配某个 Skill 的描述时，请先使用此工具加载该 Skill 的详细指令，然后再执行相应操作。",
            expandable=False
        )
        self.skill_manager = skill_manager

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        """执行 Skill 加载"""
        skill_name = parameters.get("skill_name", "")
        if not skill_name:
            return ToolResponse.error(
                code="INVALID_INPUT",
                message="请提供 Skill 名称"
            )

        # 获取完整 Skill 提示词
        full_prompt = self.skill_manager.get_full_skill_prompt(skill_name)

        if not full_prompt:
            # 列出可用的 Skill 名称
            available_skills = self.skill_manager.list_skills()
            skill_names = [s["name"] for s in available_skills]
            return ToolResponse.error(
                code="SKILL_NOT_FOUND",
                message=f"Skill '{skill_name}' 不存在。可用的 Skill: {', '.join(skill_names)}"
            )

        return ToolResponse.success(
            text=f"已加载 Skill '{skill_name}' 的完整内容:\n\n{full_prompt}",
            data={"skill_name": skill_name, "full_prompt": full_prompt}
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="skill_name",
                type="string",
                description="要加载的 Skill 名称（例如: tavily-search, email-process）",
                required=True
            )
        ]