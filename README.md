# Java2Cangjie Web 应用

将 Java 代码转换为仓颉代码的全栈 Web 应用，基于 Qwen2.5-Coder-7B-Instruct + LoRA 微调模型，采用三层架构：

- **FastAPI 模型服务**：加载 Qwen2.5-Coder-7B-Instruct + LoRA 权重（4-bit NF4 量化），提供推理接口。
- **Spring Boot 业务后端**：用户注册/登录（SHA-256 + salt 哈希）、参数校验、转发推理请求。
- **Vue 3 前端**：Chat 风格界面，支持多会话管理、语法高亮、文件导入/下载。

## 系统架构

```
用户浏览器
    │  HTTP :5173
    ▼
Nginx (Vue 3 SPA)
    │  /api/* 反向代理 → :8080
    ▼
Spring Boot :8080
    │  REST → :8001
    ▼
FastAPI :8001
    │
Qwen2.5-Coder-7B-Instruct + LoRA (4-bit NF4)
```

## 目录结构

```text
.
├── model-service/      # FastAPI + Qwen2.5-Coder 推理服务
│   ├── app/main.py     # 服务入口，ModelRuntime 类
│   ├── finetune_qwen.py  # LoRA 微调脚本
│   ├── eval_qwen.py    # 推理验证脚本
│   ├── data/           # 训练/验证/测试数据集（Alpaca 格式）
│   └── outputs/        # LoRA adapter 权重（qwen2.5b-instruct-lora/）
├── spring-backend/     # Spring Boot 3 / Java 17 网关服务
├── frontend/           # Vue 3 + Vue Router + Axios
└── docker-compose.yml  # 容器编排
```

---

## 1. 模型服务（FastAPI）

### API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 返回模型加载状态（`loaded`, `model`, `quantization`, `error`）|
| `POST` | `/api/v1/convert` | Java → 仓颉代码转译 |

### 转译接口参数

```json
{
  "java_code": "...",       // 必填
  "max_new_tokens": 512,    // 16 ~ 4096，默认 512
  "temperature": 0.1        // 0.0 ~ 2.0，默认 0.1
}
```

### 转译接口响应

```json
{
  "cangjie_code": "...",
  "model_name": "...",
  "quantization": "...",
  "latency_ms": 1234
}
```

### 模型加载逻辑（`ModelRuntime`）

- 通过环境变量 `BASE_MODEL` 指定基座模型路径（默认 `D:\models\Qwen2.5-Coder-7B-Instruct`）
- 通过环境变量 `LORA_PATH` 指定 LoRA 权重路径（默认 `./outputs/qwen2.5b-instruct-lora`）
- GPU 可用时：4-bit NF4 量化（`BitsAndBytesConfig`），显存占用约 4 GB
- CPU 模式：float32，仅用于测试（约 28 GB 内存）
- 服务启动时自动执行 `load()`，失败不崩溃，`/health` 会反映失败状态

### 推理 Prompt 格式

```
### 指令：将以下Java代码转换为仓颉代码。
转换规则：（类型映射 / 语法对齐规则）
### 输入：{java_code}
### 输出：
```

---

## 2. Spring Boot 后端

### API 接口

#### 认证（`/api/auth`）

| 方法 | 路径 | 请求体 | 说明 |
|------|------|------|------|
| `POST` | `/api/auth/register` | `{username, password}` | 注册，返回 `{token, username}` |
| `POST` | `/api/auth/login` | `{username, password}` | 登录，返回 `{token, username}` |

字段约束：`username` 3~20 字符；`password` ≥ 6 字符。

#### 业务（`/api`）

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/health` | 后端 + 模型服务联合健康检查 |
| `POST` | `/api/convert` | 转发转译请求至模型服务 |

转译请求体：`{javaCode, maxNewTokens, temperature}`（`javaCode` 最大 20000 字符）

#### 统一错误响应格式

```json
{
  "timestamp": "...",
  "status": 400,
  "error": "Bad Request",
  "message": "...",
  "path": "/api/convert"
}
```

### 安全与存储

- 密码存储：随机 16 字节 salt（Base64）+ SHA-256 哈希，存于内存
- Token：注册/登录时生成 UUID，存于内存映射
- **注意**：当前使用纯内存存储，服务重启后账号数据丢失

### 关键配置（`application.yml`）

```yaml
server:
  port: 8080

