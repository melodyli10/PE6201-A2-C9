#!/usr/bin/env python3
"""Validate and merge independent LLM judgement JSONL into an existing D4 run."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from eval.harness import read_json, summarise, write_json, write_jsonl, write_result_tables


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("judgements", type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    rows = read_jsonl(run_dir / "trials.jsonl")
    metadata = read_json(run_dir / "metadata.json")
    supplied = read_jsonl(args.judgements.resolve())
    by_hash = {}
    for item in supplied:
        digest = item.get("judge_input_sha256")
        if not digest or digest in by_hash:
            raise SystemExit(f"missing or duplicate judge_input_sha256: {digest!r}")
        required = {"judge_model_id", "reason_supported", "evidence_supported",
                    "passed", "explanation"}
        missing = sorted(required - set(item))
        if missing:
            raise SystemExit(f"judgement {digest} missing fields: {missing}")
        if item["passed"] is not (item["reason_supported"] and item["evidence_supported"]):
            raise SystemExit(f"judgement {digest} has inconsistent passed value")
        if item["judge_model_id"] == metadata["model_id"]:
            raise SystemExit(f"judge cannot grade itself: {item['judge_model_id']}")
        by_hash[digest] = item

    expected_hashes = {row["judge_input_sha256"] for row in rows if row["judgement_required"]}
    if set(by_hash) != expected_hashes:
        missing = sorted(expected_hashes - set(by_hash))
        extra = sorted(set(by_hash) - expected_hashes)
        raise SystemExit(f"judgement set mismatch; missing={missing}, extra={extra}")

    for row in rows:
        if not row["judgement_required"]:
            continue
        judgement = by_hash[row["judge_input_sha256"]]
        row["judgement_status"] = "pass" if judgement["passed"] else "fail"
        row["judgement"] = judgement
        row["passed"] = bool(row["code_passed"] and judgement["passed"])

    metadata = dict(metadata)
    metadata["judgements_applied_utc"] = datetime.now(timezone.utc).isoformat()
    output_rows = run_dir / "trials_judged.jsonl"
    write_jsonl(output_rows, rows)
    write_result_tables(run_dir, rows)
    write_json(run_dir / "summary_judged.json", summarise(rows, metadata))
    print(f"Wrote {output_rows}")
    print(f"Wrote {run_dir / 'summary_judged.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
