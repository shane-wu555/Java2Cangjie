from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import time
import os

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
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

        base_model = os.environ.get("BASE_MODEL", "qwen/Qwen-2.5B-instruct")
        lora_path = os.environ.get("LORA_PATH", "outputs/qwen2.5b-instruct-lora")

        # 选择DeviceMap以支持可用GPU或CPU
        device = "cuda" if torch.cuda.is_available() else "cpu"

        self.tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)

        # 先加载基础模型（可根据需求调整quantization_config）
        self.model = AutoModelForCausalLM.from_pretrained(
            base_model,
            device_map="auto" if torch.cuda.is_available() else {"": "cpu"},
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            trust_remote_code=True,
        )

        # 应用LoRA权重
        self.model = PeftModel.from_pretrained(self.model, lora_path, torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32)

        if not torch.cuda.is_available():
            self.model.to("cpu")

        self.model.eval()
        self.loaded = True

    def infer(self, java_code: str, max_new_tokens: int, temperature: float) -> str:
        if not self.loaded or self.model is None or self.tokenizer is None:
            raise RuntimeError("模型尚未加载，请先调用 load()")

        prompt = f"### 指令：将以下Java代码转换为仓舉编码\n### 输入：\n{java_code.strip()}\n### 输出：\n"

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
                temperature=temperature,
                top_p=0.95,
                do_sample=False,
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