model:
  service:
    base-url: ${MODEL_SERVICE_BASE_URL:http://localhost:8001}
    connect-timeout-ms: ${MODEL_SERVICE_CONNECT_TIMEOUT_MS:3000}
    read-timeout-ms: ${MODEL_SERVICE_READ_TIMEOUT_MS:30000}
```

所有配置均可通过环境变量覆盖。

### 技术栈

- Spring Boot 3.3.4 / Java 17
- Spring MVC + Jackson + Bean Validation
- `RestClient` 调用下游模型服务
- 全局异常处理（`@RestControllerAdvice`）
- 请求日志过滤器（`X-Request-Id` 响应头）
- CORS：允许所有来源，支持 `GET / POST / OPTIONS`

---

## 3. Vue 3 前端

### 页面路由

| 路径 | 页面 | 鉴权 |
|------|------|------|
| `/` | `HomeView` — 主工作台 | 需登录 |
| `/login` | `LoginView` — 登录 | 已登录则跳转首页 |
| `/register` | `RegisterView` — 注册 | 已登录则跳转首页 |

Token 存于 `localStorage`（`java2cangjie_token` / `java2cangjie_user`）。

### 主工作台功能

- **Chat 风格布局**：左侧边栏（会话列表）+ 右侧工作区（对话流）
- **多会话管理**：会话历史持久化于 `localStorage`（按用户名隔离）
- **模型健康状态**：侧边栏实时芯片，每 30 秒轮询 `/api/health`
- **Java 代码输入**：支持文本输入或导入 `.java` 文件
- **转译结果操作**：一键复制、下载 `.cj` 文件
- **语法高亮**：纯 JS 实现，支持 Java 和仓颉关键字高亮

### 技术栈

- Vue 3.5 + Vue Router 4
- Axios（转译请求超时 60 s，健康检查超时 5 s）
- `@vue/cli-service`（开发服务器监听 `0.0.0.0:5173`）
- 无 UI 组件库，纯 CSS 自定义样式

### 语法高亮支持的关键字（`utils/highlight.js`）

- Java：`class`, `interface`, `public`, `private`, `static`, `void`, `int` 等标准关键字及类型
- 仓颉：与 Java 对应的仓颉语法关键字

---

## 4. LoRA 微调

### 数据集

`model-service/data/` 下为 Alpaca 格式 JSONL：

| 文件 | 说明 |
|------|------|
| `train.alpaca.jsonl` | 完整训练集 |
| `train.alpaca.max2048.jsonl` | 截断至 2048 token 的训练集 |
| `valid.alpaca.jsonl` | 验证集 |
| `test.alpaca.jsonl` | 测试集 |

### 微调脚本

```bash
cd model-service
python finetune_qwen.py   # LoRA 微调
python eval_qwen.py       # 单样本验证
```

### 微调产物

`outputs/qwen2.5b-instruct-lora/` 包含最终 LoRA adapter（`adapter_config.json` + `adapter_model.safetensors`）及三个 checkpoint（1000 / 1100 / 1176 步）。

---

## 本地运行

### 1. 模型服务（FastAPI）

```bash
cd model-service
pip install -r requirements.txt
# 可选：指定本地模型路径
set BASE_MODEL=D:\models\Qwen2.5-Coder-7B-Instruct
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### 2. Spring Boot 后端

```bash
cd spring-backend
mvn spring-boot:run
```

### 3. Vue 3 前端

```bash
cd frontend
npm install
npm run serve
```

访问地址：

- 前端：`http://localhost:5173`
- Spring Boot Health：`http://localhost:8080/api/health`
- FastAPI Health：`http://localhost:8001/health`

---

## Docker 容器化部署

```bash
docker compose up --build
```

服务启动顺序（由健康检查控制）：

1. `model-service`（等待模型加载，宽限期 120 s）
2. `spring-backend`（等待模型服务健康）
3. `frontend`（等待 Spring Boot 健康）

访问地址同本地运行。

### GPU 环境要求

Docker Compose 已配置挂载 1 块 NVIDIA GPU。宿主机需安装：

- NVIDIA 驱动 + CUDA 12.1
- `nvidia-container-toolkit`

> 如需使用昇腾 NPU，请在容器运行参数中补充对应 runtime / device 挂载及驱动依赖。
