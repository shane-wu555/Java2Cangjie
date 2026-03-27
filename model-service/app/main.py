from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import json
import time
import os
from typing import Any

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
    from peft import PeftModel
except Exception as e:
    # 运行时无依赖会在 load() 抛错
    torch = None
    AutoTokenizer = None
    AutoModelForCausalLM = None
    PeftModel = None
    peft_load_error = e

app = FastAPI(title="Java2Cangjie Model Service", version="1.0.0")


class ConvertRequest(BaseModel):
    java_code: str = Field(..., min_length=1, description="待转换 Java 代码")
    max_new_tokens: int = Field(default=512, ge=16, le=4096)
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)


class ConvertResponse(BaseModel):
    cangjie_code: str
    model_name: str
    quantization: str
    latency_ms: int


class ModelRuntime:
    def __init__(self) -> None:
        self.loaded = False
        self.model_name = "Qwen2.5-7B-instruct"
        self.quantization = "4bit + LoRA"
        self.model = None
        self.tokenizer = None

    def load(self) -> None:
        if torch is None:
            raise RuntimeError(f"torch/transformers/peft未安装: {peft_load_error}")

        service_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        base_model = os.environ.get("BASE_MODEL", r"D:\models\Qwen2.5-Coder-7B-Instruct")
        lora_path = os.environ.get("LORA_PATH", os.path.join(service_dir, "outputs", "qwen2.5b-instruct-lora"))

        # 选择DeviceMap以支持可用GPU或CPU
        use_cuda = torch.cuda.is_available()

        self.tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)

        # 4-bit 量化配置：将内存需求从 ~14GB 压缩到 ~4GB，CPU 模式下跳过
        if use_cuda:
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                base_model,
                quantization_config=quantization_config,
                device_map="auto",
                trust_remote_code=True,
            )
            self.quantization = "4bit(NF4) + LoRA"
        else:
            # CPU 模式：使用 float32，内存约 28GB，仅用于测试
            self.model = AutoModelForCausalLM.from_pretrained(
                base_model,
                device_map={"": "cpu"},
                dtype=torch.float32,
                trust_remote_code=True,
            )
            self.quantization = "float32(CPU) + LoRA"

        # 应用LoRA权重
        self.model = PeftModel.from_pretrained(self.model, lora_path)

        self.model.eval()
        self.loaded = True

    def infer(self, java_code: str, max_new_tokens: int, temperature: float) -> str:
        if not self.loaded or self.model is None or self.tokenizer is None:
            raise RuntimeError("模型尚未加载，请先调用 load()")

        prompt = (
            "### 指令：将以下Java代码转换为仓颉代码。\n"
            "转换规则：\n"
            "1. Java基本类型映射：int→Int32, long→Int64, float→Float32, double→Float64, boolean→Bool, byte→Byte, char→Char\n"
            "2. 命名规则：\n"
            "   - struct/class 的公有字段名使用PascalCase（首字母大写），如filename→Filename\n"
            "   - 局部变量、函数参数、方法内的临时变量必须保持camelCase（首字母小写），严禁转为PascalCase，如 int x=42 → let x: Int32 = 42\n"
            "   - 函数名、方法名保持camelCase，如 main、printValue\n"
            "3. 构造方法中使用this而非self引用成员\n"
            "4. interface中的默认方法直接用func，不加open修饰符\n"
            "5. 去掉new关键字，直接调用构造器\n"
            "6. Java的 System.out.println(x) 转换为仓颉的 println(x)\n"
            "7. Java的 public static void main(String[] args) 转换为仓颉的 main(): Unit\n"
            "8. 变量声明：局部变量若绑定后不再重新赋值（包括引用类型只修改元素内容），使用 let；仅当变量本身需要重新赋值时才使用 var\n"
            "### 输入：\n"
            f"{java_code.strip()}\n"
            "### 输出：\n"
        )

        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=2048,
        )

        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}
            self.model.to("cuda")
        else:
            self.model.to("cpu")

        with torch.no_grad():
            out_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature if temperature > 0 else 1.0,
                top_p=0.95,
                do_sample=temperature > 0,
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.pad_token_id,
            )

        generated = self.tokenizer.decode(out_ids[0], skip_special_tokens=True)

        # 去掉 Prompt 前缀，保留模型生成部分
        if prompt in generated:
            generated = generated.split(prompt, 1)[-1].strip()

        if generated == "":
            generated = "[模型未返回结果，请检查 prompt 及模型权重]"

        return generated


runtime = ModelRuntime()

try:
    runtime.load()
except Exception as e:
    # 模型加载失败，/health 可反映失败状态
    runtime_load_error = str(e)
    runtime.loaded = False


