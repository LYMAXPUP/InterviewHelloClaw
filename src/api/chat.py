"""聊天 API 路由"""
import json
import re
from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    session_id: Optional[str] = None
    images: Optional[List[str]] = Field(default=None, description="图片 URL 列表")


class ChatResponse(BaseModel):
    """聊天响应"""
    content: str
    session_id: Optional[str] = None


def convert_local_image_paths(text: str) -> str:
    """将本地图片路径转换为 HTTP URL

    支持的路径格式：
    - .helloclaw/workspace/outputs/xxx.png
    - outputs/xxx.png
    - ~/.helloclaw/workspace/outputs/xxx.png（展开后）
    - Markdown 图片语法 ![...](本地路径)

    Args:
        text: 包含可能的本地图片路径的文本

    Returns:
        转换后的文本，本地路径变为 /outputs/xxx.png
    """
    # 图片扩展名（用于匹配）
    img_ext_pattern = r'(jpg|jpeg|png|gif|webp|bmp)'

    # 本地路径前缀模式（需要转换的）
    local_path_prefixes = [
        # .helloclaw/workspace/outputs/ 或类似路径（支持 / 和 \）
        r'(?:\.helloclaw[/\\]workspace[/\\]outputs[/\\])',
        # workspace/outputs/
        r'(?:workspace[/\\]outputs[/\\])',
        # 直接 outputs/ 开头
        r'(?:outputs[/\\])',
    ]

    # 合并为一个前缀匹配模式
    prefix_pattern = '(' + '|'.join(local_path_prefixes) + ')'

    # 1. 处理 Markdown 图片语法中的本地路径: ![...](本地路径)
    # 匹配: ![alt](prefix + filename.ext)
    markdown_img_pattern = r'!\[(.*?)\]\(' + prefix_pattern + r'([^)\s]+?\.' + img_ext_pattern + r')\)'

    def replace_markdown_img(match):
        alt_text = match.group(1)
        filename = match.group(2)  # filename.ext（不含前缀）
        return f'![{alt_text}](/outputs/{filename})'

    text = re.sub(markdown_img_pattern, replace_markdown_img, text, flags=re.IGNORECASE)

    # 2. 处理裸露的本地路径（不在 Markdown 语法中）
    # 匹配: prefix + filename.ext（后面可能有空格、引号等）
    bare_path_pattern = prefix_pattern + r'([^/\\\s"\']+?\.' + img_ext_pattern + r')'
    text = re.sub(bare_path_pattern, r'/outputs/\2', text, flags=re.IGNORECASE)

    return text


def extract_image_urls(text: str) -> List[str]:
    """从文本中提取直接的图片 URL

    只提取有明显图片扩展名的 URL。
    支持的格式：
    - http(s)://...jpg, .jpeg, .png, .gif, .webp, .bmp
    - Markdown 图片语法 ![...](url)
    """
    urls = []

    # 1. 提取 Markdown 图片语法中的 URL
    markdown_pattern = r'!\[.*?\]\((https?://[^\s]+?\.(?:jpg|jpeg|png|gif|webp|bmp)(?:\?[^\s]*)?)\)'
    markdown_matches = re.findall(markdown_pattern, text, re.IGNORECASE)
    urls.extend(markdown_matches)

    # 2. 提取裸露的图片 URL（直接图片文件）
    url_pattern = r'(https?://[^\s<>"\']+?\.(?:jpg|jpeg|png|gif|webp|bmp)(?:\?[^\s<>"\']*)?)'
    url_matches = re.findall(url_pattern, text, re.IGNORECASE)
    for url in url_matches:
        if url not in urls:
            urls.append(url)

    return urls


def get_agent():
    """获取全局 Agent 实例"""
    from ..main import get_agent as _get_agent
    return _get_agent()


