"""Skills API 路由"""

import os
import shutil
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from ..workspace.skills import SkillManager

router = APIRouter(prefix="/skills", tags=["skills"])


class SkillInfo(BaseModel):
    """Skill 信息模型"""
    name: str
    description: str
    path: str
    has_scripts: bool


class SkillContent(BaseModel):
    """Skill 内容模型"""
    name: str
    path: str
    content: str
    has_scripts: bool


class SkillUpdateRequest(BaseModel):
    """Skill 更新请求"""
    content: str


class AddSkillRequest(BaseModel):
    """添加 Skill 请求"""
    source_dir: str


class CreateSkillRequest(BaseModel):
    """创建新 Skill 请求"""
    name: str
    description: str = ""


class SkillListResponse(BaseModel):
    """Skill 列表响应"""
    skills: List[SkillInfo]
    total: int


# 全局 SkillManager（由 main.py 初始化）
_skill_manager: Optional[SkillManager] = None


def get_skill_manager() -> SkillManager:
    """获取 SkillManager 实例"""
    if _skill_manager is None:
        raise HTTPException(status_code=500, detail="SkillManager 未初始化")
    return _skill_manager


def init_skill_api(skill_manager: SkillManager):
    """初始化 Skill API

    Args:
        skill_manager: SkillManager 实例
    """
    global _skill_manager
    _skill_manager = skill_manager


@router.get("/list", response_model=SkillListResponse)
async def list_skills():
    """列出所有 Skills"""
    manager = get_skill_manager()
    skills_info = manager.list_skills()

    return SkillListResponse(
        skills=[SkillInfo(**s) for s in skills_info],
        total=len(skills_info)
    )


@router.get("/{skill_name}", response_model=SkillContent)
async def get_skill_content(skill_name: str):
    """获取单个 Skill 的完整内容（用于编辑）"""
    manager = get_skill_manager()
    skill = manager.loader.get_skill(skill_name)

    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' 不存在")

    # skill.path 是相对于 workspace 的路径，需要转换为绝对路径
    skill_dir = os.path.join(manager.workspace_path, skill.path)
    skill_file = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(skill_file):
        raise HTTPException(status_code=404, detail=f"Skill 文件不存在: {skill_file}")

    with open(skill_file, "r", encoding="utf-8") as f:
        content = f.read()

    return SkillContent(
        name=skill.name,
        path=skill.path,
        content=content,
        has_scripts=skill.scripts_dir is not None
    )


@router.put("/{skill_name}")
async def update_skill_content(skill_name: str, request: SkillUpdateRequest):
    """更新 Skill 内容"""
    manager = get_skill_manager()
    skill = manager.loader.get_skill(skill_name)

    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' 不存在")

    # skill.path 是相对于 workspace 的路径，需要转换为绝对路径
    skill_dir = os.path.join(manager.workspace_path, skill.path)
    skill_file = os.path.join(skill_dir, "SKILL.md")

    # 写入新内容
    with open(skill_file, "w", encoding="utf-8") as f:
        f.write(request.content)

    return {"name": skill_name, "status": "updated", "message": "Skill 已更新"}


@router.get("/prompt")
async def get_skills_prompt(full_content: bool = False):
    """获取 Skills 系统提示词

    Args:
        full_content: 是否加载完整内容（默认 False，采用渐进式披露）
    """
    manager = get_skill_manager()
    prompt = manager.get_skills_prompt(full_content=full_content)

    return {"prompt": prompt, "has_skills": bool(prompt)}


@router.get("/prompt/{skill_name}")
async def get_single_skill_prompt(skill_name: str):
    """获取单个 Skill 的完整提示词

    用于渐进式披露，当需要使用某个 Skill 时调用。
    """
    manager = get_skill_manager()
    prompt = manager.get_full_skill_prompt(skill_name)

    if not prompt:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' 不存在")

    return {"skill_name": skill_name, "prompt": prompt}


@router.post("/add")
async def add_skill(request: AddSkillRequest):
    """从外部目录添加 Skill"""
    manager = get_skill_manager()
    success = manager.add_skill_from_dir(request.source_dir)

    if not success:
        raise HTTPException(status_code=400, detail="添加 Skill 失败")

    return {"message": "Skill 已添加", "source_dir": request.source_dir}


@router.post("/create")
async def create_skill(request: CreateSkillRequest):
    """创建新的 Skill"""
    import re

    manager = get_skill_manager()

    # 验证名称格式（只允许字母、数字、下划线、中划线）
    skill_name = request.name.strip()
    if not skill_name:
        raise HTTPException(status_code=400, detail="Skill 名称不能为空")

    if not re.match(r'^[a-zA-Z0-9_-]+$', skill_name):
        raise HTTPException(status_code=400, detail="Skill 名称只能包含字母、数字、下划线和横线")

    # 检查是否已存在
    existing_skill = manager.loader.get_skill(skill_name)
    if existing_skill:
        raise HTTPException(status_code=400, detail=f"Skill '{skill_name}' 已存在")

    # 创建 Skill 目录
    skill_dir = os.path.join(manager.loader.skills_path, skill_name)
    os.makedirs(skill_dir, exist_ok=True)

    # 创建 SKILL.md 文件
    skill_file = os.path.join(skill_dir, "SKILL.md")
    default_content = f"""---
name: {skill_name}
description: "{request.description}"
---

# {skill_name}

请在此处编写 Skill 的具体工作流程和说明。
"""

    with open(skill_file, "w", encoding="utf-8") as f:
        f.write(default_content)

    return {
        "name": skill_name,
        "path": skill_dir,
        "status": "created",
        "message": f"Skill '{skill_name}' 已创建"
    }


@router.delete("/{skill_name}")
async def delete_skill(skill_name: str):
    """删除 Skill"""
    manager = get_skill_manager()
    skill = manager.loader.get_skill(skill_name)

    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' 不存在")

    # skill.path 是相对于 workspace 的路径，需要转换为绝对路径
    skill_dir = os.path.join(manager.workspace_path, skill.path)

    # 检查是否在 skills 目录下（安全检查）
    skills_base = manager.loader.skills_path
    if not os.path.abspath(skill_dir).startswith(os.path.abspath(skills_base)):
        raise HTTPException(status_code=400, detail="不能删除外部 Skill 目录")

    # 删除整个 Skill 目录
    if os.path.exists(skill_dir):
        shutil.rmtree(skill_dir)

    return {
        "name": skill_name,
        "status": "deleted",
        "message": f"Skill '{skill_name}' 已删除"
    }