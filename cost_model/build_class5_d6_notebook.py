"""Adapt the supplied Class 5 cost-to-serve notebook for Problem A D6.

This preserves the original three-layer, sensitivity and break-even cells,
then fills its 'your own use case' cell from the measured A2 battery. The
generated notebook is committed; re-running this builder is optional and
requires the original Class 5 notebook in the course workspace.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parents[2] / "Class 5" / "code" / "PE6201_Class5_C2_Cost_to_Serve.ipynb"
OUTPUT = ROOT / "cost_model" / "PE6201_A2_D6_Cost_to_Serve.ipynb"


def lines(text: str) -> list[str]:
    return text.splitlines(keepends=True)


def build() -> dict:
    notebook = json.loads(SOURCE.read_text(encoding="utf-8"))
    notebook["cells"][0]["source"] = lines(
        "# PE6201 A2 D6 - Problem A cost-to-serve calculator\n\n"
        "Adapted from the supplied Class 5 Capsule 2 cost-to-serve notebook. "
        "Its three-layer, sensitivity and break-even functions are retained; "
        "the Problem A cell below uses measured D5 tokens and D4 outcomes.\n"
    )
    notebook["cells"][2]["source"] += lines(
        "\n# A2 Problem A values recorded for the Mistral V2 battery.\n"
        "PRICES['mistral_a2'] = {'in': 0.075, 'out': 0.20, 'cached_in': 0.075}\n"
        "LABOUR['claims_assessor'] = {'usd_per_hour': 38.0, "
        "'minutes_per_escalation': 12.0}\n"
    )
    notebook["cells"][15]["source"] = lines(
        "## Section 6 - A2 Problem A measured baseline\n\n"
        "Layer 1 uses D5(b) provider usage at the recorded list price. "
        "Layer 2 prices a failed first response as 12 minutes of assessor labour. "
        "Layer 3 is USD 0 measured provider fees for the local prototype; "
        "an illustrative USD 152 maintenance assumption is shown separately. "
        "The source aggregates and all five models are in `battery_inputs.json`.\n"
    )
    notebook["cells"][16]["source"] = lines(
        "from cost_model.calculate_d6 import calculate\n"
        "D6 = calculate()\n"
        "M = next(r for r in D6['models'] if r['model_id'].startswith('mistralai/') "
        "and r['prompt_version'] == 'v2-final')\n"
        "G = next(r for r in D6['models'] if r['model_id'] == 'openai/gpt-4.1-mini')\n"
        "MY = dict(volume=8000, tier='mistral_a2', fresh_in=M['prompt_tokens']/55, "
        "cached_in=0, out=M['completion_tokens']/55, retrieval_usd=0.0, "
        "success_rate=M['passed']/55, "
        "failure_usd=escalation_cost('claims_assessor'), fixed_monthly_usd=0.0)\n"
        "var = variable_cost(MY['tier'], fresh_in=MY['fresh_in'], "
        "cached_in=MY['cached_in'], out=MY['out'], retrieval_usd=MY['retrieval_usd'])\n"
        "per = cost_per_successful_task(var, MY['success_rate'], MY['failure_usd'])\n"
        "total = monthly(var, MY['success_rate'], MY['failure_usd'], "
        "MY['volume'], MY['fixed_monthly_usd'])\n"
        "assert abs(var-M['layer_1_per_task_usd']) < 1e-6\n"
        "assert abs(total-M['monthly_usd']) < 0.01\n"
        "print(f'Mistral V2: {M[\"passed\"]}/55 passed; layer 1 USD {var:.6f}/task; '"
        "f'layer 2 USD {(per-var):.6f}/task')\n"
        "print(f'Baseline cost USD {per:.6f}/task; USD {total:,.2f}/month')\n"
        "print(f'Illustrative +4 hours/month review: USD {total+152:,.2f}/month')\n"
        "sensitivity(var, MY['failure_usd'], MY['success_rate'], label='Mistral V2:')\n"
        "print('\\nFive V2 models, same 55-trial selection:')\n"
        "for r in D6['models']:\n"
        "    if r['prompt_version'] == 'v2-final':\n"
        "        print(f'{r[\"model_id\"]:<45} {r[\"passed\"]}/55  '"
        "f'USD {r[\"all_in_per_task_usd\"]:.6f}/task')\n"
        "need = break_even_success_rate(var, G['all_in_per_task_usd'], "
        "MY['failure_usd'])\n"
        "print(f'Cheap Mistral break-even vs GPT-4.1 Mini: {need:.2%}; '"
        "f'observed {MY[\"success_rate\"]:.2%}')\n"
    )
    # Keep the supplied method and worked checks; omit its unrelated
    # invoice exercise and blank 'your own use case' placeholder.
    notebook["cells"] = notebook["cells"][:11] + notebook["cells"][15:17]
    notebook["cells"].append(
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": lines(
                "The full D6 ledger, operational caps, raw-source audit and "
                "report section are in `D6_cost_model.md` and the committed "
                "`cost_model/` evidence files. This notebook makes no live request.\n"
            ),
        }
    )
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            cell["outputs"] = []
            cell["execution_count"] = None
    OUTPUT.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return notebook


if __name__ == "__main__":
    result = build()
    print(f"Adapted {SOURCE.name}: {len(result['cells'])} cells -> {OUTPUT}")
