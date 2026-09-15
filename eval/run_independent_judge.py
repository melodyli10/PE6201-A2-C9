import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

from src import config

JUDGE_MODEL = "openai/gpt-4.1-mini"

if len(sys.argv) != 2:
    raise SystemExit(
        "Usage: python3.12 eval/run_independent_judge.py <run_dir>"
    )

run_dir = Path(sys.argv[1]).resolve()
queue_path = run_dir / "judgement_queue.jsonl"
output_path = run_dir / "judgements_gpt41mini.jsonl"
prompt_path = Path("eval/judge_prompt.md")

if not queue_path.exists():
    raise SystemExit(f"Missing: {queue_path}")

api_key = os.environ.get("OPENROUTER_API_KEY")
if not api_key:
    raise SystemExit("OPENROUTER_API_KEY is not loaded")

judge_prompt = prompt_path.read_text(encoding="utf-8")

with queue_path.open(encoding="utf-8") as f:
    queue = [json.loads(line) for line in f if line.strip()]

completed = {}
if output_path.exists():
    with output_path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                completed[item["judge_input_sha256"]] = item

print(f"Judge model: {JUDGE_MODEL}")
print(f"Pending queue entries: {len(queue)}")
print(f"Already completed: {len(completed)}")

for index, item in enumerate(queue, start=1):
    digest = item["judge_input_sha256"]

    if digest in completed:
        print(f"[{index}/{len(queue)}] already judged — skipping")
        continue

    payload = {
        "model": JUDGE_MODEL,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": judge_prompt,
            },
            {
                "role": "user",
                "content": (
                    "Evaluate the following judgement input according to the "
                    "system instructions. Return only the required JSON object.\n\n"
                    + json.dumps(item["input"], ensure_ascii=False)
                ),
            },
        ],
    }

    request = urllib.request.Request(
        f"{config.BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    for attempt in range(1, 8):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            retryable = exc.code in {429, 500, 502, 503, 504}
            if not retryable or attempt == 7:
                raise SystemExit(f"OpenRouter HTTP {exc.code}: {body}")
            wait = 60 * attempt
            print(f"OpenRouter HTTP {exc.code}; retry {attempt}/6 in {wait}s", flush=True)
            time.sleep(wait)
        except urllib.error.URLError as exc:
            if attempt == 7:
                raise
            wait = 60 * attempt
            print(f"OpenRouter connection error; retry {attempt}/6 in {wait}s: {exc}", flush=True)
            time.sleep(wait)

    content = data["choices"][0]["message"]["content"].strip()

    if content.startswith("```"):
        lines = content.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    judgement = json.loads(content)

    required = {
        "reason_supported",
        "evidence_supported",
        "passed",
        "explanation",
    }
    missing = required - set(judgement)
    if missing:
        raise SystemExit(f"Judge response missing fields: {sorted(missing)}")

    judgement["judge_input_sha256"] = digest
    judgement["judge_model_id"] = JUDGE_MODEL

    with output_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(judgement, ensure_ascii=False) + "\n")

    print(
        f"[{index}/{len(queue)}] "
        f"{item['input']['case_id']} trial {item['input']['trial']} "
        f"=> {'PASS' if judgement['passed'] else 'FAIL'}"
    )

print(f"\nDone. Wrote: {output_path}")
