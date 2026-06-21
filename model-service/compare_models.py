"""Run and compare base-model and LoRA evaluations on the same test set."""

import json
import os
import random
import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "outputs" / "comparison"
BOOTSTRAP_SAMPLES = int(os.environ.get("BOOTSTRAP_SAMPLES", "2000"))
BOOTSTRAP_SEED = int(os.environ.get("BOOTSTRAP_SEED", "42"))


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def run_evaluation(mode: str, output_file: Path) -> None:
    environment = os.environ.copy()
    environment["EVAL_MODE"] = mode
    environment["EVAL_OUTPUT"] = str(output_file)
    subprocess.run(
        [sys.executable, str(PROJECT_DIR / "evaluate_lora.py")],
        cwd=PROJECT_DIR,
        env=environment,
        check=True,
    )


def bootstrap_mean_difference(
    differences: list[float],
) -> dict[str, float | bool]:
    if not differences:
        return {"mean_delta": 0.0, "ci95_low": 0.0, "ci95_high": 0.0,
                "significant": False}

    rng = random.Random(BOOTSTRAP_SEED)
    count = len(differences)
    bootstrap_means = []
    for _ in range(BOOTSTRAP_SAMPLES):
        sample_mean = sum(
            differences[rng.randrange(count)]
            for _ in range(count)
        ) / count
        bootstrap_means.append(sample_mean)
    bootstrap_means.sort()

    low_index = int(0.025 * (BOOTSTRAP_SAMPLES - 1))
    high_index = int(0.975 * (BOOTSTRAP_SAMPLES - 1))
    low = bootstrap_means[low_index]
    high = bootstrap_means[high_index]
    return {
        "mean_delta": sum(differences) / count,
        "ci95_low": low,
        "ci95_high": high,
        "significant": low > 0.0 or high < 0.0,
    }


def per_record_scores(record: dict) -> dict[str, float]:
    from evaluate_lora import compute_metrics

    metrics = compute_metrics(
        [record.get("prediction", "")],
        [record.get("reference", "")],
    )
    return {
        "exact_match": metrics["exact_match"],
        "code_token_bleu": metrics["code_token_bleu"],
        "code_token_rouge_l_f1": metrics["code_token_rouge_l_f1"],
    }


def compare_predictions(
    base_records: list[dict],
    lora_records: list[dict],
) -> dict:
    if len(base_records) != len(lora_records):
        raise ValueError("Base and LoRA prediction counts differ")

    metric_differences = {
        "exact_match": [],
        "code_token_bleu": [],
        "code_token_rouge_l_f1": [],
    }
    paired_records = []
    for index, (base, lora) in enumerate(
        zip(base_records, lora_records),
        start=1,
    ):
        if base.get("input") != lora.get("input"):
            raise ValueError(f"Input mismatch at sample {index}")
        base_scores = per_record_scores(base)
        lora_scores = per_record_scores(lora)
        deltas = {
            name: lora_scores[name] - base_scores[name]
            for name in metric_differences
        }
        for name, delta in deltas.items():
            metric_differences[name].append(delta)
        paired_records.append(
            {
                "index": index,
                "input": base.get("input", ""),
                "reference": base.get("reference", ""),
                "base_prediction": base.get("prediction", ""),
                "lora_prediction": lora.get("prediction", ""),
                "base_scores": base_scores,
                "lora_scores": lora_scores,
                "deltas": deltas,
            }
        )

    return {
        "count": len(paired_records),
        "delta_definition": "LoRA - Base",
        "bootstrap_samples": BOOTSTRAP_SAMPLES,
        "metrics": {
            name: bootstrap_mean_difference(differences)
            for name, differences in metric_differences.items()
        },
        "records": paired_records,
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    base_output = OUTPUT_DIR / "base_predictions.jsonl"
    lora_output = OUTPUT_DIR / "lora_predictions.jsonl"

    run_evaluation("base", base_output)
    run_evaluation("lora", lora_output)

    report = compare_predictions(
        load_jsonl(base_output),
        load_jsonl(lora_output),
    )
    report_path = OUTPUT_DIR / "comparison_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    summary = {key: value for key, value in report.items() if key != "records"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Full paired report: {report_path}")


if __name__ == "__main__":
    main()
