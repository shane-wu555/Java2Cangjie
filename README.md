# Java2Cangjie Web 应用方案

本仓库提供一个可落地的三层 Web 架构：

- **FastAPI 模型服务**：负责加载量化模型（示例中为占位实现，可替换为 LLaMA Factory 推理逻辑）。
- **Spring Boot 业务后端**：负责参数校验、接口聚合、转发推理请求。
- **Vue CLI 前端**：提供用户输入 Java 代码并展示仓颉结果的页面。

## 目录结构

```text
.
├── model-service/      # FastAPI + 量化模型推理接口
├── spring-backend/     # Spring Boot 网关/业务服务
├── frontend/           # Vue3 页面
└── docker-compose.yml  # 一键容器编排
```

## 1) 模型量化与 Web 开发（FastAPI）

FastAPI 提供以下接口：

- `GET /health`：服务健康检查
- `POST /api/v1/convert`：输入 Java 代码，输出仓颉代码

`model-service/app/main.py` 中 `ModelRuntime` 预留了模型加载与推理入口：

- `load()`：替换为 LLaMA Factory 的模型加载流程
- `infer(...)`：替换为量化模型推理调用

## 2) SpringBoot 服务层

Spring Boot 暴露：

- `GET /api/health`
- `POST /api/convert`

流程：
1. 前端调用 Spring Boot 接口。
2. Spring Boot 校验参数后调用 FastAPI `/api/v1/convert`。
3. 收到模型输出后返回前端。

## 3) Vue CLI 服务界面

界面能力：

- 输入 Java 代码
- 配置 `max_new_tokens` 和 `temperature`
- 点击转换后展示仓颉代码、模型名、量化方式和推理延迟

## 本地运行

### FastAPI

```bash
cd model-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### Spring Boot

```bash
cd spring-backend
mvn spring-boot:run
```

### Vue3

```bash
cd frontend
npm install
npm run serve
```

## Docker 容器化部署

```bash
docker compose up --build
```

访问：

- 前端：`http://localhost:5173`
- Spring Boot：`http://localhost:8080/api/health`
- FastAPI：`http://localhost:8001/health`

> 生产环境中如需使用昇腾 NPU，请在容器运行参数中补充对应 runtime / device 挂载及驱动依赖。
## Qwen2.5-7B-instruct 微调（本项目新增）

### 快速开始（推荐）

打开 `model-service` 目录，编辑 `quickstart.bat`（Windows CMD）或 `quickstart.ps1`（PowerShell）文件中的路径，然后运行即可：

```powershell
# PowerShell
cd model-service
.\quickstart.ps1
```

或直接双击 `quickstart.bat`。

### 手动步骤

1. 安装依赖：

```bash
cd model-service
pip install -r requirements.txt
```

2. 使用 `finetune_qwen.py` 训练：

```bash
python finetune_qwen.py
```

3. 单例验证：

```bash
python eval_qwen.py
```

4. 启动服务：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

5. API 接口：

- `GET /health`
- `POST /api/v1/convert` 绑定参数 `java_code` / `max_new_tokens` / `temperature`

### 【重要】网络问题？使用本地模型

如果无法从 Hugging Face 下载，查看 [LOCAL_MODEL_SETUP.md](model-service/LOCAL_MODEL_SETUP.md) 了解如何使用本地模型路径。

简单示例：

```powershell
$env:BASE_MODEL = "D:\models\qwen-2.5b-instruct"
python finetune_qwen.py
```