@router.post("/send/sync", response_model=ChatResponse)
async def send_message_sync(request: ChatRequest):
    """发送消息并获取同步响应"""
    agent = get_agent()
    if not agent:
        return ChatResponse(content="Agent not initialized", session_id=request.session_id)

    # 合并显式传入的图片和文本中提取的图片
    images = request.images or []
    extracted_images = extract_image_urls(request.message)
    all_images = images + [url for url in extracted_images if url not in images]

    # 直接传 URL 给模型，不预先下载
    if all_images:
        print(f"📷 传入 {len(all_images)} 张图片 URL")

    response = agent.chat(request.message, request.session_id, images=all_images)
    # 转换本地图片路径为 HTTP URL
    response = convert_local_image_paths(response)
    return ChatResponse(content=response, session_id=request.session_id)


@router.post("/send/stream")
async def send_message_stream(request: ChatRequest):
    """发送消息并获取流式响应 (SSE)

    事件类型：
    - session: 会话信息（包含 session_id）
    - step_start: 步骤开始
    - chunk: LLM 文本块
    - tool_start: 工具调用开始
    - tool_finish: 工具调用结束
    - step_finish: 步骤结束
    - done: 完成
    - error: 错误
    """

    async def event_generator():
        agent = get_agent()
        if not agent:
            yield {
                "event": "error",
                "data": json.dumps({"error": "Agent not initialized"}, ensure_ascii=False)
            }
            return

        # 合并显式传入的图片和文本中提取的图片
        images = request.images or []
        extracted_images = extract_image_urls(request.message)
        all_images = images + [url for url in extracted_images if url not in images]

        # 直接传 URL 给模型，不预先下载
        if all_images:
            print(f"📷 传入 {len(all_images)} 张图片 URL")

        try:
            async for event in agent.achat(request.message, request.session_id, images=all_images):
                event_type = event.type.value
                event_data = event.data

                # 处理不同类型的事件
                if event_type == "agent_start":
                    session_id = getattr(agent, '_current_session_id', None)
                    yield {
                        "event": "session",
                        "data": json.dumps({"session_id": session_id}, ensure_ascii=False)
                    }

                elif event_type == "step_start":
                    yield {
                        "event": "step_start",
                        "data": json.dumps({
                            "step": event_data.get("step", 1),
                            "max_steps": event_data.get("max_steps", 10)
                        }, ensure_ascii=False)
                    }

                elif event_type == "llm_chunk":
                    chunk = event_data.get("chunk", "")
                    # 转换本地图片路径为 HTTP URL
                    chunk = convert_local_image_paths(chunk)
                    yield {
                        "event": "chunk",
                        "data": json.dumps({"content": chunk}, ensure_ascii=False)
                    }

                elif event_type == "tool_call_start":
                    yield {
                        "event": "tool_start",
                        "data": json.dumps({
                            "tool": event_data.get("tool_name", ""),
                            "args": event_data.get("args", {})
                        }, ensure_ascii=False)
                    }

                elif event_type == "tool_call_finish":
                    yield {
                        "event": "tool_finish",
                        "data": json.dumps({
                            "tool": event_data.get("tool_name", ""),
                            "result": event_data.get("result", "")
                        }, ensure_ascii=False)
                    }

                elif event_type == "step_finish":
                    yield {
                        "event": "step_finish",
                        "data": json.dumps({
                            "step": event_data.get("step", 1)
                        }, ensure_ascii=False)
                    }

                elif event_type == "max_iterations":
                    yield {
                        "event": "max_iterations",
                        "data": json.dumps({
                            "max_iterations": event_data.get("max_iterations", 10),
                            "message": event_data.get("message", "已达到最大工具调用次数")
                        }, ensure_ascii=False)
                    }

                elif event_type == "agent_finish":
                    session_id = agent.save_current_session()
                    final_content = event_data.get("result", "")
                    # 转换本地图片路径为 HTTP URL
                    final_content = convert_local_image_paths(final_content)

                    yield {
                        "event": "done",
                        "data": json.dumps({
                            "content": final_content,
                            "session_id": session_id
                        }, ensure_ascii=False)
                    }

                elif event_type == "error":
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": event_data.get("error", "Unknown error")}, ensure_ascii=False)
                    }

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}, ensure_ascii=False)
            }

    return EventSourceResponse(event_generator())


@router.post("/send")
async def send_message(request: ChatRequest):
    """发送消息（暂返回同步响应）"""
    return await send_message_sync(request)