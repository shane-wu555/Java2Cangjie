import os
import json
import torch
import jieba
from tqdm import tqdm
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge_chinese import Rouge
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel


BASE_MODEL = "/project_qwen/models/Qwen/Qwen2.5-Coder-7B-Instruct"
LORA_PATH = "/root/project_qwen/output/qwen2.5b-instruct-lora"
TEST_FILE = "/root/project_qwen/data/test.alpaca.max2048.jsonl"
OUTPUT_FILE = "/root/project_qwen/output/eval_predictions.jsonl"

MAX_NEW_TOKENS = 1024


def make_prompt(instruction: str, input_text: str) -> str:
    instruction = (instruction or "").strip()
    input_text = (input_text or "").strip()

    if input_text:
        return (
            f"### 指令：\n{instruction}\n"
            f"### 输入：\n{input_text}\n"
            f"### 输出：\n"
        )
    return f"### 指令：\n{instruction}\n### 输出：\n"


def load_jsonl(path):
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def normalize_text(text: str) -> str:
    return " ".join((text or "").strip().split())


def chinese_tokenize(text: str):
    return list(jieba.cut(normalize_text(text)))


def compute_metrics(preds, refs):
    smoothie = SmoothingFunction().method1
    rouge = Rouge()

    exact_match = 0
    bleu_scores = []
    rouge_l_f1_scores = []

    for pred, ref in zip(preds, refs):
        pred_norm = normalize_text(pred)
        ref_norm = normalize_text(ref)

        if pred_norm == ref_norm:
            exact_match += 1

        pred_tokens = chinese_tokenize(pred_norm)
        ref_tokens = chinese_tokenize(ref_norm)

        if len(pred_tokens) == 0 or len(ref_tokens) == 0:
            bleu = 0.0
        else:
            bleu = sentence_bleu(
                [ref_tokens],
                pred_tokens,
                smoothing_function=smoothie
            )
        bleu_scores.append(bleu)

        try:
            rouge_scores = rouge.get_scores(
                " ".join(pred_tokens),
                " ".join(ref_tokens)
            )
            rouge_l_f1 = rouge_scores[0]["rouge-l"]["f"]
        except Exception:
            rouge_l_f1 = 0.0
        rouge_l_f1_scores.append(rouge_l_f1)

    n = len(preds)
    return {
        "count": n,
        "exact_match": exact_match / n if n else 0.0,
        "bleu": sum(bleu_scores) / n if n else 0.0,
        "rouge_l_f1": sum(rouge_l_f1_scores) / n if n else 0.0,
    }


def main():
    print("=" * 80)
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print("Loading base model...")
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
        trust_remote_code=True,
    )

    print("Loading LoRA adapter...")
    model = PeftModel.from_pretrained(base_model, LORA_PATH)
    model.eval()

    print("Loading test data...")
    data = load_jsonl(TEST_FILE)
    print(f"Test samples: {len(data)}")

    preds = []
    refs = []
    records = []

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    for item in tqdm(data, desc="Evaluating"):
        instruction = item.get("instruction", "")
        input_text = item.get("input", "")
        reference = item.get("output", "")

        prompt = make_prompt(instruction, input_text)

        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=2048,
        ).to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.pad_token_id,
            )

        generated_ids = outputs[0][inputs["input_ids"].shape[1]:]
        prediction = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

        preds.append(prediction)
        refs.append(reference)

        records.append({
            "instruction": instruction,
            "input": input_text,
            "reference": reference,
            "prediction": prediction,
        })

    print("Computing metrics...")
    metrics = compute_metrics(preds, refs)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print("=" * 80)
    print("Evaluation finished.")
    print(f"Predictions saved to: {OUTPUT_FILE}")
    print("Metrics:")
    for k, v in metrics.items():
        if isinstance(v, float):
            print(f"{k}: {v:.4f}")
        else:
            print(f"{k}: {v}")
    print("=" * 80)


if __name__ == "__main__":
    main()