@app.get("/health")
def health() -> dict:
    info = {"status": "ok", "model": runtime.model_name}
    if runtime.loaded:
        info.update({"loaded": True, "quantization": runtime.quantization})
    else:
        info.update({"loaded": False, "error": globals().get("runtime_load_error", "unknown")})
    return info


@app.post("/api/v1/convert", response_model=ConvertResponse)
def convert(req: ConvertRequest) -> ConvertResponse:
    if not req.java_code.strip():
        raise HTTPException(status_code=400, detail="java_code 不能为空")

    if not runtime.loaded:
        raise HTTPException(status_code=500, detail=f"模型尚未加载: {globals().get('runtime_load_error', 'unknown')}")

    started = time.time()
    cangjie_code = runtime.infer(req.java_code, req.max_new_tokens, req.temperature)
    latency_ms = int((time.time() - started) * 1000)

    return ConvertResponse(
        cangjie_code=cangjie_code,
        model_name=runtime.model_name,
        quantization=runtime.quantization,
        latency_ms=latency_ms,
    )


# ─── OpenAI Function Calling 兼容接口 ────────────────────────────────────────
# 供 LangChain / AutoGen / 任意支持 OpenAI Tool 格式的框架使用
# 工具发现：GET  /v1/tools
# 工具调用：POST /v1/tools/call

_TOOL_SCHEMA: dict[str, Any] = {
    "object": "list",
    "data": [
        {
            "type": "function",
            "function": {
                "name": "convert_java_to_cangjie",
                "description": (
                    "将 Java 源代码翻译为仓颉（Cangjie）编程语言代码。"
                    "基于 Qwen2.5-Coder-7B-Instruct + LoRA 微调模型，"
                    "专门针对 Java→仓颉语法映射训练。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "java_code": {
                            "type": "string",
                            "description": "待转换的 Java 源代码（支持类、接口、方法等完整语法结构）",
                        },
                        "max_new_tokens": {
                            "type": "integer",
                            "description": "最大生成 token 数，范围 16~4096，默认 512",
                            "default": 512,
                        },
                        "temperature": {
                            "type": "number",
                            "description": "生成温度，0.0 为确定性输出，默认 0.1",
                            "default": 0.1,
                        },
                    },
                    "required": ["java_code"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "check_model_status",
                "description": (
                    "查询 Java2Cangjie 模型服务的健康状态，"
                    "返回模型名称、量化方式及加载状态。"
                    "建议在执行转换前先调用此工具确认服务就绪（loaded=true）。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
    ],
}


class ToolCallRequest(BaseModel):
    name: str = Field(..., description="工具名称，见 GET /v1/tools")
    arguments: str = Field(
        ...,
        description="JSON 字符串格式的工具参数（与 OpenAI function_call.arguments 格式一致）",
    )


class ToolCallResponse(BaseModel):
    name: str
    content: Any


@app.get("/v1/tools")
def list_tools() -> dict:
    """
    返回 OpenAI Function Calling 兼容的工具列表 schema。

    供 LangChain、AutoGen、Semantic Kernel 等框架在构建 Agent 时发现可用工具。
    响应格式与 OpenAI /v1/assistants 的 tools 字段结构一致。
    """
    return _TOOL_SCHEMA


@app.post("/v1/tools/call", response_model=ToolCallResponse)
def call_tool(req: ToolCallRequest) -> ToolCallResponse:
    """
    OpenAI Function Calling 兼容的工具调用端点。

    接受 {name, arguments} 请求，其中 arguments 为 JSON 字符串，
    格式与 OpenAI ChatCompletion tool_call.function.arguments 一致。

    示例请求：
      {"name": "convert_java_to_cangjie", "arguments": "{\"java_code\": \"public class Hello {...}\"}"}
    """
    try:
        args: dict = json.loads(req.arguments)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"arguments 不是合法 JSON: {exc}") from exc

    if req.name == "convert_java_to_cangjie":
        java_code = args.get("java_code")
        if not java_code or not str(java_code).strip():
            raise HTTPException(status_code=400, detail="参数 java_code 不能为空")
        convert_req = ConvertRequest(
            java_code=java_code,
            max_new_tokens=int(args.get("max_new_tokens", 512)),
            temperature=float(args.get("temperature", 0.1)),
        )
        result = convert(convert_req)
        return ToolCallResponse(name=req.name, content=result.cangjie_code)

    elif req.name == "check_model_status":
        return ToolCallResponse(name=req.name, content=health())

    else:
        raise HTTPException(
            status_code=404,
            detail=f"未知工具名称: {req.name!r}，可用工具见 GET /v1/tools",
        )
