from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import time
import os

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
            "2. struct的公有字段名使用PascalCase（首字母大写），如filename→Filename\n"
            "3. 构造方法中使用this而非self引用成员\n"
            "4. interface中的默认方法直接用func，不加open修饰符\n"
            "5. 去掉new关键字，直接调用构造器\n"
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
