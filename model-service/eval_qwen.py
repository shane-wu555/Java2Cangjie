import json
import os
import random
import time
from difflib import SequenceMatcher

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


def make_prompt(java_code: str) -> str:
    return f"### 指令：将以下Java代码转换为仓颉代码\n### 输入：\n{java_code.strip()}\n### 输出：\n"


def load_jsonl_samples(file_path: str) -> list[dict]:
    samples = []
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            samples.append(json.loads(line))
    return samples


def looks_like_cangjie(text: str) -> bool:
    markers = ["func ", "main()", "println(", "struct ", "interface ", "Foreign func", "let ", "match "]
    return any(marker in text for marker in markers)


def smoke_check(text: str) -> tuple[bool, list[str]]:
    issues = []
    stripped = text.strip()

    if not stripped:
        issues.append("空输出")
    if "### 指令" in stripped or "### 输入" in stripped or "### 输出" in stripped:
        issues.append("存在提示词回显")
    if "�" in stripped:
        issues.append("存在乱码")
    if not looks_like_cangjie(stripped):
        issues.append("缺少明显仓颉语法特征")

    return len(issues) == 0, issues

def similarity_score(pred: str, ref: str) -> float:
    """基于字符级编辑相似度（0.0 ~ 1.0），1.0 表示完全相同。"""
    if not pred and not ref:
        return 1.0
    if not pred or not ref:
        return 0.0
    return SequenceMatcher(None, pred.strip(), ref.strip()).ratio()


def fidelity_grade(score: float) -> str:
    if score >= 0.85:
        return "高保真"
    if score >= 0.60:
        return "中等"
    return "低保真"

def generate_one(model, tokenizer, run_device: str, java_code: str, max_new_tokens: int) -> str:
    prompt = make_prompt(java_code)
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
    inputs = {key: value.to(run_device) for key, value in inputs.items()}
    prompt_length = inputs["input_ids"].shape[1]

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )

    generated_ids = output_ids[0][prompt_length:]
    return tokenizer.decode(generated_ids, skip_special_tokens=True).strip()


if __name__ == "__main__":
    project_dir = os.path.dirname(os.path.abspath(__file__))

    base_model = os.environ.get("BASE_MODEL", r"D:\models\Qwen2.5-Coder-7B-Instruct")
    lora_dir = os.environ.get("LORA_PATH", os.path.join(project_dir, "outputs", "qwen2.5b-instruct-lora"))
    eval_file = os.environ.get("EVAL_FILE", os.path.join(project_dir, "data", "test.alpaca.jsonl"))
    # SMOKE_SAMPLE_COUNT=0 表示跑全量测试集
    sample_count = int(os.environ.get("SMOKE_SAMPLE_COUNT", 10))
    sample_seed = int(os.environ.get("SMOKE_SEED", 42))
    max_new_tokens = int(os.environ.get("MAX_NEW_TOKENS", 512))
    output_file = os.environ.get("EVAL_OUTPUT", os.path.join(project_dir, "eval_results.jsonl"))

    use_cuda = torch.cuda.is_available()
    load_dtype = torch.float16 if use_cuda else torch.float32
    device_map = {"": 0} if use_cuda else {"": "cpu"}
    run_device = "cuda" if use_cuda else "cpu"

    print(f"Base Model: {base_model}")
    print(f"LoRA Path: {lora_dir}")
    print(f"Eval File: {eval_file}")
    print(f"Run Device: {run_device}")
    print(f"Sample Count: {sample_count}")
    print("Loading tokenizer and base model...")
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        device_map=device_map,
        dtype=load_dtype,
        trust_remote_code=True,
    )

    print("Loading LoRA weights...")
    model = PeftModel.from_pretrained(
        model,
        lora_dir,
        torch_dtype=load_dtype,
        device_map=device_map,
    )
    model.eval()

    samples = load_jsonl_samples(eval_file)
    if not samples:
        raise RuntimeError(f"评测文件为空: {eval_file}")

    rng = random.Random(sample_seed)
    if sample_count <= 0 or sample_count >= len(samples):
        selected_samples = samples
        print(f"全量测试集评测模式: {len(selected_samples)} 条")
    else:
        selected_samples = rng.sample(samples, sample_count)
        print(f"抽样评测模式: {sample_count}/{len(samples)} 条（seed={sample_seed}）")

    passed = 0
    sim_scores: list[float] = []
    results: list[dict] = []
    eval_start = time.time()

    print("Starting evaluation...")
    for index, sample in enumerate(selected_samples, start=1):
        java_code = sample.get("input", "")
        expected = sample.get("output", "")
        t0 = time.time()
        prediction = generate_one(model, tokenizer, run_device, java_code, max_new_tokens)
        latency_ms = int((time.time() - t0) * 1000)
        ok, issues = smoke_check(prediction)
        sim = similarity_score(prediction, expected)
        grade = fidelity_grade(sim)
        if ok:
            passed += 1
        sim_scores.append(sim)

        result = {
            "index": index,
            "smoke_pass": ok,
            "issues": issues,
            "similarity": round(sim, 4),
            "fidelity": grade,
            "latency_ms": latency_ms,
            "java_input": java_code,
            "prediction": prediction,
            "reference": expected,
        }
        results.append(result)

        print(f"\n===== Sample {index}/{len(selected_samples)} =====")
        print("[Java 输入前12行]")
        print("\n".join(java_code.strip().splitlines()[:12]))
        print("\n[模型输出]")
        print(prediction if prediction else "<EMPTY>")
        print("\n[参考输出前12行]")
        print("\n".join(expected.strip().splitlines()[:12]))
        print(f"\n[冒烟判定] {'PASS' if ok else 'FAIL'} | 相似度: {sim:.2%} ({grade}) | 耗时: {latency_ms}ms")
        if issues:
            print(f"[问题] {'; '.join(issues)}")

    # 保存详细结果
    with open(output_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    total = len(selected_samples)
    avg_sim = sum(sim_scores) / total if total else 0.0
    high_fidelity = sum(1 for s in sim_scores if s >= 0.85)
    mid_fidelity = sum(1 for s in sim_scores if 0.60 <= s < 0.85)
    low_fidelity = sum(1 for s in sim_scores if s < 0.60)
    total_secs = time.time() - eval_start

    print("\n===== Summary =====")
    print(f"Total Samples     : {total}")
    print(f"Smoke Pass        : {passed}/{total} ({passed / total:.2%})")
    print(f"Avg Similarity    : {avg_sim:.2%}")
    print(f"高保真 (>=85%)    : {high_fidelity} ({high_fidelity / total:.2%})")
    print(f"中等保真 (60~85%) : {mid_fidelity} ({mid_fidelity / total:.2%})")
    print(f"低保真 (<60%)     : {low_fidelity} ({low_fidelity / total:.2%})")
    print(f"Total Time        : {total_secs:.1f}s")
    print(f"Results saved to  : {output_file}")
