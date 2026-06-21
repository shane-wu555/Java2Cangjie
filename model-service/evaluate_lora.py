import os
import json
import torch
import re
import random
import math
from collections import Counter
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel
from prompt_utils import make_prompt as canonical_prompt


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_MODEL = os.environ.get("BASE_MODEL", r"D:\models\Qwen2.5-Coder-7B-Instruct")
LORA_PATH = os.environ.get("LORA_PATH", os.path.join(PROJECT_DIR, "outputs", "qwen2.5b-instruct-lora"))
TEST_FILE = os.environ.get("TEST_FILE", os.path.join(PROJECT_DIR, "data", "test.alpaca.max2048.jsonl"))
OUTPUT_FILE = os.environ.get("EVAL_OUTPUT", os.path.join(PROJECT_DIR, "outputs", "eval_predictions.jsonl"))

MAX_NEW_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", 1024))
SAMPLE_COUNT = int(os.environ.get("EVAL_SAMPLE_COUNT", 0))
SAMPLE_SEED = int(os.environ.get("EVAL_SAMPLE_SEED", 42))
EVAL_MODE = os.environ.get("EVAL_MODE", "lora").lower()
if EVAL_MODE not in {"base", "lora"}:
    raise ValueError("EVAL_MODE must be base or lora")


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


def code_tokenize(text: str):
    return re.findall(r"[A-Za-z_]\w*|\d+(?:\.\d+)?|==|!=|<=|>=|&&|\|\||[-+*/%{}()\[\];,.:<>]", normalize_text(text))


def ngram_counts(tokens, order):
    return Counter(
        tuple(tokens[index:index + order])
        for index in range(len(tokens) - order + 1)
    )


def sentence_code_bleu(pred_tokens, ref_tokens):
    if not pred_tokens or not ref_tokens:
        return 0.0
    max_order = min(4, len(pred_tokens), len(ref_tokens))
    log_precisions = []
    for order in range(1, max_order + 1):
        predicted = ngram_counts(pred_tokens, order)
        reference = ngram_counts(ref_tokens, order)
        overlap = sum(
            min(count, reference[ngram])
            for ngram, count in predicted.items()
        )
        possible = sum(predicted.values())
        # Add-one smoothing keeps short, non-identical snippets measurable.
        log_precisions.append(math.log((overlap + 1) / (possible + 1)))
    brevity_penalty = (
        1.0
        if len(pred_tokens) >= len(ref_tokens)
        else math.exp(1.0 - len(ref_tokens) / len(pred_tokens))
    )
    return brevity_penalty * math.exp(sum(log_precisions) / max_order)


def rouge_l_f1(pred_tokens, ref_tokens):
    if not pred_tokens or not ref_tokens:
        return 0.0
    previous = [0] * (len(ref_tokens) + 1)
    for pred_token in pred_tokens:
        current = [0]
        for index, ref_token in enumerate(ref_tokens, start=1):
            if pred_token == ref_token:
                current.append(previous[index - 1] + 1)
            else:
                current.append(max(previous[index], current[-1]))
        previous = current
    lcs_length = previous[-1]
    precision = lcs_length / len(pred_tokens)
    recall = lcs_length / len(ref_tokens)
    return 2 * precision * recall / (precision + recall) if lcs_length else 0.0


def compute_metrics(preds, refs):
    exact_match = 0
    bleu_scores = []
    rouge_l_f1_scores = []

    for pred, ref in zip(preds, refs):
        pred_norm = normalize_text(pred)
        ref_norm = normalize_text(ref)

        if pred_norm == ref_norm:
            exact_match += 1

        pred_tokens = code_tokenize(pred_norm)
        ref_tokens = code_tokenize(ref_norm)

        bleu_scores.append(sentence_code_bleu(pred_tokens, ref_tokens))
        rouge_l_f1_scores.append(rouge_l_f1(pred_tokens, ref_tokens))

    n = len(preds)
    return {
        "count": n,
        "exact_match": exact_match / n if n else 0.0,
        "code_token_bleu": sum(bleu_scores) / n if n else 0.0,
        "code_token_rouge_l_f1": sum(rouge_l_f1_scores) / n if n else 0.0,
    }


def main():
    print("=" * 80)
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print(f"Evaluation mode: {EVAL_MODE}")
    print("Loading base model...")
    model_kwargs = {
        "device_map": "auto",
        "trust_remote_code": True,
    }
    if torch.cuda.is_available():
        model_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
    else:
        model_kwargs["torch_dtype"] = torch.float32

    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        **model_kwargs,
    )
    if EVAL_MODE == "lora":
        print("Loading LoRA adapter...")
        model = PeftModel.from_pretrained(base_model, LORA_PATH)
    else:
        print("Using base model without LoRA adapter...")
        model = base_model
    model.eval()

    print("Loading test data...")
    data = load_jsonl(TEST_FILE)
    if 0 < SAMPLE_COUNT < len(data):
        selected_indices = sorted(
            random.Random(SAMPLE_SEED).sample(
                range(len(data)),
                SAMPLE_COUNT,
            )
        )
        data = [data[index] for index in selected_indices]
    print(f"Test samples: {len(data)}")

    preds = []
    refs = []
    records = []

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    for item in tqdm(data, desc="Evaluating"):
        instruction = item.get("instruction", "")
        input_text = item.get("input", "")
        reference = item.get("output", "")

        prompt = canonical_prompt(input_text, instruction)

        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=2048,
        )
        model_device = next(model.parameters()).device
        inputs = {key: value.to(model_device) for key, value in inputs.items()}

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
            "mode": EVAL_MODE,
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

    metrics_file = os.path.splitext(OUTPUT_FILE)[0] + ".metrics.json"
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(
            {"mode": EVAL_MODE, **metrics},
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("=" * 80)
    print("Evaluation finished.")
    print(f"Predictions saved to: {OUTPUT_FILE}")
    print(f"Metrics saved to: {metrics_file}")
    print("Metrics:")
    for k, v in metrics.items():
        if isinstance(v, float):
            print(f"{k}: {v:.4f}")
        else:
            print(f"{k}: {v}")
    print("=" * 80)


if __name__ == "__main__":
    main()
