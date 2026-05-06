"""
HelloClaw Backend - FastAPI 入口
"""
import os

# 禁用 PYTHONSTARTUP 以避免 I/O 问题
os.environ.pop("PYTHONSTARTUP", None)

# 设置 matplotlib backend 为 Agg（无 GUI，支持 subprocess 图片保存）
# 使用环境变量确保 subprocess 执行 python -c 时也能生效
os.environ["MPLBACKEND"] = "Agg"

# 当前进程也设置
import matplotlib
matplotlib.use('Agg')

from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api import chat, session, config, memory, skills, interviews
from .workspace.manager import WorkspaceManager
from .workspace.skills import SkillManager
from .agent.helloclaw_agent import HelloClawAgent
from .database.mongodb_config import MongoConfig

# 加载环境变量
load_dotenv()

# 全局 Agent 实例
_agent: HelloClawAgent = None
_workspace: WorkspaceManager = None


def get_agent() -> HelloClawAgent:
    """获取全局 Agent 实例"""
    global _agent
    return _agent


def get_workspace() -> WorkspaceManager:
    """获取全局 Workspace 实例"""
    global _workspace
    return _workspace


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global _agent, _workspace

    # 启动时初始化
    print("HelloClaw Backend starting...")
    print("-*"*50)

    # 初始化工作空间
    workspace_path = os.getenv("WORKSPACE_PATH", "~/.helloclaw/workspace")
    _workspace = WorkspaceManager(workspace_path)
    _workspace.ensure_workspace_exists()
    print(f"Workspace initialized at: {_workspace.workspace_path}")

    # 挂载 outputs 目录为静态文件服务
    outputs_path = _workspace.outputs_path
    os.makedirs(outputs_path, exist_ok=True)
    app.mount("/outputs", StaticFiles(directory=outputs_path), name="outputs")
    print(f"Outputs directory mounted at /outputs")

    # 设置全局 workspace 实例
    config.set_workspace(_workspace)
    memory.set_workspace(_workspace)

    # 初始化 Skill API
    skill_manager = SkillManager(_workspace.workspace_path)
    skills.init_skill_api(skill_manager)

    # 初始化 MongoDB 连接
    print("Initializing MongoDB...")
    MongoConfig.initialize()
    print(f"MongoDB status: {'connected' if MongoConfig.is_connected() else 'not connected'}")

    # 初始化全局 Agent 实例
    _agent = HelloClawAgent(workspace_path=workspace_path)
    print("HelloClawAgent initialized")
    print(f"Skills loaded: {_agent.skill_manager.list_skills()}")

    yield
    # 关闭时清理
    print("HelloClaw Backend shutting down...")

    # 关闭 MongoDB 连接
    MongoConfig.close()
    print("MongoDB connection closed")


app = FastAPI(
    title="HelloClaw API",
    description="AI Agent powered by HelloAgents",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 健康检查
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "helloclaw-backend"}


# 注册 API 路由
app.include_router(chat.router, prefix="/api")
app.include_router(session.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(memory.router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(interviews.router, prefix="/api")


@app.get("/api")
async def api_root():
    return {"message": "HelloClaw API v0.1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
    )
