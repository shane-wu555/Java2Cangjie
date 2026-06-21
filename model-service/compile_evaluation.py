"""Measure Cangjie compiler pass rate for evaluation predictions."""

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compile generated Cangjie predictions with cjc."
    )
    parser.add_argument("predictions", type=Path)
    parser.add_argument("--compiler", default="cjc")
    parser.add_argument("--timeout", type=int, default=30)
    return parser.parse_args()


def compile_prediction(
    compiler: str,
    code: str,
    source_path: Path,
    output_path: Path,
    timeout: int,
) -> tuple[bool, str]:
    source_path.write_text(code, encoding="utf-8")
    try:
        completed = subprocess.run(
            [compiler, str(source_path), "-o", str(output_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, str(error)

    if completed.returncode == 0:
        return True, ""
    diagnostic = completed.stderr or completed.stdout
    return False, diagnostic[-2_000:]


def main() -> None:
    args = parse_args()
    compiler = shutil.which(args.compiler) or args.compiler
    records = [
        json.loads(line)
        for line in args.predictions.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]

    passed = 0
    results = []
    with tempfile.TemporaryDirectory(
        prefix="java2cangjie_compile_"
    ) as temporary_directory:
        temporary_root = Path(temporary_directory)
        for index, record in enumerate(records, start=1):
            source_path = temporary_root / f"sample_{index}.cj"
            output_path = temporary_root / f"sample_{index}.exe"
            compile_passed, compiler_error = compile_prediction(
                compiler=compiler,
                code=record.get("prediction", ""),
                source_path=source_path,
                output_path=output_path,
                timeout=args.timeout,
            )
            passed += int(compile_passed)
            results.append(
                {
                    "index": index,
                    "compile_pass": compile_passed,
                    "compiler_error": compiler_error,
                }
            )

    count = len(records)
    report = {
        "count": count,
        "compile_pass": passed,
        "compile_pass_rate": passed / count if count else 0.0,
        "results": results,
    }
    output_path = args.predictions.with_suffix(".compile.json")
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    summary = {
        key: value
        for key, value in report.items()
        if key != "results"
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"details: {output_path}")


if __name__ == "__main__":
    main()
