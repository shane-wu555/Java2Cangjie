"""
Java2Cangjie MCP Server

将 Java2Cangjie 转译服务封装为标准 MCP 工具，支持以下客户端直接调用：
  - VS Code GitHub Copilot (MCP 插件)
  - Claude Desktop
  - Cursor IDE
  - 任何兼容 MCP 协议的 AI 智能体

运行模式：
  stdio 模式（Claude Desktop / VS Code Copilot 推荐）：
      python server.py

  SSE HTTP 模式（Docker 容器 / 远程服务部署）：
      python server.py --transport sse --port 8002

环境变量：
  MODEL_SERVICE_URL  模型服务地址，默认 http://localhost:8001
"""

import argparse
import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

MODEL_SERVICE_URL: str = os.environ.get("MODEL_SERVICE_URL", "http://localhost:8001")

mcp = FastMCP(
    name="Java2Cangjie",
    instructions=(
        "你现在可以使用 Java2Cangjie 工具集，将 Java 源代码转换为华为仓颉（Cangjie）编程语言。\n"
        "- 调用 convert_java_to_cangjie 执行代码转换\n"
        "- 调用 check_model_status 确认模型服务是否就绪\n"
        "转换前建议先调用 check_model_status，确认 loaded=true 后再提交转换请求。"
    ),
)


@mcp.tool()
def convert_java_to_cangjie(
    java_code: str,
    max_new_tokens: int = 512,
    temperature: float = 0.1,
) -> str:
    """
    将 Java 源代码翻译为仓颉（Cangjie）编程语言代码。

    适用场景：将现有 Java 项目或代码片段迁移至华为仓颉编程语言。
    模型基于 Qwen2.5-Coder-7B-Instruct + LoRA 微调，专门针对 Java→仓颉语法映射训练。

    类型映射规则（自动处理）：
      int→Int32, long→Int64, float→Float32, double→Float64,
      boolean→Bool, byte→Byte, char→Char

    Args:
        java_code:       待转换的 Java 源代码（支持类、接口、方法等完整语法结构）
        max_new_tokens:  最大生成 token 数，范围 16~4096，默认 512
        temperature:     生成温度，0.0 为确定性输出，越大结果越多样，默认 0.1

    Returns:
        转换后的仓颉代码字符串
    """
    with httpx.Client(timeout=300.0) as client:
        resp = client.post(
            f"{MODEL_SERVICE_URL}/api/v1/convert",
            json={
                "java_code": java_code,
                "max_new_tokens": max_new_tokens,
                "temperature": temperature,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["cangjie_code"]


@mcp.tool()
def check_model_status() -> dict[str, Any]:
    """
    查询 Java2Cangjie 模型服务的健康状态。

    在执行代码转换前建议先调用此工具，确认模型已加载完毕（loaded=true）。
    若 loaded=false，转换请求将返回错误。

    Returns:
        字典，包含：
          loaded      (bool)  模型是否已成功加载
          model       (str)   模型名称（如 Qwen2.5-7B-instruct）
          quantization(str)   量化方式（如 4bit(NF4) + LoRA）
          error       (str)   若加载失败，此字段包含错误信息
    """
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(f"{MODEL_SERVICE_URL}/health")
        resp.raise_for_status()
        return resp.json()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Java2Cangjie MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="传输模式：stdio（本地 Claude Desktop / VS Code）或 sse（HTTP 容器部署），默认 stdio",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="SSE 模式监听地址（默认 0.0.0.0）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8002,
        help="SSE 模式监听端口（默认 8002）",
    )
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="sse")
    else:
        mcp.run()  # stdio 模式，供 Claude Desktop / VS Code Copilot 使用
