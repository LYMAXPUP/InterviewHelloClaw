"""图片生成工具 - 使用阿里云 DashScope 多模态生成 API"""

import os
import json
import uuid
import time
import re
from typing import List, Dict, Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from hello_agents.tools import Tool, ToolParameter, ToolResponse, tool_action


class ImageGenerationTool(Tool):
    """图片生成工具

    使用阿里云 DashScope 多模态生成 API (qwen-image-2.0) 生成图片。
    图片保存到 outputs 目录，前端可通过 /outputs/{filename} 访问。
    """

    def __init__(
        self,
        outputs_path: str = None,
        api_key: str = None,
        model: str = None,
        timeout: int = 120,
    ):
        """初始化图片生成工具

        Args:
            outputs_path: 图片输出目录，如未提供则使用 ~/.helloclaw/workspace/outputs
            api_key: API Key，如未提供则从环境变量 LLM_API_KEY 读取
            model: 图片生成模型，如未提供则从环境变量 IMAGE_LLM_MODEL_ID 读取
            timeout: 请求超时时间（秒），默认 120
        """
        super().__init__(
            name="generate_image",
            description="根据文字描述生成图片。图片会保存到 outputs 目录，可通过 /outputs/ 路径访问。",
            expandable=True
        )

        # 输出目录
        if outputs_path:
            self.outputs_path = os.path.expanduser(outputs_path)
        else:
            workspace_path = os.getenv("WORKSPACE_PATH", "~/.helloclaw/workspace")
            self.outputs_path = os.path.expanduser(os.path.join(workspace_path, "outputs"))

        # 确保输出目录存在
        os.makedirs(self.outputs_path, exist_ok=True)

        # API 配置
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.model = model or os.getenv("IMAGE_LLM_MODEL_ID", "qwen-image-2.0")
        self.timeout = timeout

        # 多模态生成 API endpoint
        self._api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        """执行图片生成"""
        prompt = parameters.get("prompt", "")
        size = parameters.get("size", "1024*1024")
        n = parameters.get("n", 1)

        return self._generate_image(prompt, size, n)

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="prompt",
                type="string",
                description="图片描述，详细描述你想要生成的图片内容",
                required=True
            ),
            ToolParameter(
                name="size",
                type="string",
                description="图片尺寸，可选值: 720*720, 1024*1024, 1024*720, 720*1024, 2048*2048，默认 1024*1024",
                required=False
            ),
            ToolParameter(
                name="n",
                type="integer",
                description="生成图片数量，默认 1",
                required=False
            ),
        ]

    def _generate_image(
        self,
        prompt: str,
        size: str = "1024*1024",
        n: int = 1,
    ) -> ToolResponse:
        """生成图片的核心实现 - 使用阿里云多模态生成 API

        Args:
            prompt: 图片描述
            size: 图片尺寸
            n: 生成数量

        Returns:
            ToolResponse: 生成结果
        """
        if not prompt:
            return ToolResponse.error(
                code="INVALID_INPUT",
                message="图片描述不能为空"
            )

        if not self.api_key:
            return ToolResponse.error(
                code="MISSING_API_KEY",
                message="未配置 API Key。请设置环境变量 LLM_API_KEY"
            )

        try:
            print(f"🎨 正在生成图片，模型: {self.model}")
            print(f"📝 描述: {prompt[:100]}...")
            print(f"📐 尺寸: {size}")

            # 构建请求体（阿里云多模态生成 API 格式）
            payload = {
                "model": self.model,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "text": prompt
                                }
                            ]
                        }
                    ]
                },
                "parameters": {
                    "n": n,
                    "negative_prompt": " ",
                    "prompt_extend": True,
                    "watermark": False,
                    "size": size
                }
            }

            request = Request(
                self._api_url,
                data=json.dumps(payload).encode("utf-8"),
                method="POST"
            )
            request.add_header("Content-Type", "application/json")
            request.add_header("Authorization", f"Bearer {self.api_key}")

            # 发送请求
            with urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))

            print(f"✅ API 响应成功")

            # 处理响应
            return self._process_response(data, prompt)

        except HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
            except:
                error_body = str(e)

            print(f"❌ HTTP 错误: {e.code}")
            print(f"错误详情: {error_body}")

            if e.code == 401:
                return ToolResponse.error(
                    code="AUTH_ERROR",
                    message="API Key 无效或已过期"
                )
            elif e.code == 429:
                return ToolResponse.error(
                    code="RATE_LIMIT",
                    message="API 请求频率超限，请稍后再试"
                )
            else:
                return ToolResponse.error(
                    code="HTTP_ERROR",
                    message=f"图片生成请求失败 (HTTP {e.code}): {error_body}"
                )
        except URLError as e:
            return ToolResponse.error(
                code="NETWORK_ERROR",
                message=f"网络错误: {str(e)}"
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return ToolResponse.error(
                code="GENERATION_ERROR",
                message=f"图片生成失败: {str(e)}"
            )

    def _process_response(self, data: Dict[str, Any], prompt: str) -> ToolResponse:
        """处理 API 响应，提取图片并保存

        Args:
            data: API 返回的数据
            prompt: 原始提示词

        Returns:
            ToolResponse: 包含图片路径的结果
        """
        # 检查是否有错误
        if "code" in data and data.get("code") != "Success":
            return ToolResponse.error(
                code="API_ERROR",
                message=data.get("message", "未知错误")
            )

        if "error" in data:
            return ToolResponse.error(
                code="API_ERROR",
                message=data.get("error", {}).get("message", "未知错误")
            )

        # 提取输出结果
        output = data.get("output", {})

        # 尝试从 choices 中提取（新格式）
        choices = output.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            content_list = message.get("content", [])

            if content_list:
                # content 是一个列表，每个元素可能是 image 或 text
                saved_images = []
                saved_urls = []

                for i, content_item in enumerate(content_list):
                    # 图片元素
                    if isinstance(content_item, dict) and "image" in content_item:
                        url = content_item.get("image")
                        if url:
                            print(f"📥 下载图片 {i+1}/{len(content_list)}: {url[:60]}...")
                            image_data = self._download_image(url)
                            if image_data:
                                filename = self._save_image(image_data, prompt, i)
                                if filename:
                                    saved_images.append(filename)
                                    saved_urls.append(f"/outputs/{filename}")

                    # 文本元素（可能包含 Markdown 图片）
                    elif isinstance(content_item, dict) and "text" in content_item:
                        text = content_item.get("text", "")
                        image_urls = self._extract_image_urls(text)
                        for j, url in enumerate(image_urls):
                            print(f"📥 下载图片 {j+1}/{len(image_urls)}: {url[:60]}...")
                            image_data = self._download_image(url)
                            if image_data:
                                filename = self._save_image(image_data, prompt, len(saved_images))
                                if filename:
                                    saved_images.append(filename)
                                    saved_urls.append(f"/outputs/{filename}")

                if saved_images:
                    image_list = "\n".join([f"- ![{prompt[:30]}]({url})" for url in saved_urls])
                    return ToolResponse.success(
                        text=f"已生成 {len(saved_images)} 张图片:\n{image_list}\n\n图片已保存，可以直接查看。",
                        data={
                            "prompt": prompt,
                            "images": saved_images,
                            "urls": saved_urls,
                            "count": len(saved_images),
                        }
                    )

        # 尝试从 results 中提取（旧格式）
        results = output.get("results", [])
        if results:
            saved_images = []
            saved_urls = []

            for i, result in enumerate(results):
                url = result.get("url") or result.get("image_url") or result.get("output_url")
                if url:
                    print(f"📥 下载图片 {i+1}/{len(results)}: {url[:60]}...")
                    image_data = self._download_image(url)
                    if image_data:
                        filename = self._save_image(image_data, prompt, i)
                        if filename:
                            saved_images.append(filename)
                            saved_urls.append(f"/outputs/{filename}")

            if saved_images:
                image_list = "\n".join([f"- ![{prompt[:30]}]({url})" for url in saved_urls])
                return ToolResponse.success(
                    text=f"已生成 {len(saved_images)} 张图片:\n{image_list}\n\n图片已保存，可以直接查看。",
                    data={
                        "prompt": prompt,
                        "images": saved_images,
                        "urls": saved_urls,
                        "count": len(saved_images),
                    }
                )

        # 尝试从其他字段提取
        content = output.get("content", "")
        if content:
            image_urls = self._extract_image_urls(content)
            if image_urls:
                return self._save_images_from_urls(image_urls, prompt)

        return ToolResponse.error(
            code="NO_RESULTS",
            message=f"API 返回空结果。响应: {json.dumps(data)[:500]}"
        )

    def _save_images_from_urls(self, image_urls: List[str], prompt: str) -> ToolResponse:
        """从 URL 列表下载并保存图片

        Args:
            image_urls: 图片 URL 列表
            prompt: 提示词

        Returns:
            ToolResponse: 结果
        """
        saved_images = []
        saved_urls = []

        for i, url in enumerate(image_urls):
            print(f"📥 下载图片 {i+1}/{len(image_urls)}: {url[:60]}...")
            image_data = self._download_image(url)
            if image_data:
                filename = self._save_image(image_data, prompt, i)
                if filename:
                    saved_images.append(filename)
                    saved_urls.append(f"/outputs/{filename}")

        if not saved_images:
            return ToolResponse.error(
                code="SAVE_ERROR",
                message="图片下载或保存失败"
            )

        image_list = "\n".join([f"- ![{prompt[:30]}]({url})" for url in saved_urls])

        return ToolResponse.success(
            text=f"已生成 {len(saved_images)} 张图片:\n{image_list}\n\n图片已保存，可以直接查看。",
            data={
                "prompt": prompt,
                "images": saved_images,
                "urls": saved_urls,
                "count": len(saved_images),
            }
        )

    def _extract_image_urls(self, text: str) -> List[str]:
        """从文本中提取图片 URL

        Args:
            text: 文本内容

        Returns:
            图片 URL 列表
        """
        urls = []

        # 1. 提取 Markdown 图片语法中的 URL
        markdown_pattern = r'!\[.*?\]\((https?://[^\s\)]+?\.(?:jpg|jpeg|png|gif|webp|bmp)(?:\?[^\s\)]*)?)\)'
        markdown_matches = re.findall(markdown_pattern, text, re.IGNORECASE)
        urls.extend(markdown_matches)

        # 2. 提取裸露的图片 URL
        url_pattern = r'(https?://[^\s<>"\'\)]+?\.(?:jpg|jpeg|png|gif|webp|bmp)(?:\?[^\s<>"\'\)]*)?)'
        url_matches = re.findall(url_pattern, text, re.IGNORECASE)
        for url in url_matches:
            if url not in urls:
                urls.append(url)

        # 3. 阿里云 OSS URL 可能不含扩展名，尝试匹配 oss 相关 URL
        oss_pattern = r'(https?://[^\s<>"\'\)]*oss[^\s<>"\'\)]*)'
        oss_matches = re.findall(oss_pattern, text, re.IGNORECASE)
        for url in oss_matches:
            if url not in urls:
                urls.append(url)

        return urls

    def _download_image(self, url: str) -> bytes:
        """从 URL 下载图片

        Args:
            url: 图片 URL

        Returns:
            图片二进制数据
        """
        try:
            request = Request(url)
            request.add_header("User-Agent", "Mozilla/5.0 HelloClaw ImageGenerator")
            request.add_header("Accept", "image/*")

            with urlopen(request, timeout=60) as response:
                return response.read()
        except Exception as e:
            print(f"⚠️ 图片下载失败: {e}")
            return None

    def _save_image(self, image_data: bytes, prompt: str, index: int) -> str:
        """保存图片到 outputs 目录

        Args:
            image_data: 图片二进制数据
            prompt: 提示词
            index: 图片索引

        Returns:
            文件名（不含路径）
        """
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            unique_id = uuid.uuid4().hex[:6]
            filename = f"img_{timestamp}_{unique_id}_{index}.png"

            filepath = os.path.join(self.outputs_path, filename)
            with open(filepath, "wb") as f:
                f.write(image_data)

            print(f"📷 图片已保存: {filename}")
            return filename

        except Exception as e:
            print(f"⚠️ 图片保存失败: {e}")
            return None

    @tool_action("generate_image", "生成图片")
    def _generate_action(self, prompt: str, size: str = "1024*1024") -> str:
        """生成图片

        Args:
            prompt: 图片描述
            size: 图片尺寸（可选）
        """
        response = self._generate_image(prompt, size)
        return response.text