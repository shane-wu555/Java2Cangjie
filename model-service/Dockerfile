# ---------------------------------------------------------------
# 基础镜像选择：
#   CPU 推理    → python:3.11-slim（当前默认）
#   NVIDIA GPU  → nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04
#   Ascend NPU  → 使用厂商提供的 cann+torch_npu 基础镜像
# ---------------------------------------------------------------
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（curl 用于容器内健康调试）
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# 若需 CUDA 版 torch，可在构建时覆盖：
#   --build-arg TORCH_INDEX=https://download.pytorch.org/whl/cu121
ARG TORCH_INDEX=https://download.pytorch.org/whl/cu121
RUN pip install --no-cache-dir -r requirements.txt

# 只复制业务代码，模型权重通过 volume 挂载
COPY app ./app

EXPOSE 8001

# workers=1 保证模型只被加载一次；timeout 设大以覆盖首次推理延迟
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1", "--timeout-keep-alive", "120"]
