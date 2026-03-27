FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

# SSE HTTP 模式运行，供其他容器或远程 MCP 客户端访问
ENV MODEL_SERVICE_URL=http://model-service:8001

EXPOSE 8002

CMD ["python", "server.py", "--transport", "sse", "--port", "8002"]
