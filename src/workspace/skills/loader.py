"""Skill 加载器 - 解析和管理 Skills"""

import os
import re
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class Skill:
    """Skill 数据结构"""
    name: str
    description: str
    content: str
    path: str
    scripts_dir: Optional[str] = None

    def to_summary(self) -> str:
        """将 Skill 转换为摘要格式（用于渐进式披露的初始加载）

        只包含 name、description 和 location，不包含完整内容。
        """
        path_info = f"路径: {self.path}"
        if self.scripts_dir:
            path_info += f"\n脚本目录: {self.scripts_dir}"

        return f"""### {self.name}
{self.description}
{path_info}"""

    def to_prompt(self) -> str:
        """将 Skill 转换为完整系统提示词格式

        包含所有内容，用于 Agent 需要执行该 Skill 时。
        """
        # 构建路径信息
        path_info = f"路径: {self.path}"
        if self.scripts_dir:
            path_info += f"\n脚本目录: {self.scripts_dir}"

        return f"""## Skill: {self.name}

{self.description}

{path_info}

{self.content}
"""


class SkillLoader:
    """Skill 加载器

    负责扫描、解析和加载 skills 目录下的所有 SKILL.md 文件。

    Skills 目录结构：
    skills/
    ├── skill-name-1/
    │   ├── SKILL.md          # Skill 定义文件（必须）
    │   └── scripts/          # Skill 相关脚本（可选）
    │       └── script.py
    └── skill-name-2/
    │   ├── SKILL.md
    │   └── scripts/
    """

    # Skill 定义文件的固定名称
    SKILL_FILE = "SKILL.md"

    def __init__(self, skills_path: str, workspace_path: str = None):
        """初始化 SkillLoader

        Args:
            skills_path: Skills 目录路径
            workspace_path: 工作空间路径（用于生成相对于工作空间的路径）
        """
        self.skills_path = os.path.expanduser(skills_path)
        self.workspace_path = os.path.expanduser(workspace_path) if workspace_path else None
        self._skills: Dict[str, Skill] = {}
        self._loaded = False

    def load_all(self) -> List[Skill]:
        """加载所有 Skills

        Returns:
            加载的 Skill 列表
        """
        if not os.path.exists(self.skills_path):
            self._loaded = True
            return []

        # 清除已有缓存，确保重新加载
        self._skills.clear()

        skills = []
        for entry in os.listdir(self.skills_path):
            entry_path = os.path.join(self.skills_path, entry)
            if os.path.isdir(entry_path):
                skill = self._load_skill(entry_path)
                if skill:
                    skills.append(skill)
                    self._skills[skill.name] = skill

        self._loaded = True
        return skills

    def _get_relative_path(self, abs_path: str) -> str:
        """获取相对于工作空间的路径

        如果 workspace_path 已设置，返回相对于工作空间的路径。
        否则返回原始路径。

        Args:
            abs_path: 绝对路径

        Returns:
            相对路径或原始路径
        """
        if not self.workspace_path:
            return abs_path

        # 将两者都转为绝对路径进行比较
        abs_workspace = os.path.abspath(self.workspace_path)
        abs_target = os.path.abspath(abs_path)

        try:
            # 计算相对路径
            rel_path = os.path.relpath(abs_target, abs_workspace)
            return rel_path
        except ValueError:
            # 在 Windows 上，如果路径在不同的驱动器上，relpath 会失败
            return abs_path

    def _load_skill(self, skill_dir: str) -> Optional[Skill]:
        """加载单个 Skill

        Args:
            skill_dir: Skill 目录路径

        Returns:
            Skill 对象，如果加载失败返回 None
        """
        skill_file = os.path.join(skill_dir, self.SKILL_FILE)
        if not os.path.exists(skill_file):
            return None

        try:
            with open(skill_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 解析 YAML frontmatter
            metadata, body = self._parse_frontmatter(content)

            if not metadata:
                print(f"⚠️ Skill 文件缺少 frontmatter: {skill_file}")
                return None

            name = metadata.get("name", "")
            description = metadata.get("description", "")

            if not name:
                print(f"⚠️ Skill 文件缺少 name 字段: {skill_file}")
                return None

            # 检查是否有 scripts 目录
            scripts_dir = None
            scripts_path = os.path.join(skill_dir, "scripts")
            if os.path.exists(scripts_path) and os.path.isdir(scripts_path):
                scripts_dir = scripts_path

            # 计算相对于工作空间的路径（用于 Agent 执行命令）
            rel_skill_dir = self._get_relative_path(skill_dir)
            rel_scripts_dir = self._get_relative_path(scripts_dir) if scripts_dir else None

            return Skill(
                name=name,
                description=description,
                content=body,
                path=rel_skill_dir,  # 使用相对路径
                scripts_dir=rel_scripts_dir,  # 使用相对路径
            )

        except Exception as e:
            print(f"❌ 加载 Skill 失败: {skill_file} - {e}")
            return None

    def _parse_frontmatter(self, content: str) -> tuple:
        """解析 YAML frontmatter

        Args:
            content: 文件内容

        Returns:
            (metadata_dict, body_content) 元组
        """
        # 匹配 YAML frontmatter: --- 之间的内容
        pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            return None, content

        try:
            metadata = yaml.safe_load(match.group(1))
            body = match.group(2).strip()
            return metadata, body
        except yaml.YAMLError:
            return None, content

    def get_skill(self, name: str) -> Optional[Skill]:
        """获取指定名称的 Skill

        Args:
            name: Skill 名称

        Returns:
            Skill 对象，如果不存在返回 None
        """
        if not self._loaded:
            self.load_all()
        return self._skills.get(name)

    def get_all_skills(self) -> Dict[str, Skill]:
        """获取所有 Skills

        Returns:
            Skill 名称到 Skill 对象的映射
        """
        if not self._loaded:
            self.load_all()
        return self._skills

    def list_skill_names(self) -> List[str]:
        """列出所有 Skill 名称

        Returns:
            Skill 名称列表
        """
        if not self._loaded:
            self.load_all()
        return list(self._skills.keys())

    def build_skills_prompt(self, full_content: bool = False, force_reload: bool = True) -> str:
        """构建所有 Skills 的系统提示词

        将所有 Skill 定义整合为一个提示词段落，
        用于注入到 Agent 的系统提示词中。

        Args:
            full_content: 是否加载完整内容（默认 False，采用渐进式披露）
            force_reload: 是否强制重新加载（默认 True，确保每次对话都获取最新内容）

        Returns:
            Skills 提示词字符串
        """
        # 强制重新加载，确保每次对话都能获取最新的 Skill 内容
        if force_reload or not self._loaded:
            self.load_all()

        if not self._skills:
            return ""

        if full_content:
            # 传统模式：加载所有 Skill 的完整内容
            parts = ["\n## Available Skills\n"]
            parts.append("以下 Skills 可供你使用。当用户请求匹配 Skill 描述时，请调用相应的命令。\n")

            for skill in self._skills.values():
                parts.append(skill.to_prompt())
                parts.append("\n---\n")

            return "\n".join(parts)
        else:
            # 渐进式披露模式：只加载摘要信息
            parts = ["\n## Available Skills\n"]
            parts.append("以下 Skills 可供你使用。每个 Skill 只显示摘要信息。\n")
            parts.append("当用户请求匹配某个 Skill 描述时，请先使用 `load_skill` 工具加载该 Skill 的完整内容，然后再执行相应操作。\n")

            for skill in self._skills.values():
                parts.append(skill.to_summary())
                parts.append("")

            return "\n".join(parts)

    def get_full_skill_prompt(self, name: str) -> Optional[str]:
        """获取单个 Skill 的完整提示词

        用于渐进式披露，当 Agent 需要使用某个 Skill 时调用。

        Args:
            name: Skill 名称

        Returns:
            Skill 完整提示词，如果不存在返回 None
        """
        # 每次都重新加载，确保获取最新内容
        self.load_all()

        skill = self._skills.get(name)
        if not skill:
            return None

        return skill.to_prompt()

    def reload(self) -> List[Skill]:
        """重新加载所有 Skills

        Returns:
            加载的 Skill 列表
        """
        self._skills.clear()
        self._loaded = False
        return self.load_all()


class SkillManager:
    """Skill 管理器

    提供更高层次的 Skill 管理功能，与 WorkspaceManager 集成。
    """

    def __init__(self, workspace_path: str):
        """初始化 SkillManager

        Args:
            workspace_path: 工作空间路径
        """
        self.workspace_path = os.path.expanduser(workspace_path)
        self.skills_path = os.path.join(self.workspace_path, "skills")
        # 传入 workspace_path，用于生成相对路径
        self.loader = SkillLoader(self.skills_path, self.workspace_path)

    def ensure_skills_dir_exists(self):
        """确保 skills 目录存在"""
        if not os.path.exists(self.skills_path):
            os.makedirs(self.skills_path, exist_ok=True)

    def load_skills(self) -> List[Skill]:
        """加载所有 Skills

        Returns:
            Skill 列表
        """
        self.ensure_skills_dir_exists()
        return self.loader.load_all()

    def get_skills_prompt(self, full_content: bool = False, force_reload: bool = True) -> str:
        """获取 Skills 系统提示词

        Args:
            full_content: 是否加载完整内容（默认 False，采用渐进式披露）
            force_reload: 是否强制重新加载（默认 True，确保获取最新内容）

        Returns:
            Skills 提示词字符串
        """
        self.ensure_skills_dir_exists()
        return self.loader.build_skills_prompt(full_content=full_content, force_reload=force_reload)

    def get_full_skill_prompt(self, name: str) -> Optional[str]:
        """获取单个 Skill 的完整提示词

        用于渐进式披露，当 Agent 需要使用某个 Skill 时调用。

        Args:
            name: Skill 名称

        Returns:
            Skill 完整提示词，如果不存在返回 None
        """
        self.ensure_skills_dir_exists()
        return self.loader.get_full_skill_prompt(name)

    def list_skills(self) -> List[Dict[str, Any]]:
        """列出所有 Skills 信息

        Returns:
            Skill 信息列表
        """
        self.load_skills()
        skills_info = []
        for skill in self.loader.get_all_skills().values():
            skills_info.append({
                "name": skill.name,
                "description": skill.description,
                "path": skill.path,
                "has_scripts": skill.scripts_dir is not None,
            })
        return skills_info

    def add_skill_from_dir(self, source_dir: str) -> bool:
        """从外部目录添加 Skill

        将外部 Skill 目录复制到 workspace/skills/ 下。

        Args:
            source_dir: 源 Skill 目录路径

        Returns:
            是否成功添加
        """
        if not os.path.exists(source_dir):
            print(f"❌ 源目录不存在: {source_dir}")
            return False

        # 检查是否有 SKILL.md
        skill_file = os.path.join(source_dir, self.loader.SKILL_FILE)
        if not os.path.exists(skill_file):
            print(f"❌ 目录中没有 SKILL.md: {source_dir}")
            return False

        # 读取 Skill 名称
        try:
            with open(skill_file, "r", encoding="utf-8") as f:
                content = f.read()
            metadata, _ = self.loader._parse_frontmatter(content)
            if not metadata or not metadata.get("name"):
                print(f"❌ SKILL.md 缺少有效的 name 字段")
                return False
            skill_name = metadata.get("name")
        except Exception as e:
            print(f"❌ 解析 SKILL.md 失败: {e}")
            return False

        # 目标目录
        self.ensure_skills_dir_exists()
        target_dir_name = os.path.basename(source_dir)
        target_dir = os.path.join(self.skills_path, target_dir_name)

        if os.path.exists(target_dir):
            print(f"⚠️ Skill 目录已存在: {target_dir}")
            return False

        # 复制目录
        import shutil
        try:
            shutil.copytree(source_dir, target_dir)
            print(f"✅ Skill 已添加: {skill_name} -> {target_dir}")
            # 重新加载
            self.loader.reload()
            return True
        except Exception as e:
            print(f"❌ 复制 Skill 目录失败: {e}")
            return False

    def reload_skills(self) -> List[Skill]:
        """重新加载所有 Skills

        Returns:
            Skill 列表
        """
        return self.loader.reload()