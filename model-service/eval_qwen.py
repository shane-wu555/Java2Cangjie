import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel


if __name__ == "__main__":
    base_model = os.environ.get("BASE_MODEL", "qwen/Qwen-2.5B-instruct")
    lora_dir = os.environ.get("LORA_PATH", "outputs/qwen2.5b-instruct-lora")

    print(f"Base Model: {base_model}")
    print(f"LoRA Path: {lora_dir}")
    print("Loading tokenizer and base model...")
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        device_map="auto",
        trust_remote_code=True,
    )

    print("Loading LoRA weights...")
    model = PeftModel.from_pretrained(model, lora_dir, torch_dtype=torch.float16)
    model.eval()

    sample_java = """
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println(\"Hello, Cangjie!\");
    }
}
"""

    prompt = f"### 指令：将以下Java代码转换为仓颉代码\n### 输入：\n{sample_java}\n### 输出：\n"

    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048).to(model.device)

    print("Generating output...")
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.1,
            top_p=0.95,
            do_sample=False,
            eos_token_id=tokenizer.eos_token_id,
        )

    decoded = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    print("=== 推理结果 ===")
    print(decoded)
