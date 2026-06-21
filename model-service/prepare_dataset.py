"""Rebuild cleaned Java-to-Cangjie Alpaca datasets reproducibly."""

import argparse
import hashlib
import json
import random
from pathlib import Path

from prompt_utils import INSTRUCTION, make_prompt

SOURCE_KEYS = ("input", "java", "java_code", "source", "source_code")
TARGET_KEYS = ("output", "cangjie", "cangjie_code", "target", "target_code")


def load_records(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".jsonl":
        return [
            json.loads(line)
            for line in text.splitlines()
            if line.strip()
        ]

    value = json.loads(text)
    if isinstance(value, dict):
        value = value.get("data", value.get("records", []))
    if not isinstance(value, list):
        raise ValueError(f"{path}: expected a JSON array")
    return value


def first_string(record: dict, keys: tuple[str, ...]) -> str:
    return next(
        (
            record[key]
            for key in keys
            if isinstance(record.get(key), str)
        ),
        "",
    )


def clean_code(text: str) -> str:
    normalized = (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\0", "")
        .strip()
    )
    return "\n".join(line.rstrip() for line in normalized.split("\n"))


def save_jsonl(path: Path, records: list[dict]) -> None:
    content = "".join(
        json.dumps(record, ensure_ascii=False) + "\n"
        for record in records
    )
    path.write_text(content, encoding="utf-8")


def filter_by_token_length(
    records: list[dict],
    tokenizer,
    max_tokens: int,
) -> list[dict]:
    filtered = []
    for record in records:
        training_text = (
            make_prompt(record["input"], record["instruction"])
            + record["output"]
            + tokenizer.eos_token
        )
        token_ids = tokenizer(
            training_text,
            add_special_tokens=False,
        )["input_ids"]
        if len(token_ids) <= max_tokens:
            filtered.append(record)
    return filtered


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean and split Java-to-Cangjie parallel data."
    )
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "data",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-chars", type=int, default=20_000)
    parser.add_argument("--max-tokens", type=int, default=2_048)
    parser.add_argument(
        "--tokenizer",
        help="Optional local tokenizer path for max-token files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_records = [
        record
        for input_path in args.inputs
        for record in load_records(input_path)
    ]

    unique_records: dict[str, dict] = {}
    output_variants: dict[str, set[str]] = {}
    dropped_empty = 0
    dropped_too_long = 0
    dropped_duplicate = 0

    for raw_record in raw_records:
        source = clean_code(first_string(raw_record, SOURCE_KEYS))
        target = clean_code(first_string(raw_record, TARGET_KEYS))

        if not source or not target:
            dropped_empty += 1
            continue
        if max(len(source), len(target)) > args.max_chars:
            dropped_too_long += 1
            continue

        pair_hash = hashlib.sha256(
            (source + "\0" + target).encode("utf-8")
        ).hexdigest()
        if pair_hash in unique_records:
            dropped_duplicate += 1
            continue

        unique_records[pair_hash] = {
            "instruction": INSTRUCTION,
            "input": source,
            "output": target,
        }
        output_variants.setdefault(source, set()).add(target)

    records = list(unique_records.values())
    random.Random(args.seed).shuffle(records)

    train_end = int(len(records) * 0.90)
    valid_end = int(len(records) * 0.95)
    splits = {
        "train": records[:train_end],
        "valid": records[train_end:valid_end],
        "test": records[valid_end:],
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for split_name, split_records in splits.items():
        save_jsonl(
            args.output_dir / f"{split_name}.alpaca.jsonl",
            split_records,
        )

    max_token_counts = {}
    if args.tokenizer:
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(
            args.tokenizer,
            trust_remote_code=True,
        )
        for split_name, split_records in splits.items():
            filtered = filter_by_token_length(
                split_records,
                tokenizer,
                args.max_tokens,
            )
            save_jsonl(
                args.output_dir
                / f"{split_name}.alpaca.max{args.max_tokens}.jsonl",
                filtered,
            )
            max_token_counts[split_name] = len(filtered)

    report = {
        "input_total": len(raw_records),
        "kept_total": len(records),
        "dropped_empty": dropped_empty,
        "dropped_too_long": dropped_too_long,
        "dropped_duplicate": dropped_duplicate,
        "conflicting_inputs": sum(
            len(variants) > 1
            for variants in output_variants.values()
        ),
        **{
            f"{split_name}_count": len(split_records)
            for split_name, split_records in splits.items()
        },
        "max_token_counts": max_token_counts,
        "seed": args.seed,
    }
    report_text = json.dumps(report, ensure_ascii=False, indent=2)
    (args.output_dir / "dataset_report.json").write_text(
        report_text + "\n",
        encoding="utf-8",
    )
    print(report_text)


if __name__ == "__main__":
    main()
